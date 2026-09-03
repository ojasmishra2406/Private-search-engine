import pytest
from src.evaluation.metrics import recall_at_k, precision_at_k, mrr_at_k, ndcg_at_k
from src.evaluation.dataset import EvalQuery, EvaluationDataset
from src.evaluation.runner import EvaluationRunner

def test_recall_at_k():
    assert recall_at_k(["a", "b", "c"], {"a", "c", "d"}, 3) == 2 / 3
    assert recall_at_k(["a", "b", "c"], {"a", "c", "d"}, 1) == 1 / 3
    assert recall_at_k([], {"a"}, 5) == 0.0
    assert recall_at_k(["a"], set(), 5) == 0.0

def test_precision_at_k():
    assert precision_at_k(["a", "b", "c"], {"a", "c", "d"}, 3) == 2 / 3
    assert precision_at_k(["a", "b", "c"], {"a", "c", "d"}, 1) == 1.0
    assert precision_at_k(["a", "b", "c"], {"a", "c", "d"}, 0) == 0.0
    assert precision_at_k([], {"a"}, 5) == 0.0

def test_mrr_at_k():
    assert mrr_at_k(["b", "a", "c"], {"a", "d"}, 3) == 0.5
    assert mrr_at_k(["a", "b", "c"], {"a", "d"}, 3) == 1.0
    assert mrr_at_k(["b", "c"], {"a", "d"}, 3) == 0.0

def test_ndcg_at_k():
    # Ideal: a, b
    # Actual: a, c, b
    # DCG = 1/log2(2) [a] + 0 + 1/log2(4) [b] = 1.0 + 0.5 = 1.5
    # IDCG = 1/log2(2) + 1/log2(3) = 1.0 + 0.6309 = 1.6309
    ndcg = ndcg_at_k(["a", "c", "b"], {"a", "b"}, 3)
    assert 0.91 < ndcg < 0.93

    assert ndcg_at_k(["a", "b"], set(), 3) == 0.0
    assert ndcg_at_k([], {"a"}, 3) == 0.0

def test_evaluation_runner():
    ds = EvaluationDataset([
        EvalQuery("q1", ["a", "b"])
    ])
    
    runner = EvaluationRunner(ds)
    
    # Fake retriever that returns perfect results
    def perfect_retriever(q):
        return ["a", "b"]
        
    results = runner.evaluate(perfect_retriever, k_values=[2])
    assert results["metrics"]["Recall@2"] == 1.0
    assert results["metrics"]["Precision@2"] == 1.0
    assert results["metrics"]["MRR@2"] == 1.0
    assert results["metrics"]["nDCG@2"] == 1.0
    assert len(results["per_query"]) == 1
    assert "latency" in results
