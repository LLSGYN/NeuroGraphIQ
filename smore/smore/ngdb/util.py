import pickle as pkl
import os.path as osp

def generate_query(parse_result):
    raise NotImplementedError

class Stats:
    def __init__(self, desc=None):
        self.data = {}
        if desc is not None:
            self.data['description'] = desc
    
    def log_data(self, name, value):
        self.data[name] = value
    
    def log_list_data(self, name, value):
        if name not in self.data:
            self.data[name] = []
        self.data[name].append(value)

    def save_data(self, path):
        with open(path, 'wb') as f:
            pkl.dump(self.data, f, pkl.HIGHEST_PROTOCOL)

class QueryInterface:
    def __init__(self, model, id2ent_path):
        with open(id2ent_path, 'rb') as f:
            self.id2ent = pkl.load(f)
        self.model = model
    
    def make_query(self, query_str: str) -> list[str]:
        pass
