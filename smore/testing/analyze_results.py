import argparse
import pickle as pkl
import os.path as osp
import numpy as np
import matplotlib.pyplot as plt

class Metrics(object):
    @staticmethod
    def precision_score(pred, ans,  k=1.0):
        """
        pred [Q, N_entities]
        ans  [Q, num_answer(q_i)]

        注意：这里没有做对于easy/hard answer的filtering,我们是否有必要做?
        """
        pred = np.vstack(pred)
        print(pred.shape)
        counts = int(pred.shape[1] * k)
        X = pred[:, :counts]
        Y = ans

        score_total = 0
        for x, y in zip(X, Y):
            score_total += len(set(x) & set(y)) / counts
        return score_total / X.shape[0]
    
    @staticmethod
    def recall_score(pred, ans, k=1.0):
        """
        pred [Q, N_entities]
        ans  [Q, num_answer(q_i)]
        """
        pred = np.vstack(pred)
        counts = int(pred.shape[1] * k)
        X = pred[:, :counts]
        Y = ans

        score_total = 0
        for x, y in zip(X, Y):
            score_total += len(set(x) & set(y)) / len(y) if len(y) != 0 else 0.
        return score_total / X.shape[0]
    
    @staticmethod
    def precision_reall_curve(pred, ans, step=0.15):
        pred = np.vstack(pred)
        ps, rs, ks = [], [], []
        k = step
        while k < 1.0:
            ps.append(Metrics.precision_score(pred, ans, k))
            rs.append(Metrics.recall_score(pred, ans, k))
            k += step
        print(ps)
        print(rs)
    
    @staticmethod
    def mrr_score(pred, ans):
        pred = np.vstack(pred)
        X = pred
        Y = ans

        score_total = 0
        for x, y in zip(X, Y):
            y_set = set(y)
            score = 0
            for v in y_set:
                cnt = 0
                v_rank = None
                for t in x:
                    if t == v or (t not in y_set):
                        cnt += 1
                    if t == v:
                        v_rank = cnt
                        break
                assert v_rank is not None
                score += 1 / v_rank
            score_total += score / len(y)
        return score_total / X.shape[0]

    @staticmethod
    def hits_score(pred, ans, k=10, filt=None):
        pred = np.vstack(pred)
        X = pred
        Y = ans

        score_total = 0
        for _, (x, y) in enumerate(zip(X, Y)):
            y_set = set(y)
            if filt is not None:
                z = filt[_]
            score = 0
            for v in y_set:
                cnt = 0
                for i in range(len(x)):
                    if filt is not None and x[i] in z:
                        continue
                    if x[i] == v or (x[i] not in y_set):
                        cnt += 1
                    if x[i] == v:
                        score += 1
                        break
                    if cnt == k:
                        break
            score_total += score / len(y) if len(y) != 0 else 0.
        return score_total / X.shape[0]

def evaluate(qtype, pred, ans, filt=None):
    """
    计算: precision, recall, mrr, hits@k
    """
    print("\n-----------------------------------------")
    print(f"Evaluating structure {qtype}:")
    print(f"Average precision: {Metrics.precision_score(pred, ans, k=0.0033)}")
    print(f"Average recall: {Metrics.recall_score(pred, ans, k=0.0033)}")
    # print(f"Average mrr: {Metrics.mrr_score(pred, ans)}")
    # print(f"Average hits@1: {Metrics.hits_score(pred, ans, 1)}")
    print(f"Average hits@3: {Metrics.hits_score(pred, ans, 3, filt=filt)}")
    # print(f"Average hits@10: {Metrics.hits_score(pred, ans, 10)}")

def eval_missing(qtype, simple_ans, pred, ans):
    print("\n-----------------------------------------")
    print(f"Evaluating structure {qtype}:")
    hard_answers = []
    for x, y in zip(simple_ans, ans):
        x = set(x)
        hard_answers.append(y - x)
    evaluate(qtype, pred, hard_answers, simple_ans)

def main(args):
    with open(osp.join(args.data_path, 'rdf_results.pkl'), 'rb') as f:
        rdf_results = pkl.load(f)
    with open(osp.join(args.data_path, 'ngdb_results.pkl'), 'rb') as f:
        ngdb_resutls = pkl.load(f)
    with open(osp.join(args.data_path, 'all_answers.pkl'), 'rb') as f:
        all_answers = pkl.load(f)

    tasks = args.tasks.split(',')

    # 评测NGDBs的查询精度
    if args.test_accuracy:
        for tp in tasks:
            evaluate(tp, ngdb_resutls[tp], all_answers[tp])
    
    # 评测NGDBs能否检索到hard-arsnwers（因为缺失边导致rdflib无法检索到的答案）
    if args.test_hard_ans:
        for tp in tasks:
            eval_missing(tp, rdf_results[tp], ngdb_resutls[tp], all_answers[tp])
    
    # 比较二者的查询时间开销
    if args.test_time:
        with open('rdf_time.pkl', 'rb') as f:
            rdf_time = pkl.load(f)
        with open('ngdb_time.pkl', 'rb') as f:
            ngdb_time = pkl.load(f)
        for qtype in tasks:
            print(f"{qtype}-time-rdflib", rdf_time[qtype])
            print(f"{qtype}-time-ngdb", ngdb_time[qtype])
            print("-----------------------------------------------")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Analyzing results of smore and ngdbs')
    parser.add_argument('-p', '--data_path', type=str, default='/home/lousy/smore/data/FB15k')
    parser.add_argument('-t', '--tasks', type=str, default='1p,2p,3p,2i,3i,ip,pi')
    parser.add_argument('--test_accuracy', action='store_true')
    parser.add_argument('--test_hard_ans', action='store_true')
    parser.add_argument('--test_time', action='store_true')
    args = parser.parse_args()
    main(args)