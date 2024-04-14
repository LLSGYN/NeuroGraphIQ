# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import json
import logging
import os
import random

import numpy as np
import torch
import time
import pickle
import rdflib

from collections import defaultdict
from tqdm import tqdm
from tensorboardX import SummaryWriter, GlobalSummaryWriter
import torch.multiprocessing as mp
import math

from smore.models import build_model
from smore.common.util import flatten_query, list2tuple, parse_time, set_global_seed, eval_tuple, construct_graph, tuple2filterlist, maybe_download_dataset, flatten
from smore.common.config import parse_args, all_tasks, query_name_dict, name_query_dict
from smore.common.embedding.embed_optimizer import get_optim_class
from smore.cpp_sampler.sampler_clib import KGMem
from smore.training.train_process import async_aggr, train_mp
from smore.evaluation.dataloader import MultihopTestDataset, Test1pDataset, Test1pBatchDataset
# from smore.ngdb.util import generate_query, Stats
# from query_parser import QueryParser

from collections import namedtuple
QueryData = namedtuple('QueryData', ['data', 'buffer', 'writer_buffer'])


def setup_train_mode(args):
    tasks = args.tasks.split('.')
    if args.training_tasks is None:
        args.training_tasks = args.tasks
    training_tasks = args.training_tasks.split('.')
    
    if args.online_sample:
        if eval_tuple(args.online_sample_mode)[3] == 'wstruct':
            normalized_structure_prob = np.array(eval_tuple(args.online_weighted_structure_prob)).astype(np.float32)
            normalized_structure_prob /= np.sum(normalized_structure_prob)
            normalized_structure_prob = normalized_structure_prob.tolist()
            assert len(normalized_structure_prob) == len(training_tasks)
        else:
            normalized_structure_prob = [1/len(training_tasks)] * len(training_tasks)
        args.normalized_structure_prob = normalized_structure_prob
        train_dataset_mode, sync_steps, sparse_embeddings, async_optim, merge_mode = eval_tuple(args.train_online_mode)
        update_mode, optimizer_name, optimizer_device, squeeze_flag, queue_size = eval_tuple(args.optim_mode)
        assert train_dataset_mode in ['single'], "mix has been deprecated"
        assert update_mode in ['aggr'], "fast has been deprecated"
        assert optimizer_name in ['adagrad', 'rmsprop', 'adam']
        args.sync_steps = sync_steps
        args.async_optim = async_optim
        args.merge_mode = merge_mode
        args.sparse_embeddings = sparse_embeddings
        args.sparse_device = optimizer_device
        args.train_dataset_mode = train_dataset_mode


def setup_save_path(args):
    cur_time = parse_time()
    if args.prefix is None:
        prefix = 'logs'
    else:
        prefix = args.prefix
    print("overwritting args.save_path")
    args.save_path = os.path.join(prefix, args.data_path.split('/')[-1], "{}-{}".format(args.training_tasks, args.tasks), args.geo)
    if args.geo in ['box']:
        tmp_str = "g-{}-mode-{}".format(args.gamma, args.box_mode)
    elif args.geo in ['vec']:
        tmp_str = "g-{}".format(args.gamma)
    elif args.geo == 'beta':
        tmp_str = "g-{}-mode-{}".format(args.gamma, args.beta_mode)
    elif args.geo == 'rotate':
        tmp_str = "g-{}-mode-{}".format(args.gamma, args.rotate_mode)
    elif args.geo == 'distmult':
        tmp_str = "g-{}-mode-{}".format(args.gamma, args.distmult_mode)
    elif args.geo == 'complex':
        tmp_str = "g-{}-mode-{}".format(args.gamma, args.complex_mode)
    else:
        tmp_str = "g-{}-mode-{}".format(args.gamma, args.model_config)
    if args.negative_adversarial_sampling:
        tmp_str += '-adv-{}'.format(args.adversarial_temperature)
    if args.reg_coeff != 0:
        tmp_str += '-reg-{}'.format(args.reg_coeff)
    tmp_str += '-ngpu-{}'.format(args.gpus)

    if args.online_sample:
        tmp_str += '-os-{}'.format(args.online_sample_mode)
        if eval_tuple(args.online_sample_mode)[3] == 'wstruct':
            tmp_str += '-({})'.format(",".join(["%.2f"%i for i in args.normalized_structure_prob]))

        tmp_str += '-dataset-{}'.format(args.train_online_mode)
        tmp_str += '-opt-{}'.format(args.optim_mode)
        if args.share_negative:
            tmp_str += '-sharen' 
        tmp_str += '-%s' % args.sampler_type
    tmp_str += '-lr_%s' % args.lr_schedule
    if args.checkpoint_path is not None:
        # args.save_path = args.checkpoint_path
        args.save_path = os.path.join(args.save_path, tmp_str, "deploy", cur_time)
    else:
        args.save_path = os.path.join(args.save_path, tmp_str, cur_time)

    if not os.path.exists(args.save_path):
        os.makedirs(args.save_path)

    print ("logging to", args.save_path)


def set_logger(args):
    '''
    Write logs to console and log file
    '''
    if args.do_train:
        log_file = os.path.join(args.save_path, 'train.log')
    else:
        log_file = os.path.join(args.save_path, 'test.log')

    logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(message)s',
        level=logging.INFO,
        datefmt='%Y-%m-%d %H:%M:%S',
        filename=log_file,
        filemode='a+'
    )
    if args.print_on_screen:
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
        console.setFormatter(formatter)
        logging.getLogger('').addHandler(console)

    if not args.do_train: # if not training, then create tensorboard files in some tmp location
        test_name = args.eval_path.split('/')[-1]
        writer = SummaryWriter(os.path.join(args.save_path, test_name))
    else:
        writer = SummaryWriter(args.save_path)
    return writer


def get_model(args):
    with open('%s/stats.txt'%args.data_path) as f:
        entrel = f.readlines()
        nentity = int(entrel[0].split(' ')[-1])
        nrelation = int(entrel[1].split(' ')[-1])
    
    args.nentity = nentity
    args.nrelation = nrelation    
    model = build_model(args, nentity, nrelation, query_name_dict)
    EmbedOpt = get_optim_class(args)
    EmbedOpt.prepare_optimizers(args, [x[1] for x in model.named_sparse_embeddings()])
    gpus = [int(i) for i in args.gpus.split(".")]

    logging.info('-------------------------------'*3)
    logging.info('Model Parameter Configuration:')
    num_params = 0
    for name, param in model.named_parameters():
        logging.info('Parameter %s: %s, require_grad = %s' % (name, str(param.size()), str(param.requires_grad)))
        if param.requires_grad:
            num_params += np.prod(param.size())
    logging.info('Parameter Number: %d' % num_params)
    if args.geo == 'box':
        logging.info('box mode = %s' % args.box_mode)
    elif args.geo == 'beta':
        logging.info('beta mode = %s' % args.beta_mode)
    return model


def try_load_checkpoint(args, model):
    init_step = 0
    current_learning_rate = args.learning_rate
    warm_up_steps = args.max_steps // 2
    optimizer_stats = None
    if args.checkpoint_path is not None:
        logging.info('Loading checkpoint %s...' % args.checkpoint_path)
        checkpoint = torch.load(os.path.join(args.checkpoint_path, 'checkpoint'), map_location='cpu')
        init_step = checkpoint['step']
        missing, unexpected = model.load_state_dict(checkpoint['model_state_dict'], strict=False)
        logging.info("Missing keys: %s" % (str(missing)))
        logging.info("Unexpected keys: %s" % (str(unexpected)))

        if args.do_train:
            current_learning_rate = checkpoint['current_learning_rate']
            warm_up_steps = checkpoint['warm_up_steps']
            optimizer_stats = checkpoint['optimizer_state_dict']
    else:
        logging.info('Randomly Initializing %s Model...' % args.geo)
    opt_stats = {
        'init_step': init_step,
        'warm_up_steps': warm_up_steps,
        'current_learning_rate': current_learning_rate,
        'optimizer_stats': optimizer_stats
    }
    return opt_stats


def load_1p_eval_data(args, phase):
    logging.info("loading %s data for link pred" % phase)
    all_data = torch.load(os.path.join(args.eval_path, "%s.pt" % phase))
    if 'head_neg' in all_data:  # bi-directional
        logging.info('evaluating bi-directional 1p')
        fwd_data = {'head': all_data['head'],
                    'relation': all_data['relation'] * 2,
                    'tail': all_data['tail']}
        if 'tail_neg' in all_data:
            fwd_data['tail_neg'] = all_data['tail_neg']
        backwd_data = {'head': all_data['tail'],
                    'relation': all_data['relation'] * 2 + 1,
                    'tail': all_data['head']}
        if 'head_neg' in backwd_data:
            backwd_data['tail_neg'] = all_data['head_neg']
        merged_dict = {}
        for key in fwd_data:
            merged_dict[key] = np.concatenate([fwd_data[key], backwd_data[key]])
    else:
        logging.info('evaluating uni-directional 1p')
        fwd_data = {'head': all_data['head'],
                    'relation': all_data['relation'],
                    'tail': all_data['tail']}
        if 'tail_neg' in all_data:
            fwd_data['tail_neg'] = all_data['tail_neg']
        merged_dict = fwd_data
    if args.eval_batch_size > 1:
        test_dataset = Test1pBatchDataset(merged_dict, args.nentity, args.nrelation)
    else:
        test_dataset = Test1pDataset(merged_dict, args.nentity, args.nrelation)

    logging.info("%s info:" % phase)
    logging.info("num queries: %s" % len(test_dataset))
    buf = mp.Queue()
    writer_buffer = mp.Queue()
    return QueryData(test_dataset,"deploy", buf, writer_buffer)


def load_eval_data(args, phase):
    tasks = args.tasks.split('.')
    logging.info("loading %s data" % phase)
    if args.eval_path is not None:
        all_data = pickle.load(open(os.path.join(args.eval_path, "all-%s-data.pkl" % phase), 'rb'))

        # remove tasks not in args.tasks
        query_structures_to_remove = []
        for name in all_tasks:
            if not args.filter_test:
                continue
            if 'u' in name:
                name, evaluate_union = name.split('-')
            else:
                evaluate_union = args.evaluate_union
            if name not in tasks or evaluate_union != args.evaluate_union:
                query_structure = name_query_dict[name if 'u' not in name else '-'.join([name, evaluate_union])]
                query_structures_to_remove.append(query_structure)
        if len(query_structures_to_remove) != 0:
            all_data = [data for data in all_data if data[0] not in query_structures_to_remove]
    else:
        print('no %s data found' % phase)
        all_data = []
    test_dataset = MultihopTestDataset(all_data, args.nentity, args.nrelation)
    logging.info("%s info:" % phase)
    logging.info("num queries: %s" % len(test_dataset))
    buf = mp.Queue()
    writer_buffer = mp.Queue()
    return QueryData(test_dataset, buf, writer_buffer)


def write_to_writer(eval_dict, writer):

    def collect_and_write(writer_buffer, mode):
        metrics, average_metrics, step = writer_buffer.get()
        if step == -1:
            return False
        for query_structure in metrics:
            for metric in metrics[query_structure]:
                qname = query_name_dict[query_structure] if query_structure in query_name_dict else str(query_structure)
                writer.add_scalar("_".join([mode, qname, metric]), metrics[query_structure][metric], step)
        for metric in average_metrics:
            writer.add_scalar("_".join([mode, 'average', metric]), average_metrics[metric], step)
        return True

    writer_flag = True
    while writer_flag:
        writer_flag = False
        for key in eval_dict:
            if collect_and_write(eval_dict[key].writer_buffer, key):
                writer_flag = True

def retrieve_beta(entity_embedding, query_embedding, answers):
    from smore.common.torchext.dist_func.beta_dist import BetaDist
    import torch.distributions.kl as torch_kl
    t0 = time.time()
    alpha_embedding, beta_embedding = torch.chunk(entity_embedding.unsqueeze(1), 2, dim=-1)
    entity_dist = BetaDist(alpha_embedding, beta_embedding)
    query_dist = BetaDist(*query_embedding)
    kld = torch_kl._kl_beta_beta(entity_dist, query_dist)
    dist = torch.norm(kld, p=1, dim=-1).squeeze()
    print("Time to calculate the distance", time.time() - t0)

    for i in range(23):
        answer_0 = torch.topk(dist[i], k=1000, largest=True)[1].tolist()
        ground_truth_0 = answers[i]
        count = 0
        for ans in answer_0:
            count += 1 if ans in ground_truth_0 else 0
        print("precision:", count / len(answer_0))

def ranking_box(entity_embedding, query_embedding, query_offset):
    query_embedding = query_embedding.squeeze()
    query_offset = query_offset.squeeze()
    delta = (entity_embedding - query_embedding).abs()
    distance_out = torch.nn.functional.relu(delta - query_offset)
    distance_in = torch.min(delta, query_offset)
    dist = (torch.norm(distance_out, p=1, dim=-1) + 0.02 * torch.norm(distance_in, p=1, dim=-1)).cpu().detach()

    rankings = dist.argsort().numpy()
    return rankings # 取top-50的entities

def retrieve_box(entity_embedding, query_embedding, query_offset, answers=None):
    t0 = time.time()
    query_embedding = query_embedding.squeeze()
    query_offset = query_offset.squeeze()
    tolerence = 2.0
    ps = []
    rs = []
    for i in range(1):
        # print(torch.abs(query_offset[i]))
        # exit()
        query_offset[i] = torch.abs(query_offset[i]) + tolerence
        mask_le = torch.all(entity_embedding <= query_embedding[i] + query_offset[i], dim=1)
        mask_ge = torch.all(entity_embedding >= query_embedding[i] - query_offset[i], dim=1)
        retrieved = torch.logical_and(mask_le, mask_ge)
        idx = retrieved.nonzero().squeeze().cpu().tolist()
        return idx
        # print(idx)
        
        if answers is not None:
            ground_truth = torch.zeros(entity_embedding.shape[0], dtype=torch.bool).cuda()
            indicies = torch.tensor(list(answers[i])).cuda()
            ground_truth[indicies] = True
            TP = (retrieved & ground_truth).sum().item()  # 交集，即检索到的相关样本数
            FP = (retrieved & (~ground_truth)).sum().item()  # 预测为正但实际为负的样本数
            FN = ((~retrieved) & ground_truth).sum().item()  # 预测为负但实际为正的样本数

            # 计算 Precision、Recall 和 F1 值
            precision = TP / (TP + FP + 1e-10)  # 加入一个小值避免除零错误
            recall = TP / (TP + FN + 1e-10)
            f1_score = 2 * (precision * recall) / (precision + recall + 1e-10)

            print("Precision:", precision)
            print("Recall:", recall)
            print("F1 Score:", f1_score)
            ps.append(precision)
            rs.append(recall)
    
    if answers is not None:
        import matplotlib.pyplot as plt
        plt.scatter(ps, rs)
        plt.title('Precision-Recall on FB15k dataset')
        plt.xlabel('precision')
        plt.ylabel('recall')
        plt.savefig('scatter_plot.png')

def main(parser):
    args = parser.parse_args(None)
    set_global_seed(args.seed)
    gpus = [int(i) for i in args.gpus.split(".")]
    assert args.gpus == '.'.join([str(i) for i in range(len(gpus))]), 'only support continuous gpu ids starting from 0, please set CUDA_VISIBLE_DEVICES instead'
    
    maybe_download_dataset(args.data_path)

    setup_train_mode(args)
    
    setup_save_path(args)

    writer = set_logger(args)

    model = get_model(args)

    logging.info('-------------------------------'*3)
    logging.info('Geo: %s' % args.geo)
    logging.info('Data Path: %s' % args.data_path)
    logging.info('#entity: %d' % args.nentity)
    logging.info('#relation: %d' % args.nrelation)
    logging.info('#max steps: %d' % args.max_steps)
    logging.info('Evaluate unions using: %s' % args.evaluate_union)

    kg_mem = KGMem(dtype=args.kg_dtype)
    kg_mem.load(os.path.join(args.data_path, 'train_bidir.bin'))
    kg_mem.share_memory()

    opt_stats = try_load_checkpoint(args, model)
    logging.info('tasks = %s' % args.tasks)
    logging.info('init_step = %d' % opt_stats['init_step'])
    if args.do_train:
        logging.info("Training info:")
        logging.info("{}: infinite".format(args.training_tasks))
        logging.info('Start Training...')
        logging.info('learning_rate = %d' % opt_stats['current_learning_rate'])
    logging.info('batch_size = %d' % args.batch_size)
    logging.info('hidden_dim = %d' % args.hidden_dim)
    logging.info('gamma = %f' % args.gamma)
    
    eval_dict = {}
    aggr_procs = []
    args.gpus = gpus
    if len(gpus) > 1:
        assert not args.cuda
        model.share_memory()

    for phase in ['valid', 'test']:
        if getattr(args, 'do_%s' % phase, False):
            if args.eval_link_pred:  # load ogb benchmark 1p dataset
                d = load_1p_eval_data(args, phase)
            else:
                d = load_eval_data(args, phase)
            result_aggregator = mp.Process(target=async_aggr, args=(args, d.buffer, d.writer_buffer, 'phase'))
            result_aggregator.start()
            aggr_procs.append(result_aggregator)
            eval_dict[phase] = d

    if args.feature_folder is not None:
        logging.info('loading static entity+relation features from %s' % args.feature_folder)
        ro_feat = {
            "entity": torch.tensor(np.load(os.path.join(args.feature_folder, "entity_feat.npy")), dtype=torch.float16),
            "relation": torch.tensor(np.load(os.path.join(args.feature_folder, "relation_feat.npy")), dtype=torch.float16)
        }
    else:
        ro_feat = None
    procs = []
    training_tasks = args.training_tasks.split('.')
    for rank, gpu_id in enumerate(gpus):
        logging.info("[GPU {}] tasks: {}".format(gpu_id, args.training_tasks))
        local_eval_dict = {}
        for phase in eval_dict:
            q_data = eval_dict[phase]
            nq_per_proc = math.ceil(len(q_data.data) / len(gpus))
            local_eval_dict[phase] = QueryData(q_data.data.subset(rank * nq_per_proc, nq_per_proc), q_data.buffer, q_data.writer_buffer)
        proc = mp.Process(target=train_mp, args=(args, kg_mem, opt_stats, model, local_eval_dict, training_tasks, ro_feat, gpu_id))
        procs.append(proc)
        proc.start()

    write_to_writer(eval_dict, writer)
    for proc in procs + aggr_procs:
        proc.join()

    logging.info("Training finished!!")

    exit()
    """
    Trining finished, now deploy the query processor model
    TODO:
    1. Query parser: SPARQL query -> (e,(r,))....
    2. Feeds structured query to the model
    3. Answer Retrieval in the graph
    4. implement query as service
    5. pytorch model deploying

    Note: this is a temporary implementation, a server module will be implemented in the future
    """

    parser = QueryParser()
    # query, query_structure = build_queries(edge_list)
    # assert query_structure == ('e', ('r',))
    # query_str = """
    # SELECT ?o WHERE
    # {
    #     :m.0qcr0 :base.bioventurist.bv_medical_condition.company_involved ?o .
    # }
    # """
    # query_str = """
    # SELECT ?movie WHERE
    # {
    #     :m.07s9rl0 :film.film.genre ?movie .
    # }
    # """
    # query_structure = ('e', ('r',))
    with open(os.path.join(args.data_path, 'smore_queries.pkl'), 'rb') as f:
        total_query_str = pickle.load(f)
    # Query2Box
    # entity_embedding = model.entity_embedding.embedding
    entity_embedding = model.entity_embedding(None)
    model.to(torch.device('cuda:0'))
    model.eval()

    stats = Stats('rdflib')

    query_types = ['1p', '2p', '3p', '2i', '3i', 'ip', 'pi']
    # query_types = ['1p']
    total_results = {}
    for qtype in query_types:
        total_time = 0
        total_retieve_time = 0
        total_parse_time = 0
        total_calc_time = 0
        struct_results = []
        for query_str in total_query_str[qtype]:
            t0 = time.time()
            query, query_structure = parser.parse(query_str)
            t1 = time.time()
            queries = torch.LongTensor([flatten(query)]).cuda()

            with torch.no_grad():
                [query_embedding, query_offset] = model.inference(query_structure, queries, torch.device('cuda:0'))
            t2 = time.time()
            
            # results = retrieve_box(entity_embedding, query_embedding, query_offset)
            results = ranking_box(entity_embedding, query_embedding, query_offset)
            struct_results.append(results)
            t3 = time.time()
            total_time += t3 - t0
            total_retieve_time += t3 - t2
            total_calc_time += t2 - t1
            total_parse_time += t1 - t0
        total_results[qtype] = struct_results
        stats.log_data(qtype, total_time / len(total_query_str[qtype]))
        stats.log_data(f"{qtype}_parse", total_parse_time / len(total_query_str[qtype]))
        stats.log_data(f"{qtype}_calc", total_calc_time / len(total_query_str[qtype]))
        stats.log_data(f"{qtype}_retriv", total_retieve_time / len(total_query_str[qtype]))
        print("------------------------------")
        print(f"query structure: {qtype}")
        print("avg query time", total_time / 1000)
        print("avg parse time", total_parse_time / 1000)
        print("avg calc time", total_calc_time / 1000)
        print("avg retriv time", total_retieve_time / 1000)
        print()
    stats.save_data('/home/lousy/smore/testing/ngdb_time.pkl')

    with open(os.path.join(args.data_path, 'ngdb_results.pkl'), 'wb') as f:
        pickle.dump(total_results,  f, pickle.HIGHEST_PROTOCOL)

# @app.route('/query', methods=['POST"])
# async def recv_query(request):
#     recevied_string = request.json.get('query')
#     parser = QueryParser()
#     try:
#         parser.parse(recevied_string)
#     except ValueError as e:
#         error_message = 


if __name__ == '__main__':
    torch.multiprocessing.set_start_method('spawn')
    main(parse_args())
