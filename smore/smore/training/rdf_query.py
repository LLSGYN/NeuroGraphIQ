import argparse
import os.path as osp
import pickle as pkl
import time

from rdflib import Graph, URIRef, Namespace
# from rdflib.namespace import FOAF, RDF
from tqdm import tqdm

def get_rdf_triples(data_path):
    g = Graph()
    rdf_path = osp.join(data_path, 'graph.ttl')
    t0 = time.time()
    if osp.exists(rdf_path) and False:
        g.parse(rdf_path)
        print("Loading the graph takes", time.time() - t0, "seconds.")
    else:
        with open(osp.join(data_path, 'id2ent.pkl'), 'rb') as f:
            id2ent = pkl.load(f)
        with open(osp.join(data_path, 'id2rel.pkl'), 'rb') as f:
            id2rel = pkl.load(f)
        with open(osp.join(data_path, 'rel2mp.pkl'), 'rb') as f:
            rel2mp = pkl.load(f)

        ns = Namespace('http://rdf.freebase.com/ns/')
        # ns = Namespace("/")
        with open(osp.join(data_path, 'train_bidir.txt')) as f:
            for i, line in enumerate(f):
                if len(line) == 0:
                    continue
                e1, rel, e2 = line.split('\t')
                e1 = id2ent[int(e1.strip())]
                rel = id2rel[int(rel.strip())]
                if rel[0] != '+':
                    continue
                e2 = id2ent[int(e2.strip())]
                e1 = ns[e1[1:].replace('/', '.')]
                rel = ns[rel[2:].replace('/', '.')]
                # rel = ns[rel2mp[rel]]
                e2 = ns[e2[1:].replace('/', '.')]
                g.add((e1, rel, e2))
        print("Building the graph takes", time.time() - t0, "seconds.")
        # g.serialize(rdf_path, format='turtle')
    return g

def main():
    data_path = '/home/lousy/smore/data/FB15k'
    g = get_rdf_triples(data_path)

    query_str = """
    PREFIX : <http://rdf.freebase.com/ns/>
    SELECT ?o WHERE
    {
        ?u :people.person.gender :m.05zppz .
        ?u :award.award_winner.awards_won..award.award_honor.honored_for ?o .
    }
    """
    # res = []
    # for x in g.query(query_str):
    #     print(x[0])
        # res.append(x[0].replace(".", "/"))
    # with open(osp.join(data_path, 'rdf_queries.pkl'), 'rb') as f:
    #     queries = pkl.load(f)
    # with open(osp.join(data_path, 'ent2id.pkl'), 'rb') as f:
    #     ent2id = pkl.load(f)

    # query_types = args.tasks.split(',')
    # total_results = {}
    # for qtype in query_types:
    #     total_time = 0
    #     print("------------------------------")
    #     print(queries[qtype][0])
    #     total_results[qtype] = []
    #     for q in tqdm(queries[qtype]):
    #         t0 = time.time()
    #         results = [r for r in g.query(q)]
    #         t1 = time.time()
    #         total_time += time.time() - t0
    #         # results = [r[0].replace('http://rdf.freebase.com/ns', '') for r in results]
    #         results = [ent2id[r.replace('.', '/')] for r in results]
    #         total_results[qtype].append(results)
    #     print(f"avg {qtype} query time", total_time / len(total_results[qtype]))

    # with open(osp.join(data_path, 'rdf_results.pkl'), 'wb') as f:
    #     pkl.dump(total_results,  f, pkl.HIGHEST_PROTOCOL)

if __name__ == '__main__':
    # parser = argparse.ArgumentParser(description='Test on rdflib.')
    # parser.add_argument('-t', '--tasks', type=str, default='1p,2p,3p,2i,3i,ip,pi')
    # parser.add_argument('-p', '--data_path', type=str, default='/home/lousy/smore/data/FB15k')
    # args = parser.parse_args()
    main()