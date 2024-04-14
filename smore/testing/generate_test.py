import os.path as osp
import pickle as pkl
import numpy as np
import argparse

rdf_templates = {}
smore_templates = {}
# 1p
rdf_templates['1p'] = """
    PREFIX ns: <http://rdf.freebase.com/ns/>
    SELECT ?o
    WHERE {{
        ns:{} ns:{} ?o .
    }}
"""

smore_templates['1p'] = """
    SELECT ?o WHERE
    {{
        :{} :{} ?o .
    }}
"""

# 2p
rdf_templates['2p'] = """
    PREFIX ns: <http://rdf.freebase.com/ns/>
    SELECT ?o
    WHERE {{
        ns:{} ns:{} ?u .
        ?u ns:{} ?o .
    }}
"""

smore_templates['2p'] = """
    SELECT ?o WHERE
    {{
        :{} :{} ?u .
        ?u :{} ?o .
    }}
"""

# 3p
rdf_templates['3p'] = """
    PREFIX ns: <http://rdf.freebase.com/ns/>
    SELECT ?o
    WHERE {{
        ns:{} ns:{} ?u .
        ?u ns:{} ?v .
        ?v ns:{} ?o .
    }}
"""

smore_templates['3p'] = """
    SELECT ?o WHERE
    {{
        :{} :{} ?u .
        ?u :{} ?v .
        ?v :{} ?o .
    }}
"""

# 2i
rdf_templates['2i'] = """
    PREFIX ns: <http://rdf.freebase.com/ns/>
    SELECT ?o
    WHERE {{
        ns:{} ns:{} ?o .
        ns:{} ns:{} ?o .
    }}
"""

smore_templates['2i'] = """
    SELECT ?o WHERE
    {{
        :{} :{} ?o .
        :{} :{} ?o .
    }}
"""

# 3i
rdf_templates['3i'] = """
    PREFIX ns: <http://rdf.freebase.com/ns/>
    SELECT ?o
    WHERE {{
        ns:{} ns:{} ?o .
        ns:{} ns:{} ?o .
        ns:{} ns:{} ?o .
    }}
"""

smore_templates['3i'] = """
    SELECT ?o WHERE
    {{
        :{} :{} ?o .
        :{} :{} ?o .
        :{} :{} ?o .
    }}
"""

# ip
rdf_templates['ip'] = """
    PREFIX ns: <http://rdf.freebase.com/ns/>
    SELECT ?o
    WHERE {{
        ns:{} ns:{} ?u .
        ns:{} ns:{} ?u .
        ?u ns:{} ?o .
    }}
"""

smore_templates['ip'] = """
    SELECT ?o WHERE
    {{
        :{} :{} ?u .
        :{} :{} ?u .
        ?u :{} ?o .
    }}
"""

# pi
rdf_templates['pi'] = """
    PREFIX ns: <http://rdf.freebase.com/ns/>
    SELECT ?o
    WHERE {{
        ns:{} ns:{} ?u .
        ?u ns:{} ?o .
        ns:{} ns:{} ?o .
    }}
"""

smore_templates['pi'] = """
    SELECT ?o WHERE
    {{
        :{} :{} ?u .
        ?u :{} ?o .
        :{} :{} ?o .
    }}
"""

# 2u
rdf_templates['2u'] = """
    PREFIX ns: <http://rdf.freebase.com/ns/>
    SELECT ?o
    WHERE {{
        {{ ns:{} ns:{} ?o . }}
        UNION
        {{ ns:{} ns:{} ?o . }}
    }}
"""

smore_templates['2u'] = """
    SELECT ?o WHERE
    {{
        {{ :{} :{} ?o . }}
        UNION
        {{ :{} :{} ?o . }}
    }}
"""

# up
rdf_templates['up'] = """
    PREFIX ns: <http://rdf.freebase.com/ns/>
    SELECT ?o
    WHERE {{
        {{
            SELECT ?v WHERE {{
                {{ ns:{} ns:{} ?v . }}
                UNION
                {{ ns:{} ns:{} ?v . }}
            }}
        }}
        ?v ns:{} ?o .
    }}
"""

smore_templates['up'] = """
    SELECT ?o WHERE
    {{
        {{
            SELECT ?v WHERE {{
                {{ :{} :{} ?v . }}
                UNION
                {{ :{} :{} ?v . }}
            }}
        }}
        ?v :{} ?o .
    }}
"""

def fill_name(query, id2ent, id2rel, rel2mp):
    res = ()
    is_all_relation = True
    for x in query:
        if isinstance(x, tuple):
            is_all_relation = False
            break
    if is_all_relation:
        return tuple(rel2mp[id2rel[x]] for x in query if x != -1)
    else:
        for x in query:
            if isinstance(x, tuple):
                res += fill_name(x, id2ent, id2rel, rel2mp)
            else:
                res += (id2ent[x][1:].replace('/', '.'),)
    return res

def main(args):
    if args.do_name_mapping:
        rel2mp = {}
        mp2rel = {}
        with open(osp.join(args.data_path, 'rel2id.pkl'), 'rb') as f:
            rel2id = pkl.load(f)
        for rel in rel2id:
            if rel[0] == '+':
                mapped = 'pos' + rel[1:].replace('/', '.')
            elif rel[0] == '-':
                mapped = 'neg' + rel[1:].replace('/', '.')
            else:
                raise NotImplementedError
            rel2mp[rel] = mapped
            mp2rel[mapped] = rel
        with open(osp.join(args.data_path, 'rel2mp.pkl'), 'wb') as f:
            pkl.dump(rel2mp, f, pkl.HIGHEST_PROTOCOL)
        with open(osp.join(args.data_path, 'mp2rel.pkl'), 'wb') as f:
            pkl.dump(mp2rel, f, pkl.HIGHEST_PROTOCOL)
    else:
        with open(osp.join(args.data_path, 'rel2mp.pkl'), 'rb') as f:
            rel2mp = pkl.load(f)
        with open(osp.join(args.data_path, 'mp2rel.pkl'), 'rb') as f:
            mp2rel = pkl.load(f)
    
    tasks = args.tasks.split(',')
    with open(osp.join(args.data_path, 'id2ent.pkl'), 'rb') as f:
        id2ent = pkl.load(f)
    with open(osp.join(args.data_path, 'id2rel.pkl'), 'rb') as f:
        id2rel = pkl.load(f)

    all_query_tuples = {}
    all_answers = {}
    for qtype in tasks:
        with open(osp.join(args.data_path, f'test-{qtype}-answers.pkl'), 'rb') as f:
            answers = pkl.load(f)
        answer_size = []
        answer_key = []
        for key in answers:
            answer_size.append(len(answers[key]))
            answer_key.append(key)

        if args.weighted_sampling:
            selected_offset = np.random.choice(np.arange(len(answer_size)), size=args.num_samples, p=(answer_size / np.sum(answer_size)), replace=False)
        else:
            selected_offset = np.random.choice(np.arange(len(answer_size)), size=args.num_samples, replace=False)
        selected = selected_offset.tolist()
        all_query_tuples[qtype] = [answer_key[x] for x in selected]
        all_answers[qtype] = [answers[k] for k in all_query_tuples[qtype]]

    rdf_queries = {}
    smore_queries = {}
    for qtype in tasks:
        rdf_temp = []
        smore_temp = []
        for query in all_query_tuples[qtype]:
            data = fill_name(query, id2ent, id2rel, rel2mp)
            rdf_temp.append(rdf_templates[qtype].format(*data))
            smore_temp.append(smore_templates[qtype].format(*data))
        rdf_queries[qtype] = rdf_temp
        smore_queries[qtype] = smore_temp

    with open(osp.join(args.data_path, 'rdf_queries.pkl'), 'wb') as f:
        pkl.dump(rdf_queries, f, pkl.HIGHEST_PROTOCOL)
    with open(osp.join(args.data_path, 'smore_queries.pkl'), 'wb') as f:
        pkl.dump(smore_queries, f, pkl.HIGHEST_PROTOCOL)
    with open(osp.join(args.data_path, 'all_answers.pkl'), 'wb') as f:
        pkl.dump(all_answers, f, pkl.HIGHEST_PROTOCOL)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='generate_test', 
                                     description='Generating test samples for rdflib and smore')
    parser.add_argument('-mr', '--do_name_mapping', action='store_true')
    parser.add_argument('-t', '--tasks', type=str, default='1p,2p,3p,2i,3i,ip,pi')
    parser.add_argument('-p', '--data_path', type=str, default='/home/lousy/smore/data/FB15k')
    parser.add_argument('-n', '--num_samples', type=int, default=1000)
    parser.add_argument('--weighted_sampling', action='store_true')
    args = parser.parse_args()
    main(args)
