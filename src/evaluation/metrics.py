import math
from typing import List, Set

def recall_at_k(retrieved_ids: List[str], relevant_ids: Set[str], k: int) -> float:
    if not relevant_ids:
        return 0.0
    retrieved_k = retrieved_ids[:k]
    hits = sum(1 for doc_id in retrieved_k if doc_id in relevant_ids)
    return hits / len(relevant_ids)

def precision_at_k(retrieved_ids: List[str], relevant_ids: Set[str], k: int) -> float:
    if k == 0:
        return 0.0
    retrieved_k = retrieved_ids[:k]
    if not retrieved_k:
        return 0.0
    hits = sum(1 for doc_id in retrieved_k if doc_id in relevant_ids)
    return hits / len(retrieved_k)

def mrr_at_k(retrieved_ids: List[str], relevant_ids: Set[str], k: int) -> float:
    retrieved_k = retrieved_ids[:k]
    for rank, doc_id in enumerate(retrieved_k, start=1):
        if doc_id in relevant_ids:
            return 1.0 / rank
    return 0.0

def ndcg_at_k(retrieved_ids: List[str], relevant_ids: Set[str], k: int) -> float:
    # Binary relevance assumption (1 if in relevant_ids, else 0)
    if not relevant_ids:
        return 0.0
        
    retrieved_k = retrieved_ids[:k]
    dcg = 0.0
    for rank, doc_id in enumerate(retrieved_k, start=1):
        if doc_id in relevant_ids:
            dcg += 1.0 / math.log2(rank + 1)
            
    # Ideal DCG: top min(k, len(relevant_ids)) are relevant
    idcg = 0.0
    ideal_hits = min(k, len(relevant_ids))
    for rank in range(1, ideal_hits + 1):
        idcg += 1.0 / math.log2(rank + 1)
        
    if idcg == 0.0:
        return 0.0
        
    return dcg / idcg
