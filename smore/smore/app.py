import json
import os
import os.path as osp
import pickle as pkl
import time

from flask import Flask, request, jsonify
from flask_cors import CORS
# from flask_sqlalchemy import SQLAlchemy
# from werkzeug.security import generate_password_hash, check_password_hash
# from flask_jwt_extended import JWTManager, create_access_token
# from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity

from .state import NGDBState
from .query_parser import QueryParser, QueryDAG, adjust
from .ngdb_query import exec_query, padding_length, exec_query_dag
from .rdf_query import exec_rdflib_query, get_rdf_graph

app = Flask(__name__)
CORS(app)
# CORS(app, resources=r'/*')
data_path = '../data/'
init_data = 'NELL'
init_model = 'box'
app.config['ngdb_state'] = NGDBState(data_path, init_data, init_model)
app.config['dataset'] = init_data
app.config['processor'] = init_model

app.config['train_rdf_kg'] = get_rdf_graph(data_path, init_data, 'train')
app.config['test_rdf_kg'] = get_rdf_graph(data_path, init_data, 'test')

# # 配置数据库
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# app.config['JWT_SECRET_KEY'] = 'NGDB_demo_secret_key'

# db = SQLAlchemy(app)
# jwt = JWTManager(app)

# class User(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     username = db.Column(db.String(80), unique=True, nullable=False)
#     password = db.Column(db.String(120), nullable=False)

# with app.app_context():
#     # 创建数据库和表
#     db.create_all()

# @app.route('/login', methods=['POST'])
# def login():
#     data = request.json
#     username = data['username']
#     password = data['password']

#     user = User.query.filter_by(username=username).first()

#     if user and check_password_hash(user.password, password):
#         access_token = create_access_token(identity=username)
#         return jsonify({
#             'success': True, 
#             'message': 'Login successful',
#             'access_token': access_token
#         })
#     return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

# @app.route('/register', methods=['POST'])
# def register():
#     data = request.json
#     username = data['username']
#     password = data['password']

#     existing_user = User.query.filter_by(username=username).first()

#     if existing_user:
#         return jsonify({'success': False, 'message': 'User already exists'}), 400

#     hashed_password = generate_password_hash(password)
#     new_user = User(username=username, password=hashed_password)
#     db.session.add(new_user)
#     db.session.commit()

#     return jsonify({'success': True, 'message': 'User registered successfully'})

@app.route("/search_options")
def get_kg_options():
    query = request.args.get('query', '', type=str)
    qtype = request.args.get('type', '', type=str)
    if qtype == 'node':
        id2ent = app.config['ngdb_state'].id2ent
        entities = [id2ent[x] for x in id2ent]
        return jsonify([option for option in entities if query.lower() in option.lower()])
    elif qtype == 'edge':
        id2rel = app.config['ngdb_state'].id2rel
        if app.config['dataset'] == 'FB15k':
            relations = [id2rel[x][1:] for x in id2rel if id2rel[x][0] == '+']
        else:
            relations = []
            for x in id2rel:
                if 'reverse' in id2rel[x]:
                    continue
                relations.append(id2rel[x])
        return jsonify([option for option in relations if query.lower() in option.lower()])
    else:
        raise NotImplementedError

@app.route('/set_graph', methods=['POST'])
def set_graph():
    data = request.json
    dataset = data['graph']
    processor = data['processor']
    if dataset != app.config['dataset']:
        app.config['dataset'] = dataset
        app.config['train_rdf_kg'] = get_rdf_graph(data_path, dataset, 'train')
        app.config['test_rdf_kg'] = get_rdf_graph(data_path, dataset, 'test')
    app.config['processor'] = processor

    # if not osp.exists(osp.join(data_path, dataset)) or \
    #     not osp.exists(osp.join(data_path, dataset, processor)):
    #     return f"Invalid request", 404

    app.config['ngdb_state'] = NGDBState(data_path, dataset, processor)

    return f"OK, graph: {dataset}, model: {processor}"

@app.route("/exec_query")
def handle_query():
    t0 = time.time()
    # parser = QueryParser()
    parser = app.config['ngdb_state'].parser

    query_str = request.args.get('query_str', '', type=str)
    id2ent = app.config['ngdb_state'].id2ent
    # model = app.config['model']
    model = app.config['ngdb_state'].model
    # entity_embedding = app.config['entity_emb']
    entity_embedding = app.config['ngdb_state'].entity_embedding
    res_ngdb, query_plan = exec_query(model, entity_embedding, parser, id2ent, query_str, app.config['processor'])
    t1 = time.time()
    res_rdflib = exec_rdflib_query(app.config['train_rdf_kg'], query_str)
    t2 = time.time()
    ground_truth_set = set(exec_rdflib_query(app.config['test_rdf_kg'], query_str))
    train_ans_set = set(res_rdflib)
    res_ngdb_checked = []
    for x in res_ngdb:
        if (x in ground_truth_set) and (x not in train_ans_set):
            res_ngdb_checked += [[x, 1]]
        else:
            res_ngdb_checked += [[x, 0]]
    result_table = padding_length(res_ngdb_checked, res_rdflib)
    return jsonify({"result_table": result_table, "time_ngdb": t1 - t0, "time_symbolic": t2 - t1, "query_plan": query_plan})

@app.route("/exec_graph_query")
def hande_graph_query():
    # data = request.args
    data = request.args.get('data')
    data = json.loads((data))

    target = data['target']
    edges = data['triples']
    manager = app.config['ngdb_state'].manager

    def get_node_id(x):
        if x['type'] == 'variable':
            return manager.get_variable(x['id'])
        return manager.get_anchor(x['id'])

    def get_relation_id(x):
        if app.config['dataset'] == 'FB15k':
            return manager.get_relation(x[1:].replace('/', '.'))
        else:
            return manager.get_relation(x)

    triples = []

    for edge in edges:
        u = get_node_id(edge['src'])
        v = get_node_id(edge['dst'])
        rel = get_relation_id(edge['rel'])
        triples.append([u, rel, v])
    
    print(triples)
    query_graph = QueryDAG(manager, triples)
    query_graph.print()
    dag = adjust(query_graph, target, manager)
    dag.print()
    # dag = dag.transform_to_dnf()
    # dag.print()
    id2ent = app.config['ngdb_state'].id2ent
    id2ent = app.config['ngdb_state'].id2ent
    # model = app.config['model']
    model = app.config['ngdb_state'].model
    # entity_embedding = app.config['entity_emb']
    entity_embedding = app.config['ngdb_state'].entity_embedding
    res_ngdb = exec_query_dag(model, entity_embedding, dag, id2ent, app.config['processor'])
    # return jsonify({"result_table": res_ngdb[:50], "time_ngdb": t1 - t0, "time_symbolic": t2 - t1})
    return jsonify({"result_table": res_ngdb})

if __name__ == '__main__':
    app.run(debug=True)
