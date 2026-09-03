import math
from typing import List, Set

class Metrics:
    @staticmethod
    def precision_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
        """
        Calculates Precision@K.
        If fewer than K documents are retrieved, the denominator is still strictly K.
        If K=0, returns 0.0.
        """
        if k <= 0:
            return 0.0
        top_k = retrieved[:k]
        if not top_k:
            return 0.0
        
        # Count unique relevant documents in top K
        # Assuming `retrieved` shouldn't have duplicates, but if it does, 
        # standard metric treats them as list positions.
        relevant_count = sum(1 for doc in top_k if doc in relevant)
        return relevant_count / k

    @staticmethod
    def recall_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
        """
        Calculates Recall@K.
        If there are no relevant documents, behavior is undefined; returning 0.0 by convention.
        """
        if not relevant or k <= 0:
            return 0.0
        top_k = retrieved[:k]
        
        # Standard recall counts unique relevant documents retrieved
        retrieved_relevant = set(top_k).intersection(relevant)
        return len(retrieved_relevant) / len(relevant)

    @staticmethod
    def mrr(retrieved: List[str], relevant: Set[str]) -> float:
        """
        Calculates Mean Reciprocal Rank (MRR) for a single query.
        """
        if not relevant:
            return 0.0
            
        for idx, doc in enumerate(retrieved):
            if doc in relevant:
                return 1.0 / (idx + 1)
        return 0.0

    @staticmethod
    def ndcg_at_k(retrieved: List[str], relevant: Set[str], k: int) -> float:
        """
        Calculates NDCG@K assuming binary relevance (1 if relevant, 0 otherwise).
        """
        if not relevant or k <= 0:
            return 0.0
            
        top_k = retrieved[:k]
        dcg = 0.0
        for i, doc in enumerate(top_k):
            if doc in relevant:
                # Binary relevance DCG formula: rel / log2(i + 2)  (since i is 0-indexed)
                dcg += 1.0 / math.log2(i + 2)
                
        # Calculate IDCG (Ideal DCG)
        # Ideal ranking puts all relevant documents at the top
        ideal_relevant_count = min(len(relevant), k)
        idcg = 0.0
        for i in range(ideal_relevant_count):
            idcg += 1.0 / math.log2(i + 2)
            
        if idcg == 0.0:
            return 0.0
            
        return dcg / idcg
