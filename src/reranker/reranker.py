from typing import List, Optional
from dataclasses import dataclass
from .cross_encoder import CrossEncoderModel

@dataclass
class RerankCandidate:
    doc_id: str
    text: str
    original_score: float
    rerank_score: Optional[float] = None
    # We can carry other metadata (like title, url, snippet) so the API doesn't have to re-hydrate,
    # but the instructions say "The reranker must not know how candidates were retrieved... no database querying".
    # So we'll let the caller pass whatever they want, and we just return the sorted list of candidates.

class CrossEncoderReranker:
    def __init__(self, model: CrossEncoderModel, max_document_chars: int = 4000, batch_size: int = 32):
        self.model = model
        self.max_document_chars = max_document_chars
        self.batch_size = batch_size

    def rerank(self, query: str, candidates: List[RerankCandidate], top_k: int = 10) -> List[RerankCandidate]:
        """
        Reranks a candidate pool using the cross-encoder model.
        """
        if not query.strip() or not candidates:
            return []

        # 1. Truncate text and construct pairs
        query_doc_pairs = []
        for cand in candidates:
            truncated_text = cand.text[:self.max_document_chars]
            query_doc_pairs.append((query, truncated_text))
            
        # 2. Batch predict
        try:
            scores = self.model.predict_batch(query_doc_pairs, batch_size=self.batch_size)
        except Exception as e:
            # If the model fails during prediction, fallback gracefully
            # The instructions say: "reranked endpoint must gracefully fall back to Hybrid results"
            # But the caller usually handles this. If we fail here, we can raise, or just return them sorted by original score.
            # "Never turn a model-loading failure into an empty search result."
            raise RuntimeError(f"CrossEncoder prediction failed: {e}")

        # 3. Assign scores
        for cand, score in zip(candidates, scores):
            cand.rerank_score = score

        # 4. Sort by rerank_score (descending), then doc_id (ascending) for deterministic ties
        # If rerank_score is None, we treat it as extremely low.
        candidates.sort(key=lambda c: (-(c.rerank_score if c.rerank_score is not None else float('-inf')), c.doc_id))

        # 5. Apply final top_k truncation
        if top_k > 0:
            return candidates[:top_k]
        return candidates
