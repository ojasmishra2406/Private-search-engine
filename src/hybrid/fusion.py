from typing import List, Tuple, Dict, Any

def normalize_scores(scores: List[float]) -> List[float]:
    """
    Min-max normalize a list of scores to the range [0.0, 1.0].
    If all scores are identical, or the list is empty/length 1,
    returns 1.0 for all (or empty).
    """
    if not scores:
        return []
    
    min_s = min(scores)
    max_s = max(scores)
    
    if max_s == min_s:
        return [1.0] * len(scores)
        
    range_s = max_s - min_s
    return [(s - min_s) / range_s for s in scores]


def weighted_fusion(
    bm25_results: List[Tuple[str, float]], 
    dense_results: List[Tuple[str, float]], 
    alpha: float = 0.5
) -> List[Tuple[str, float]]:
    """
    Combines BM25 and Dense results using normalized weighted fusion.
    
    alpha = 1.0 means 100% BM25
    alpha = 0.0 means 100% Dense
    
    Documents missing from one list are assigned a normalized score of 0.0 for that list.
    """
    if alpha < 0.0 or alpha > 1.0:
        raise ValueError("alpha must be between 0.0 and 1.0")
        
    bm25_ids = [doc_id for doc_id, _ in bm25_results]
    bm25_scores = [score for _, score in bm25_results]
    
    dense_ids = [doc_id for doc_id, _ in dense_results]
    dense_scores = [score for _, score in dense_results]
    
    norm_bm25_scores = normalize_scores(bm25_scores)
    norm_dense_scores = normalize_scores(dense_scores)
    
    bm25_dict = dict(zip(bm25_ids, norm_bm25_scores))
    dense_dict = dict(zip(dense_ids, norm_dense_scores))
    
    all_docs = set(bm25_ids) | set(dense_ids)
    
    fused = []
    for doc_id in all_docs:
        b_score = bm25_dict.get(doc_id, 0.0)
        d_score = dense_dict.get(doc_id, 0.0)
        
        final_score = (alpha * b_score) + ((1.0 - alpha) * d_score)
        fused.append((doc_id, final_score))
        
    # Sort descending by score, then ascending by doc_id to ensure determinism
    fused.sort(key=lambda x: (-x[1], x[0]))
    return fused


def reciprocal_rank_fusion(
    bm25_results: List[Tuple[str, float]], 
    dense_results: List[Tuple[str, float]], 
    k: int = 60
) -> List[Tuple[str, float]]:
    """
    Combines BM25 and Dense results using Reciprocal Rank Fusion (RRF).
    
    RRF(d) = Σ (1 / (k + rank(d)))
    
    Documents missing from one list contribute 0 from that list.
    k is a smoothing constant, typically 60.
    """
    if k <= 0:
        raise ValueError("k must be a positive integer")
        
    rrf_scores: Dict[str, float] = {}
    
    # rank is 1-indexed
    for rank, (doc_id, _) in enumerate(bm25_results, start=1):
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (k + rank))
        
    for rank, (doc_id, _) in enumerate(dense_results, start=1):
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (k + rank))
        
    fused = list(rrf_scores.items())
    
    # Sort descending by score, then ascending by doc_id to ensure determinism
    fused.sort(key=lambda x: (-x[1], x[0]))
    return fused
