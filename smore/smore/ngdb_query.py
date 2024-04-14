import numpy as np
import torch
import torch.distributions.kl as torch_kl
import time

from smore.common.util import flatten_query, list2tuple, parse_time, set_global_seed, eval_tuple, construct_graph, tuple2filterlist, maybe_download_dataset, flatten
from itertools import zip_longest
from smore.common.torchext.dist_func.beta_dist import BetaDist


def padding_length(r1, r2):
    return list(zip_longest(r1, r2))

def ranking_box(entity_embedding, query_embedding, query_offset):
    query_embedding = torch.squeeze(query_embedding, 0)
    query_embedding = torch.squeeze(query_embedding, 1)
    query_offset = torch.squeeze(query_offset, 0)
    query_offset = torch.squeeze(query_offset, 1)
    dists = []
    # to support union queries, calculate each querie's distance
    for i in range(query_embedding.shape[0]):
        delta = (entity_embedding - query_embedding[i]).abs()
        distance_out = torch.nn.functional.relu(delta - query_offset[i])
        distance_in = torch.min(delta, query_offset[i])
        # should we modify this distance function?
        dist = (torch.norm(distance_out, p=1, dim=-1) + 0.02 * torch.norm(distance_in, p=1, dim=-1)).cpu().detach().tolist()
        dists.extend([(idx, d) for (idx, d) in enumerate(dist)])
    dists = sorted(dists, key=lambda x: x[1])
    occurance = set()
    rankings = []
    for idx, d in dists:
        if idx not in occurance:
            rankings.append(idx)
            occurance.add(idx)
    assert len(rankings) == entity_embedding.shape[0]
    return rankings

def ranking_beta(entity_embedding, query_embedding):
    t0 = time.time()
    alpha_embedding, beta_embedding = torch.chunk(entity_embedding.unsqueeze(1), 2, dim=-1)
    entity_dist = BetaDist(alpha_embedding, beta_embedding)
    query_dist = BetaDist(*query_embedding)
    t1 = time.time()
    kld = torch_kl._kl_beta_beta(entity_dist, query_dist)
    dist = torch.norm(kld, p=1, dim=-1).squeeze().cpu().detach().numpy()
    t2 = time.time()
    # print(dist.shape)
    # rankings = list(range(len(dist)))
    # rankings = sorted(rankings, key=lambda x: dist[x])
    rankings = np.argsort(np.argsort(dist))
    t3 = time.time()
    print("t1 - t0", t1 - t0)
    print("t2 - t1", t2 - t1)
    print("t3 - t2", t3 - t2)
    return rankings

def exec_query(model, entity_embedding, parser, id2ent, query_str, mode='box'):
    query, query_structure, query_plan, n_lim = parser.parse(query_str)
    print(query)
    print(query_structure)
    queries = torch.LongTensor([flatten(query)]).cuda()

    if mode == 'box':
        with torch.no_grad():
            [query_embedding, query_offset] = model.inference(query_structure, queries, torch.device('cuda:0'))
        rankings = ranking_box(entity_embedding, query_embedding, query_offset)
    else:
        t0 = time.time()
        with torch.no_grad():
            query_embedding = model.inference(query_structure, queries, torch.device('cuda:0'))
        t1 = time.time()
        rankings = ranking_beta(entity_embedding, query_embedding)
    result = list(map(lambda x: id2ent[x], rankings))[:n_lim]
    return result, query_plan

def exec_query_dag(model, entity_embedding, dag, id2ent, mode='box'):
    query, query_structure = dag.get_kgreasoning_format()
    queries = torch.LongTensor([flatten(query)]).cuda()

    if mode == 'box':
        with torch.no_grad():
            [query_embedding, query_offset] = model.inference(query_structure, queries, torch.device('cuda:0'))
        rankings = ranking_box(entity_embedding, query_embedding, query_offset)
    else:
        t0 = time.time()
        with torch.no_grad():
            query_embedding = model.inference(query_structure, queries, torch.device('cuda:0'))
        t1 = time.time()
        rankings = ranking_beta(entity_embedding, query_embedding)
    result = list(map(lambda x: id2ent[x], rankings))
    return result