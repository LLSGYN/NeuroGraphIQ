import argparse
import json
import numpy as np
import time
import torch
import torch.nn as nn
import os.path as osp
import pickle as pkl
from .query_parser import QueryParser, MetaManager

from smore.models import build_model
from smore.common.config import parse_args, all_tasks, query_name_dict, name_query_dict
from smore.common.embedding.embed_optimizer import get_optim_class
from smore.common.util import flatten_query, list2tuple, parse_time, set_global_seed, eval_tuple, construct_graph, tuple2filterlist, maybe_download_dataset, flatten

class NGDBState(object):
    def __init__(self, data_path:str, dataset:str, processor:str):
        self.dataset = dataset
        self.processor = processor
        self.root = osp.join(data_path, dataset)
        self.model = None

        self.load_model()
        # load graph data
        self.manager = MetaManager(data_path, dataset)
        self.parser = QueryParser(self.manager, dm=(processor != 'box'))
        # self.train_rdf_kg = get_rdf_graph(data_path, dataset, 'train')
        # self.test_rdf_kg = get_rdf_graph(data_path, dataset, 'test')

        with open(osp.join(data_path, dataset, 'id2ent.pkl'), 'rb') as f:
            self.id2ent = pkl.load(f)
        with open(osp.join(data_path, dataset, 'id2rel.pkl'), 'rb') as f:
            self.id2rel = pkl.load(f)

    def setup_train_mode(self, args):
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
        
    def get_model(self, args):
        with open(osp.join(self.root, 'stats.txt')) as f:
            entrel = f.readlines()
            nentity = int(entrel[0].split(' ')[-1])
            nrelation = int(entrel[1].split(' ')[-1])
        
        args.nentity = nentity
        args.nrelation = nrelation    
        model = build_model(args, nentity, nrelation, query_name_dict)
        # EmbedOpt = get_optim_class(args)
        # EmbedOpt.prepare_optimizers(args, [x[1] for x in model.named_sparse_embeddings()])
        return model

    def load_checkpoint(self, args, model:nn.Module):
        checkpoint = torch.load(osp.join(args.checkpoint_path, 'checkpoint'),
                                map_location='cpu')
        model.load_state_dict(checkpoint['model_state_dict'], strict=False)

    def load_config(self):
        with open(osp.join(self.root, f'{self.processor}.json'), 'r') as f:
            config_args = json.load(f)
        args = argparse.Namespace()
        parser = parse_args()
        parser.parse_args(args=[], namespace=args)
        for key, value in config_args.items():
            setattr(args, key, value)
        return args

    def load_model(self):
        args = self.load_config()
        self.setup_train_mode(args)
        model = self.get_model(args)
        self.load_checkpoint(args, model)
        # create model
        entity_embedding = model.entity_embedding(None)
        model.to(torch.device('cuda:0'))
        model.eval()
        self.model = model
        self.entity_embedding = entity_embedding