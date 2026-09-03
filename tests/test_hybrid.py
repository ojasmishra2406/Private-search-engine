import pytest
from src.hybrid.fusion import normalize_scores, weighted_fusion, reciprocal_rank_fusion
from src.hybrid.retriever import HybridRetriever
from typing import List, Tuple

# Mock components for testing HybridRetriever independently
class MockLexicalSearchResult:
    def __init__(self, doc_id, score):
        self.doc_id = doc_id
        self.score = score

class MockLexicalSearch:
    def __init__(self, results):
        self.results = results
        
    def search(self, query: str, top_k: int):
        return [MockLexicalSearchResult(doc_id, score) for doc_id, score in self.results][:top_k]

class MockDenseRetriever:
    def __init__(self, results, fail=False):
        self.results = results
        self.fail = fail
        
    def search(self, query: str, top_k: int):
        if self.fail:
            raise Exception("Dense index unavailable")
        return self.results[:top_k]

# ---- Normalization Tests ----
def test_normalize_scores_standard():
    scores = [10.0, 5.0, 0.0]
    norm = normalize_scores(scores)
    assert norm == [1.0, 0.5, 0.0]

def test_normalize_scores_identical():
    scores = [7.5, 7.5, 7.5]
    norm = normalize_scores(scores)
    assert norm == [1.0, 1.0, 1.0]

def test_normalize_scores_empty_or_single():
    assert normalize_scores([]) == []
    assert normalize_scores([4.2]) == [1.0]

def test_zero_score_range_during_normalization():
    # If all scores are the same, max_s == min_s. Already covered by identical test, 
    # but verifying explicit 0.0 scores
    assert normalize_scores([0.0, 0.0]) == [1.0, 1.0]

# ---- Weighted Fusion Tests ----
def test_weighted_fusion_bm25_only_alpha_1():
    bm25 = [("docA", 10.0), ("docB", 5.0)]
    dense = [("docB", 0.9), ("docC", 0.8)]
    # alpha=1.0 means 100% BM25
    res = weighted_fusion(bm25, dense, alpha=1.0)
    scores = {doc_id: score for doc_id, score in res}
    assert scores["docA"] == 1.0  # normalized max
    assert scores["docB"] == 0.0  # normalized min
    assert scores["docC"] == 0.0  # missing from BM25 -> 0.0

def test_weighted_fusion_dense_only_alpha_0():
    bm25 = [("docA", 10.0), ("docB", 5.0)]
    dense = [("docB", 0.9), ("docC", 0.8)]
    # alpha=0.0 means 100% Dense
    res = weighted_fusion(bm25, dense, alpha=0.0)
    scores = {doc_id: score for doc_id, score in res}
    assert scores["docB"] == 1.0
    assert scores["docC"] == 0.0
    assert scores["docA"] == 0.0

def test_weighted_fusion_50_50_alpha_half():
    bm25 = [("docA", 10.0), ("docB", 5.0)]     # Norm: A=1.0, B=0.0
    dense = [("docB", 0.9), ("docC", 0.8)]     # Norm: B=1.0, C=0.0
    res = weighted_fusion(bm25, dense, alpha=0.5)
    scores = {doc_id: score for doc_id, score in res}
    assert scores["docA"] == 0.5 * 1.0 + 0.5 * 0.0  # 0.5
    assert scores["docB"] == 0.5 * 0.0 + 0.5 * 1.0  # 0.5
    assert scores["docC"] == 0.5 * 0.0 + 0.5 * 0.0  # 0.0
    # docA and docB tie at 0.5. Sort order breaks tie by doc_id ascending -> docA before docB
    assert res[0] == ("docA", 0.5)
    assert res[1] == ("docB", 0.5)
    assert res[2] == ("docC", 0.0)

def test_weighted_fusion_missing_docs_handling():
    # Only one doc in each, no overlap
    bm25 = [("docA", 10.0)]
    dense = [("docB", 0.8)]
    res = weighted_fusion(bm25, dense, alpha=0.5)
    scores = {doc_id: score for doc_id, score in res}
    # With 1 item, normalize returns 1.0
    assert scores["docA"] == 0.5 * 1.0 + 0.5 * 0.0  # 0.5
    assert scores["docB"] == 0.5 * 0.0 + 0.5 * 1.0  # 0.5

def test_weighted_fusion_invalid_alpha():
    with pytest.raises(ValueError):
        weighted_fusion([], [], alpha=1.5)
    with pytest.raises(ValueError):
        weighted_fusion([], [], alpha=-0.1)

# ---- RRF Fusion Tests ----
def test_rrf_basic():
    bm25 = [("docA", 10.0), ("docB", 5.0)]
    dense = [("docB", 0.9), ("docC", 0.8)]
    res = reciprocal_rank_fusion(bm25, dense, k=60)
    scores = {doc_id: score for doc_id, score in res}
    
    # docA rank 1 in BM25 -> 1/61
    assert scores["docA"] == 1/61
    # docB rank 2 in BM25 -> 1/62, rank 1 in dense -> 1/61
    assert scores["docB"] == (1/62) + (1/61)
    # docC rank 2 in dense -> 1/62
    assert scores["docC"] == 1/62
    
    # Sorted order: docB > docA > docC
    assert res[0][0] == "docB"
    assert res[1][0] == "docA"
    assert res[2][0] == "docC"

def test_rrf_missing_document_contributes_zero():
    # docC is missing from BM25, so it only gets the Dense RRF score (1/62)
    # Verified in test_rrf_basic
    pass

def test_rrf_invalid_k():
    with pytest.raises(ValueError):
        reciprocal_rank_fusion([], [], k=0)
    with pytest.raises(ValueError):
        reciprocal_rank_fusion([], [], k=-5)

def test_stable_deterministic_ordering_tied_scores():
    # Force tie
    bm25 = [("docZ", 10.0), ("docA", 10.0)]
    dense = []
    res = reciprocal_rank_fusion(bm25, dense, k=60)
    # docZ rank 1 -> 1/61, docA rank 2 -> 1/62
    # Wait, RRF depends on input rank. Let's make ranks tie by doing identical rank across lists
    bm25_tie = [("docZ", 10.0)]
    dense_tie = [("docA", 0.9)]
    res_tie = reciprocal_rank_fusion(bm25_tie, dense_tie, k=60)
    # Both get 1/61. docA should be first alphanumerically
    assert res_tie[0][0] == "docA"
    assert res_tie[1][0] == "docZ"

# ---- HybridRetriever Tests ----
def test_hybrid_retriever_bm25_only_results():
    lex = MockLexicalSearch([("docA", 10.0)])
    dense = MockDenseRetriever([])
    retriever = HybridRetriever(lex, dense)
    res = retriever.search("q")
    assert len(res) == 1
    assert res[0][0] == "docA"

def test_hybrid_retriever_dense_only_results():
    lex = MockLexicalSearch([])
    dense = MockDenseRetriever([("docB", 0.9)])
    retriever = HybridRetriever(lex, dense)
    res = retriever.search("q")
    assert len(res) == 1
    assert res[0][0] == "docB"

def test_hybrid_retriever_both_empty():
    lex = MockLexicalSearch([])
    dense = MockDenseRetriever([])
    retriever = HybridRetriever(lex, dense)
    assert retriever.search("q") == []

def test_hybrid_retriever_union_and_duplicate_merging():
    lex = MockLexicalSearch([("docA", 10.0), ("docB", 5.0)])
    dense = MockDenseRetriever([("docB", 0.9), ("docC", 0.8)])
    retriever = HybridRetriever(lex, dense)
    res = retriever.search("q")
    # docA, docB, docC -> 3 unique docs
    assert len(res) == 3

def test_hybrid_retriever_candidate_pool_truncation():
    # Provide 5 docs, but pool=2
    lex = MockLexicalSearch([("doc1", 10), ("doc2", 9), ("doc3", 8)])
    dense = MockDenseRetriever([("doc4", 0.9), ("doc5", 0.8), ("doc6", 0.7)])
    retriever = HybridRetriever(lex, dense)
    # RRF with pool 2 -> brings in doc1, doc2, doc4, doc5. doc3, doc6 ignored.
    res = retriever.search("q", candidate_pool_size=2)
    assert len(res) == 4
    ids = [r[0] for r in res]
    assert "doc1" in ids
    assert "doc4" in ids
    assert "doc3" not in ids

def test_hybrid_retriever_top_k_truncation():
    lex = MockLexicalSearch([("doc1", 10), ("doc2", 9)])
    dense = MockDenseRetriever([("doc3", 0.9), ("doc4", 0.8)])
    retriever = HybridRetriever(lex, dense)
    res = retriever.search("q", top_k=2)
    assert len(res) == 2

def test_hybrid_retriever_invalid_top_k():
    lex = MockLexicalSearch([("doc1", 10)])
    dense = MockDenseRetriever([("doc2", 0.9)])
    retriever = HybridRetriever(lex, dense)
    assert retriever.search("q", top_k=0) == []
    assert retriever.search("q", top_k=-1) == []

def test_hybrid_retriever_degrades_gracefully_when_dense_fails():
    lex = MockLexicalSearch([("doc1", 10)])
    dense = MockDenseRetriever([("doc2", 0.9)], fail=True)
    retriever = HybridRetriever(lex, dense)
    res = retriever.search("q")
    assert len(res) == 1
    assert res[0][0] == "doc1"
