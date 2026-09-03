import pytest
from src.reranker.cross_encoder import CrossEncoderModel
from src.reranker.reranker import CrossEncoderReranker, RerankCandidate

class MockCrossEncoderModel(CrossEncoderModel):
    def __init__(self):
        # Bypass sentence-transformers initialization
        self.device = "cpu"
        self.model_name = "mock-model"

    def predict_batch(self, query_doc_pairs, batch_size=16):
        scores = []
        for q, text in query_doc_pairs:
            # Simple mock scoring based on exact match length or something predictable
            score = 0.0
            if "relevant" in text.lower():
                score += 5.0
            if "tie" in text.lower():
                score = 1.0 # Force tie
            if not text:
                score -= 10.0
            scores.append(score)
        return scores


@pytest.fixture
def reranker():
    model = MockCrossEncoderModel()
    return CrossEncoderReranker(model, max_document_chars=50, batch_size=2)


def test_model_interface(reranker):
    assert reranker.max_document_chars == 50
    assert reranker.batch_size == 2


def test_pair_construction_and_score_assignment(reranker):
    candidates = [
        RerankCandidate(doc_id="1", text="this is very relevant", original_score=1.0),
        RerankCandidate(doc_id="2", text="not helpful", original_score=2.0)
    ]
    reranked = reranker.rerank("query", candidates, top_k=10)
    
    assert len(reranked) == 2
    # doc 1 should have higher score due to "relevant"
    assert reranked[0].doc_id == "1"
    assert reranked[0].rerank_score > reranked[1].rerank_score
    assert reranked[0].original_score == 1.0
    assert reranked[1].original_score == 2.0


def test_deterministic_ties(reranker):
    candidates = [
        RerankCandidate(doc_id="b", text="tie document", original_score=0.0),
        RerankCandidate(doc_id="a", text="tie document", original_score=0.0)
    ]
    reranked = reranker.rerank("query", candidates, top_k=10)
    
    # Both score 1.0, should tie-break on doc_id ('a' before 'b')
    assert reranked[0].doc_id == "a"
    assert reranked[1].doc_id == "b"


def test_top_k_truncation(reranker):
    candidates = [
        RerankCandidate(doc_id=str(i), text="relevant", original_score=0.0)
        for i in range(5)
    ]
    reranked = reranker.rerank("query", candidates, top_k=2)
    assert len(reranked) == 2


def test_empty_candidates_or_query(reranker):
    assert reranker.rerank("query", []) == []
    assert reranker.rerank("", [RerankCandidate("1", "text", 1.0)]) == []


def test_document_truncation(reranker):
    # max chars is 50
    candidates = [RerankCandidate("1", "x" * 100 + " relevant", 1.0)]
    reranked = reranker.rerank("query", candidates)
    # The word "relevant" is after 50 chars, so it won't be seen by the mock
    assert reranked[0].rerank_score == 0.0


def test_cross_encoder_failure_fallback(monkeypatch, reranker):
    def fail_predict(*args, **kwargs):
        raise RuntimeError("Model crashed")
    
    monkeypatch.setattr(reranker.model, "predict_batch", fail_predict)
    candidates = [RerankCandidate("1", "relevant", 1.0)]
    
    with pytest.raises(RuntimeError):
        reranker.rerank("query", candidates)
