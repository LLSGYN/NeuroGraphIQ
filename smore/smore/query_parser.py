import copy
import queue
import rdflib
import rdflib.plugins.sparql.parser as parser
import os
import pyparsing
import pickle as pkl

from collections import defaultdict
from itertools import product
from rdflib.plugins.sparql.parserutils import prettify_parsetree, CompValue
from typing import Iterable, Union

# class Variable(str):
#     def __new__(cls, value):
#         return super().__new__(cls, value)

# class Grounded(str):
#     def __new__(cls, value):
#       return super().__new__(cls, value)

def adjust(g: 'QueryDAG', target:str, manager: 'MetaManager') -> 'QueryDAG':

    def undirected_adj(g: 'QueryDAG'):
        adj = g.ent_out
        adj_undir = defaultdict(lambda: defaultdict(set))
        for u in adj:
            for r in adj[u]:
                for v in adj[u][r]:
                    adj_undir[u][r].add(v)
                    adj_undir[v][manager.reverse_relation(r)].add(u)
        return adj_undir

    cnt = 0
    mp = dict()
    adj = undirected_adj(g)
    q = queue.Queue()
    q.put(manager.get_variable(target))
    while not q.empty():
        cnt += 1
        u = q.get()
        mp[u] = cnt
        for r in adj[u]:
            for v in adj[u][r]:
                if v not in mp:
                    q.put(v)
    
    # edges = []
    # for u in adj:
    #     for r in adj[u]:
    #         for v in adj[u][r]:
    #             if manager.node_data[u]['type'] == 'anchor':
    #                 edges.append((u, r, v))
    #             elif mp[v] < mp[u] and (not 
    #                 manager.node_data[v]['type'] == 'anchor'):
    #                 edges.append((u, r, v))


    to_v = defaultdict(lambda: list([]))
    edges = []
    for u in adj:
        for r in adj[u]:
            for v in adj[u][r]:
                if manager.node_data[u]['type'] == 'anchor':
                    to_v[v].append((u, r, v))
                elif mp[v] < mp[u] and (not 
                    manager.node_data[v]['type'] == 'anchor'):
                    to_v[v].append((u, r, v))

    edges = []
    for x in adj:
        if len(to_v[x]) == 1:
            edges += to_v[x]
            continue
        elif len(to_v[x]) >= 2:
            is_all_uni, no_uori, is_all_ins = True, True, True
            for u, r, v in to_v[x]:
                is_all_uni &= (r == 0)
                is_all_ins &= (r == 2)
                no_uori &= ((r != 0) and (r != 2))
            if is_all_uni:
                print("all union, nothing to do")
                edges += to_v[x]
            elif is_all_ins:
                print("all intersection, nothing to do")
                edges += to_v[x]
            elif no_uori:
                print("auto intersection triggered!")
                ins_cnt = 0
                for u, r, v in to_v[x]:
                    ins_cnt += 1
                    relab_v = manager.get_variable(f"{v}_INS_{ins_cnt}")
                    edges.append((u, r, relab_v))
                    edges.append((relab_v, 2, v)) # 补充intersection edge
            else:
                raise ValueError("Both intersection edge and relation edge detected!")
    
    return QueryDAG(manager, edges)

def adjust_dm(g: 'QueryDAG') -> 'QueryDAG':
    has_union = False
    for u in g.ent_out:
        for rel in g.ent_out[u]:
            for v in g.ent_out[u][rel]:
                if rel == 0: #union
                    has_union = True
                    union_node = v
                    break
    if not has_union:
        return g
    manager = g.manager
    edges = []
    uni_neg = manager.get_variable(f"{union_node}_DMNEG")
    edges.append((uni_neg, 1, union_node))
    for u in g.ent_out:
        for rel in g.ent_out[u]:
            for v in g.ent_out[u][rel]:
                if v != union_node:
                    assert rel != 0
                    edges.append((u, rel, v))
                else: # DM 
                    assert rel == 0
                    temp = manager.get_variable(f"{u}_DMNEG")
                    edges.append((u, 1, temp)) # NEG
                    edges.append((temp, 2, uni_neg))
    return QueryDAG(manager, edges)


class QueryDAG(object):
    def __init__(self, manager: 'MetaManager', triples=None):
        self.nodes = set()
        self.ent_out = defaultdict(lambda: defaultdict(set))
        self.manager = manager

        if triples is not None:
            for [s, r, o] in triples:
                self.ent_out[s][r].add(o)
                self.nodes.add(s)
                self.nodes.add(o)

    def export_plan(self):
        data = { "nodes": [], "edges": [] }
        for idx in self.nodes:
            name, tp = self.manager.get_node_name(idx)
            if tp == 'anchor':
                data["nodes"].append({"id": f"{idx}", "label": name, "type": "ellipse", "style": {"fill": "#f7faff"}})
            else:
                if len(self.ent_out[idx]) > 0:
                    data["nodes"].append({"id": f"{idx}", "label": "Var", "type": "circle", "style": {"fill": "grey"}})
                else:
                    data["nodes"].append({"id": f"{idx}", "label": "Target", "type": "star", "size": 20, "style": {"fill": "#ffa500"}})
        
        for u in self.nodes:
            for rel in self.ent_out[u]:
                for v in self.ent_out[u][rel]:
                    name, flg = self.manager.get_rel_name(rel)
                    conf = {"source": f"{u}", "target": f"{v}", "label": name, "style": { "lineDash": None if flg else [5]}}
                    data['edges'].append(conf)
        return data


    def print(self) -> None:
        for u in self.nodes:
            for rel in self.ent_out[u]:
                for v in self.ent_out[u][rel]:
                    print(u, v, rel)
        
    def transform_to_dnf(self):
        """
        This implementation is based on the algorithm proposed in Query2Box.
        Note that this might lead to redundant graphs, can we avoid this?
        """
        ent_in = defaultdict(lambda: defaultdict(set))

        targets = [n for n in self.nodes if self.is_sink_node(n)]
        assert len(targets) == 1
        target = targets[0]
        print("TARGET IS", target)
        for u in self.ent_out:
            for rel in self.ent_out[u]:
                for v in self.ent_out[u][rel]:
                    ent_in[v][rel].add(u)
        
        union_nodes = [x for x in self.nodes if 'UNION' in ent_in[x]]
        parnet_nodes = [ent_in[v]['UNION'] for v in union_nodes]

        def reverse_build(choice, it):
            print("\nREVERSE BUILD", it)
            print("-----------------------")
            q = queue.Queue()
            q.put(target)
            
            flag = {}
            sg_edges = defaultdict(lambda: defaultdict(set))
            while not q.empty():
                u = q.get()
                for rel in ent_in[u]:
                    flag[u] = True
                    print("FLAG",u, " Is True")
                    for v in ent_in[u][rel]:
                        if u in union_nodes:
                            if v not in choice:
                                continue
                            # merge union node and parent
                            sg_edges[v] = sg_edges[u]
                            sg_edges.pop(u)
                            q.put(v)
                        else:
                            sg_edges[v][rel].add(u)
                            q.put(v)

            # ret_nodes = set()
            ret_edges = defaultdict(lambda: defaultdict(set))
            relabel = lambda x: x if x not in flag else f"relab_{x}_{it}"
            for u in sg_edges:
                # ret_nodes.add(relabel(u))
                for rel in sg_edges[u]:
                    for v in sg_edges[u][rel]:
                        ret_edges[relabel(u)][rel].add(relabel(v))

            return ret_edges, relabel(target)

        all_triples = []
        for it, prod in enumerate(product(*parnet_nodes)):
            sg_edges, t = reverse_build(prod, it)
            for u in sg_edges:
                for rel in sg_edges[u]:
                    for v in sg_edges[u][rel]:
                        all_triples.append([u, rel, v])
                        print(u, v, rel)
            all_triples.append([t, 'UNION', target])
        
        return QueryDAG(self.manager, all_triples)
    
    def get_kgreasoning_format(self) -> tuple:
        """
        Build the query structure with current QueryDAG.
        returns:
            (query, query_structure)
        """
        def merge_incoming(msgs: list) -> tuple:
            union_flag = 0
            for msg in msgs:
                if msg[-1][-1] in ['u', -1]:
                    union_flag += 1
            assert union_flag == 0 or (
                union_flag == len(msgs) and union_flag > 1
            )
            if union_flag > 0:
                # transform for union operation (DNF)
                new_msgs = [(x[0], x[1][:-1]) for x in msgs]
                if msgs[0][-1][-1] == -1:
                    new_msgs.append((-1,))
                else:
                    new_msgs.append(('u',))
                return tuple(new_msgs)
            else:
                return msgs[0] if len(msgs) == 1 else tuple(msgs)

        
        def insert_relation(msg: tuple, rel) -> tuple:
            is_all_relation = True
            for x in msg[1]:
                if isinstance(x, tuple):
                    is_all_relation = False
                    break
            if is_all_relation:
                return (msg[0], (msg[1] + (rel,)))
            else:
                return (msg, (rel,))
        
        in_degs, out_degs = defaultdict(lambda: 0), defaultdict(lambda: 0)
        for u in self.nodes:
            for rel in self.ent_out[u]:
                for v in self.ent_out[u][rel]:
                    in_degs[v] += 1
                    out_degs[u] += 1

        flag = 0
        q = queue.Queue()
        for node in self.nodes:
            if out_degs[node] == 0:
                flag += 1
            if in_degs[node] == 0:
                q.put((node, 
                       (self.manager.node_data[node]['id'], ()), 
                       ('e', ())))
        # ensure there is only one sink-node
        assert flag == 1

        u_or_n = [0, 1]
        query_msg = defaultdict(lambda: list([]))
        struct_msg = defaultdict(lambda: list([]))
        while not q.empty():
            u, uq, us = q.get()

            for rel in self.ent_out[u]:
                if rel == 2: # intersection
                    for v in self.ent_out[u][rel]:
                        in_degs[v] -= 1
                        query_msg[v].append(uq)
                        struct_msg[v].append(us)
                        if in_degs[v] > 0:
                            continue
                        vq = merge_incoming(query_msg[v])
                        vs = merge_incoming(struct_msg[v])
                        q.put((v, vq, vs))

                else: # union / negation / relation 
                    if rel in u_or_n:
                        idx = u_or_n.index(rel)
                        rq, rs = [-1, -2][idx], ['u', 'n'][idx]
                    else:
                        rq, rs = self.manager.rel_data[rel]['id'], 'r'

                    for v in self.ent_out[u][rel]:
                        in_degs[v] -= 1
                        query_msg[v].append(insert_relation(uq, rq))
                        struct_msg[v].append(insert_relation(us, rs))
                        if in_degs[v] > 0:
                            continue
                        vq = merge_incoming(query_msg[v])
                        vs = merge_incoming(struct_msg[v])
                        q.put((v, vq, vs))
        return uq, us

    def negation(self) -> 'QueryDAG':
        ret_dag = QueryDAG(self.manager)
        ret_dag.nodes = copy.copy(self.nodes)
        sink_nodes = set([n for n in self.nodes if self.is_sink_node(n)])

        for u in self.nodes:
            for rel in self.ent_out[u]:
                for node in self.ent_out[u][rel]:
                    if node in sink_nodes:
                        node_negated = self.manager.get_variable(f"{node}_NEGATION")
                        ret_dag.ent_out[u][rel].add(node_negated)
                        # ret_dag.ent_out[u][rel].add(f"{node}_NEGATION")
                    else:
                        ret_dag.ent_out[u][rel].add(node)

        r_negation = self.manager.get_relation("NEGATION")
        for node in sink_nodes:
            node_negated = self.manager.get_variable(f"{node}_NEGATION")
            ret_dag.ent_out[node_negated][r_negation].add(node)
            ret_dag.nodes.add(node_negated)

        return ret_dag

    def is_sink_node(self, node) -> bool:
        for rel in self.ent_out[node]:
            if len(self.ent_out[node][rel]) > 0:
                return False
        return True

    @staticmethod
    def merge(data: Iterable['QueryDAG'], manager: 'MetaManager') -> 'QueryDAG':
        """
        Description:
        Merging multiple QueryDAGs together.
        **Intersection** and ~~Variable Propagation~~ is performed here.
        """
        ret_dag =  QueryDAG(manager)
        common_nodes = set.intersection(*[g.nodes for g in data])
        if len(common_nodes) != 1:
            raise NotImplementedError
        else:
            sink_node = list(common_nodes)[0]
            for g in data:
                if not g.is_sink_node(sink_node):
                    assert False, print("Common node in the DAGs must be a sink node")
        
        relabeled_nodes = []
        for i, graph in enumerate(data):
            for node in graph.nodes:
                for rel in graph.ent_out[node]:
                    ret_dag.ent_out[node][rel] = set.union(ret_dag.ent_out[node][rel],
                                                           graph.ent_out[node][rel])
                    # if sink_node in graph.ent_out[node][rel]:
                    #     sink_name = manager.node_data[sink_node]["name"]
                    #     relabeled_node = manager.get_variable(f"{sink_name}_RELABEL_{i}")
                    #     ret_dag.ent_out[node][rel].remove(sink_node)
                    #     ret_dag.ent_out[node][rel].add(relabeled_node)
                    #     relabeled_nodes.append(relabeled_node)
                    #     ret_dag.nodes.add(relabeled_node)
            ret_dag.nodes = set.union(ret_dag.nodes, graph.nodes)
        
        # r_instersection = manager.get_relation("INTERSECTION")
        # for node in relabeled_nodes:
        #     ret_dag.ent_out[node][r_instersection].add(sink_node)
        return ret_dag
        # ret_dag = QueryDAG(manager)
        # for graph in data:
        #     for node in graph.nodes:
        #         for rel in graph.ent_out[node]:
        #             ret_dag.ent_out[node][rel] = set.union(ret_dag.ent_out[node][rel],
        #                                                    graph.ent_out[node][rel])
        #     ret_dag.nodes = set.union(ret_dag.nodes, graph.nodes)
        # return ret_dag
    
    @staticmethod
    def union(data: Iterable['QueryDAG'], manager: 'MetaManager') -> 'QueryDAG':
        """
        Description:
        Logic union of multiple QueryDAGs.
        比较棘手的一点是，SPARQL查询本质是模式匹配，因此图中任何满足查询模式的结果都能作为答案。
        在这种逻辑下，UNION得到的是匹配到的子图的集合。
        但是一个QueryDAG代表一个查询子图的集合，如何对QueryDAG做UNION是一个问题。
        如果要满足GQE等工作所有查询都是有唯一的sink-node的假设，那么我们可以直接对sink-node加一条union边
        但是如何考虑我们可能会对多个variable进行union的问题？

        暂且先假设有一个唯一的sink node这种情况
        { foo r1 ?x. } UNION { bar r2 ?x . }
        Represented as:

        foo --r1--> ?x1
                       \\u
                        --> ?x
                       /u
        bar --r2--> ?x2 
        """
        ret_dag =  QueryDAG(manager)
        common_nodes = set.intersection(*[g.nodes for g in data])
        if len(common_nodes) != 1:
            raise NotImplementedError
        else:
            sink_node = list(common_nodes)[0]
            for g in data:
                if not g.is_sink_node(sink_node):
                    assert False, print("Common node in the DAGs must be a sink node")
        
        relabeled_nodes = []
        for i, graph in enumerate(data):
            for node in graph.nodes:
                for rel in graph.ent_out[node]:
                    ret_dag.ent_out[node][rel] = set.union(ret_dag.ent_out[node][rel],
                                                           graph.ent_out[node][rel])
                    if sink_node in graph.ent_out[node][rel]:
                        # relabeled_node = f"{sink_node}_RELABEL_{i}"
                        sink_name = manager.node_data[sink_node]["name"]
                        relabeled_node = manager.get_variable(f"{sink_name}_RELABEL_{i}")
                        ret_dag.ent_out[node][rel].remove(sink_node)
                        ret_dag.ent_out[node][rel].add(relabeled_node)
                        relabeled_nodes.append(relabeled_node)
                        ret_dag.nodes.add(relabeled_node)
            ret_dag.nodes = set.union(ret_dag.nodes, graph.nodes)
        
        r_union = manager.get_relation("UNION")
        for node in relabeled_nodes:
            ret_dag.ent_out[node][r_union].add(sink_node)
        return ret_dag

class MetaManager(object):
    def __init__(self, data_root, dataset) -> None:
        import os.path as osp
        data_path = osp.join(data_root, dataset)
        with open(osp.join(data_path, 'ent2id.pkl'), 'rb') as f:
            self.ent2id = pkl.load(f)
        with open(osp.join(data_path, 'rel2id.pkl'), 'rb') as f:
            self.rel2id = pkl.load(f)
        with open(osp.join(data_path, 'id2ent.pkl'), 'rb') as f:
            self.id2ent = pkl.load(f)
        with open(osp.join(data_path, 'id2rel.pkl'), 'rb') as f:
            self.id2rel = pkl.load(f)
        if dataset == 'FB15k':
            with open(osp.join(data_path, 'mp2rel.pkl'), 'rb') as f:
                self.mp2rel = pkl.load(f)
        self._node_alloc = -1
        self.node_data = []
        self.mp = {}
        self.dataset = dataset

        # self._rel_alloc = 1
        # self.rel_data = [-1, -2]
        # self.mp_rel = {"UNION": 0, "NEGATION": 1}
        self._rel_alloc = 5
        self.rel_data = [-1, -2, -3, -4, -5, -6]
        self.mp_rel = {"UNION": 0, "NEGATION": 1, "INTERSECTION": 2}
    
    def get_node_name(self, x):
        data = self.node_data[x]
        if data['type'] == 'anchor':
            return self.id2ent[data['id']], 'anchor'
        else:
            return data['name'], 'variable'

    def get_rel_name(self, x):
        logics = ["u", "n", "i"]
        if x < 3:
            return logics[x], 0
        data = self.rel_data[x]
        name = data["name"] if data['pos'] else data['name'] + "_reverse"
        return name, 1
    
    def get_anchor(self, name) -> int:
        if (name, 0) in self.mp:
            return self.mp[(name, 0)]
        self._node_alloc += 1
        self.node_data.append({
            'type': 'anchor',
            'id': self.ent2id[name],
        })
        self.mp[(name, 0)] = self._node_alloc
        return self._node_alloc

    def get_variable(self, name) -> int:
        if (name, 1) in self.mp:
            return self.mp[(name, 1)]
        self._node_alloc += 1
        self.node_data.append({
            'type': 'variable',
            'name': name,
        })
        self.mp[(name, 1)] = self._node_alloc
        return self._node_alloc

    def get_relation(self, _name, positive=True) -> int:
        if _name in ['UNION', 'NEGATION', 'INTERSECTION']:
            return self.mp_rel[_name]
        if self.dataset == 'FB15k':
            if positive:
                name = "pos." + _name
            else:
                name = "neg." + _name
            if name in self.mp_rel:
                return self.mp_rel[name]
            self._rel_alloc += 1
            self.rel_data.append({
                'name': _name,
                'id': self.rel2id[self.mp2rel[name]],
                'pos': positive
            })
            self.mp_rel[name] = self._rel_alloc
            return self._rel_alloc
        else: # NELL
            _name = _name.replace(".", ":")
            if not positive:
                name = _name + "_reverse"
            else:
                name = _name
            if name in self.mp_rel:
                return self.mp_rel[name]
            self._rel_alloc += 1
            self.rel_data.append({
                'name': _name,
                'id': self.rel2id[name],
                'pos': positive
            })
            self.mp_rel[name] = self._rel_alloc
            return self._rel_alloc
    
    def reverse_relation(self, rid:int) -> int:
        if not isinstance(rid, int):
            raise ValueError("id must be integer")
        if rid <= 2:
            return rid + 3 # reverse i / u / n
        if rid < 6 or rid >= len(self.rel_data):
            raise ValueError(f"invalid id={rid}")
        data = self.rel_data[rid]
        return self.get_relation(data['name'], not data['pos'])

class QueryParser(object):
    def __init__(self, manager, dm=False):
        self.contain_union = None
        self.manager = manager
        self.dm = dm

    def _extract_variable(self, x) -> str:
        if isinstance(x, dict):
            val = x['localname']
            if self.manager.dataset == 'FB15k':
                val = "/" + val.replace('.', '/')
            return self.manager.get_anchor(val)
            # return self.ent2id[val]
            # return Grounded(val)
        elif isinstance(x, str):
            return self.manager.get_variable(str(x))
            # return Variable(str(x))
        else:
            raise NotImplementedError
        
    def _extract_relation(self, x) -> str:
        val =  x['part'][0]['part'][0]['part']['localname']
        return self.manager.get_relation(val)
        # return self.rel2id[self.mp2rel[val]]
    
    def _extract_projection(self, result) -> str:
        return str(result['projection'][0]['var'])

    def _parse_SubSelect(self, ss: CompValue) -> 'QueryDAG':
        # projection_target = self._extract_projection(ss)
        assert ss['where'].name == 'GroupGraphPatternSub'
        return self._parse_GroupGraphPatternSub(ss['where'])
    
    def _parse_GroupOrUnionGraphPattern(self, gougp: CompValue) -> 'QueryDAG':
        union_flag = len(gougp['graph'])

        all_dag = []
        for graph in gougp['graph']:
            if graph.name == 'SubSelect':
                sub_dag = self._parse_SubSelect(graph)
            elif graph.name == 'GroupGraphPatternSub':
                union_flag -= 1
                sub_dag = self._parse_GroupGraphPatternSub(graph)
            else:
                raise NotImplementedError
            all_dag.append(sub_dag)

        if union_flag == 0 and len(gougp['graph']) != 1: # all GroupGraphPatternSub and we should do union
            return QueryDAG.union(all_dag, self.manager)
        else:
            # 如果长度不是1，又不是or，那么意义不明
            assert len(all_dag) == 1
            return all_dag[0]
            
    def _parse_Filter(self, filt: CompValue) -> 'QueryDAG':
        # only support negation at this time
        assert len(filt['expr']) == 1 and \
            filt['expr'].name == 'Builtin_NOTEXISTS'
        assert filt['expr']['graph'].name == 'GroupGraphPatternSub'
        dag = self._parse_GroupGraphPatternSub(
            filt['expr']['graph']
        )
        return dag.negation()
    
    def _parse_TriplesBlock(self, triples: CompValue) -> 'QueryDAG':
        extracted_triples = []
        for triple in triples['triples']:
            s = self._extract_variable(triple[0])
            r = self._extract_relation(triple[1])
            o = self._extract_variable(triple[2])
            extracted_triples.append([s, r, o])
        
        return QueryDAG(self.manager, extracted_triples)

    def _parse_GroupGraphPatternSub(self, ggps: CompValue) -> 'QueryDAG':
        """
        input: GroupGraphPatternSub in a parse result
        output:
            tuple: query_of_all_variables structure_of_all_variables
        """
        all_dag = []
        for part in ggps['part']:
            if part.name == 'TriplesBlock':
                sub_dag = self._parse_TriplesBlock(part)
            elif part.name == 'GroupOrUnionGraphPattern':
                sub_dag = self._parse_GroupOrUnionGraphPattern(part)
            elif part.name == 'Filter':
                sub_dag = self._parse_Filter(part)
            all_dag.append(sub_dag)
        
        if len(all_dag) == 1:
            return all_dag[0]
        else:
            return QueryDAG.merge(all_dag, self.manager)

    def parse(self, query_str: str) -> tuple:
        self.contain_union = False
        parse_result = parser.parseQuery(query_str)
        limit_entry = parse_result[1].get('limitoffset', None)
        nlim = 100
        if limit_entry != 'limitoffset':
            nlim = int(limit_entry['limit'])
        # print(prettify_parsetree(parse_result))
        assert list(parse_result[0]) == []
        target = self._extract_projection(parse_result[1])
        assert parse_result[1]['where'].name == 'GroupGraphPatternSub'
        dag = self._parse_GroupGraphPatternSub(
            parse_result[1]['where'])
        dag.print()
        print("-------------------------------")
        dag = adjust(dag, target, self.manager)
        dag.print()
        print("-------------------------------")
        if self.dm:
            dag = adjust_dm(dag)
            dag.print()
            print("-------------------------------")
        # dag = dag.transform_to_dnf()
        query, query_structure = dag.get_kgreasoning_format()
        return query, query_structure, dag.export_plan(), nlim
    
    # def parse(self, query_str: str) -> QueryDAG:
    #     try:
    #         parse_result = parser.parseQuery(query_str)
    #     except Exception as e:
    #         print("Invalid sparql query!")
    #     assert parse_result[1].name == 'SelectQuery'
    #     dag = self._parse_GroupGraphPatternSub(
    #         parse_result[1]['where'])
    #     return dag

if __name__ == '__main__':
    # query_str = """
    # SELECT ?o WHERE
    # {
    # ?u :people.person.gender :m.05zppz.
    # ?u :award.award_winner.awards_won..award.award_honor.honored_for ?o .
    # }
    # """

    # query_str = """
    # SELECT ?actor WHERE
    # {
    #     {
    #         SELECT ?film WHERE {
    #             { :m.06pj8 :film.director.film ?film . }
    #             UNION
    #             { :m.03_gd :film.director.film ?film . }
    #         }
    #     }
    #     ?actor :film.actor.film..film.performance.film ?film .
    # }
    # """

    query_str = """
    SELECT ?actor WHERE
    {
        {
            SELECT ?film WHERE {
                { :m.06pj8 :film.director.film ?film . }
                UNION
                { :m.03_gd :film.director.film ?film . }
            }
        }
        ?actor :film.actor.film..film.performance.film ?film .
    }
    LIMIT 50
    """

    manager = MetaManager('../data', 'FB15k')
    query_parser = QueryParser(manager, True)
    q, qs, plan, nlim = query_parser.parse(query_str)
    print(q, qs, plan, nlim)