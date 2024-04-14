import argparse
import os.path as osp
import pickle as pkl
import time

from rdflib import Graph, URIRef, Namespace
from tqdm import tqdm

def load_edges(g, ns, id2ent, id2rel, data_path, dataset, file):
    with open(osp.join(data_path, dataset, file)) as f:
        for i, line in enumerate(f):
            if len(line) == 0:
                continue
            e1, rel, e2 = line.split('\t')
            e1 = id2ent[int(e1.strip())]
            rel = id2rel[int(rel.strip())]
            e2 = id2ent[int(e2.strip())]
            if dataset == 'FB15k':
                if rel[0] != '+':
                    continue
                e1 = ns[e1[1:].replace('/', '.')]
                rel = ns[rel[2:].replace('/', '.')]
                e2 = ns[e2[1:].replace('/', '.')]
                g.add((e1, rel, e2))
            else: # NELL
                if '_reverse' in rel:
                    continue
                if ',' in e1 or ',' in e2:
                    continue
                e1 = ns[e1]
                rel = ns[rel.replace(':', '.')]
                e2 = ns[e2]
                g.add((e1, rel, e2))


def get_rdf_graph(data_path, dataset, mode='train'):
    g = Graph()
    rdf_path = osp.join(data_path, dataset, f'graph_{mode}.nt')
    t0 = time.time()
    if osp.exists(rdf_path):
        g.parse(rdf_path, format="nt")
        print("Loading the graph takes", time.time() - t0, "seconds.")
    else:
        with open(osp.join(data_path, dataset, 'id2ent.pkl'), 'rb') as f:
            id2ent = pkl.load(f)
        with open(osp.join(data_path, dataset, 'id2rel.pkl'), 'rb') as f:
            id2rel = pkl.load(f)

        ns = Namespace('http://www.example.com/ns/')
        load_edges(g, ns, id2ent, id2rel, data_path, dataset, 'train_bidir.txt')
        if mode == 'test':
            load_edges(g, ns, id2ent, id2rel, data_path, dataset, 'valid_bidir.txt')
            load_edges(g, ns, id2ent, id2rel, data_path, dataset, 'test_bidir.txt')
        # with open(osp.join(data_path, dataset, 'train_bidir.txt')) as f:
        #     for i, line in enumerate(f):
        #         if len(line) == 0:
        #             continue
        #         e1, rel, e2 = line.split('\t')
        #         e1 = id2ent[int(e1.strip())]
        #         rel = id2rel[int(rel.strip())]
        #         e2 = id2ent[int(e2.strip())]
        #         if dataset == 'FB15k':
        #             if rel[0] != '+':
        #                 continue
        #             e1 = ns[e1[1:].replace('/', '.')]
        #             rel = ns[rel[2:].replace('/', '.')]
        #             e2 = ns[e2[1:].replace('/', '.')]
        #             g.add((e1, rel, e2))
        #         else: # NELL
        #             if '_reverse' in rel:
        #                 continue
        #             if ',' in e1 or ',' in e2:
        #                 continue
        #             e1 = ns[e1]
        #             rel = ns[rel.replace(':', '.')]
        #             e2 = ns[e2]
        #             g.add((e1, rel, e2))
        
        # if mode == 'test':
        #     with open(osp.join(data_path, dataset, 'valid_bidir.txt')) as f:
        #         for i, line in enumerate(f):
        #             if len(line) == 0:
        #                 continue
        #             e1, rel, e2 = line.split('\t')
        #             e1 = id2ent[int(e1.strip())]
        #             rel = id2rel[int(rel.strip())]
        #             if rel[0] != '+':
        #                 continue
        #             e2 = id2ent[int(e2.strip())]
        #             e1 = ns[e1[1:].replace('/', '.')]
        #             rel = ns[rel[2:].replace('/', '.')]
        #             e2 = ns[e2[1:].replace('/', '.')]
        #             g.add((e1, rel, e2))

        #     with open(osp.join(data_path, dataset, 'test_bidir.txt')) as f:
        #         for i, line in enumerate(f):
        #             if len(line) == 0:
        #                 continue
        #             e1, rel, e2 = line.split('\t')
        #             e1 = id2ent[int(e1.strip())]
        #             rel = id2rel[int(rel.strip())]
        #             if rel[0] != '+':
        #                 continue
        #             e2 = id2ent[int(e2.strip())]
        #             e1 = ns[e1[1:].replace('/', '.')]
        #             rel = ns[rel[2:].replace('/', '.')]
        #             e2 = ns[e2[1:].replace('/', '.')]
        #             g.add((e1, rel, e2))
        
        print("Building the graph takes", time.time() - t0, "seconds.")
        g.serialize(rdf_path, format='nt')
    return g

def exec_rdflib_query(rdf_graph, query_str):
    query_str.replace("SELECT", "SELECT DISTINCT")
    processed = 'PREFIX : <http://www.example.com/ns/> \n' + query_str

    res = []
    for x in rdf_graph.query(processed):
        ent = x[0][len("http://www.example.com/ns"):]
        ent = ent.replace(".", "/")
        res.append(ent)
    return res

