import pytest
from src.core.metrics import Metrics

def test_precision_at_k():
    relevant = {"d1", "d2"}
    
    # Perfect precision
    assert Metrics.precision_at_k(["d1", "d2", "d3"], relevant, 2) == 1.0
    
    # Partial precision
    assert Metrics.precision_at_k(["d1", "d3", "d4"], relevant, 2) == 0.5
    
    # Zero precision
    assert Metrics.precision_at_k(["d3", "d4"], relevant, 2) == 0.0
    
    # Empty results
    assert Metrics.precision_at_k([], relevant, 2) == 0.0
    
    # Fewer results than K
    # retrieved 1 relevant out of 2 requested means 1/2 = 0.5
    assert Metrics.precision_at_k(["d1"], relevant, 2) == 0.5
    
    # No relevant docs
    assert Metrics.precision_at_k(["d1"], set(), 2) == 0.0
    
    # Duplicate retrieved documents (though shouldn't happen, testing logic)
    assert Metrics.precision_at_k(["d1", "d1"], relevant, 2) == 1.0

def test_recall_at_k():
    relevant = {"d1", "d2", "d3"}
    
    # Perfect recall
    assert Metrics.recall_at_k(["d1", "d2", "d3", "d4"], relevant, 3) == 1.0
    
    # Partial recall
    assert Metrics.recall_at_k(["d1", "d4", "d5"], relevant, 3) == 1/3
    
    # Zero recall
    assert Metrics.recall_at_k(["d4", "d5"], relevant, 3) == 0.0
    
    # Empty results
    assert Metrics.recall_at_k([], relevant, 3) == 0.0
    
    # No relevant docs (undefined, return 0.0)
    assert Metrics.recall_at_k(["d1"], set(), 3) == 0.0
    
    # Duplicates in retrieval shouldn't inflate recall
    assert Metrics.recall_at_k(["d1", "d1", "d4"], relevant, 3) == 1/3

def test_mrr():
    relevant = {"d1", "d2"}
    
    # First item is relevant (rank 1)
    assert Metrics.mrr(["d1", "d3", "d4"], relevant) == 1.0
    
    # Second item is relevant (rank 2)
    assert Metrics.mrr(["d3", "d1", "d4"], relevant) == 0.5
    
    # Third item is relevant (rank 3)
    assert Metrics.mrr(["d3", "d4", "d2"], relevant) == 1/3
    
    # Fifth item is relevant (rank 5)
    assert Metrics.mrr(["d3", "d4", "d5", "d6", "d1"], relevant) == 0.2
    
    # Tenth item is relevant (rank 10)
    assert Metrics.mrr(["d3", "d4", "d5", "d6", "d7", "d8", "d9", "d10", "d11", "d1"], relevant) == 0.1
    
    # None relevant
    assert Metrics.mrr(["d3", "d4", "d5"], relevant) == 0.0
    
    # Empty retrieved
    assert Metrics.mrr([], relevant) == 0.0
    
    # Empty relevant
    assert Metrics.mrr(["d1"], set()) == 0.0

def test_ndcg_at_k():
    relevant = {"d1", "d2"}
    
    # IDCG for 2 items is 1/log2(2) + 1/log2(3) = 1.0 + 0.6309 = 1.6309
    
    # Perfect ranking
    ndcg_perfect = Metrics.ndcg_at_k(["d1", "d2", "d3"], relevant, 2)
    assert pytest.approx(ndcg_perfect) == 1.0
    
    # Partial ranking (1st relevant, 2nd irrelevant)
    # DCG = 1/log2(2) = 1.0. IDCG = 1.6309. NDCG = 1.0 / 1.6309 = 0.6131
    ndcg_partial1 = Metrics.ndcg_at_k(["d1", "d3", "d4"], relevant, 2)
    assert pytest.approx(ndcg_partial1, 0.001) == 0.6131
    
    # Partial ranking (1st irrelevant, 2nd relevant)
    # DCG = 1/log2(3) = 0.6309. IDCG = 1.6309. NDCG = 0.6309 / 1.6309 = 0.3868
    ndcg_partial2 = Metrics.ndcg_at_k(["d3", "d1", "d4"], relevant, 2)
    assert pytest.approx(ndcg_partial2, 0.001) == 0.3868
    
    # Zero NDCG
    assert Metrics.ndcg_at_k(["d3", "d4"], relevant, 2) == 0.0
    
    # Empty results
    assert Metrics.ndcg_at_k([], relevant, 2) == 0.0
    
    # No relevant docs
    assert Metrics.ndcg_at_k(["d1"], set(), 2) == 0.0
