from typing import List, Tuple, Optional
from src.core.search import LexicalSearch
from src.dense.retriever import DenseRetriever
from src.hybrid.fusion import weighted_fusion, reciprocal_rank_fusion

import time

class HybridRetriever:
    """
    Orchestrates Hybrid Retrieval by combining Lexical (BM25) and Dense (FAISS) 
    candidates using Weighted Fusion or Reciprocal Rank Fusion (RRF).
    """
    def __init__(self, lexical_retriever: LexicalSearch, dense_retriever: DenseRetriever):
        self.lexical_retriever = lexical_retriever
        self.dense_retriever = dense_retriever

    def search(
        self, 
        query: str, 
        top_k: int = 10, 
        candidate_pool_size: int = 100, 
        method: str = 'rrf', 
        alpha: float = 0.5,
        rrf_k: int = 60,
        return_diagnostics: bool = False
    ):
        t_start = time.perf_counter()
        
        # Lexical search
        bm25_raw = self.lexical_retriever.search(query, top_k=candidate_pool_size)
        bm25_candidates = [(res.doc_id, res.score) for res in bm25_raw]
        t_lexical = time.perf_counter()
        
        # Dense search
        try:
            dense_candidates = self.dense_retriever.search(query, top_k=candidate_pool_size)
        except Exception as e:
            dense_candidates = []
        t_dense = time.perf_counter()
            
        if not bm25_candidates and not dense_candidates:
            if return_diagnostics:
                return [], {}, {}
            return []
            
        # Fusion
        if method == 'weighted':
            fused = weighted_fusion(bm25_candidates, dense_candidates, alpha=alpha)
        elif method == 'rrf':
            fused = reciprocal_rank_fusion(bm25_candidates, dense_candidates, k=rrf_k)
        else:
            raise ValueError(f"Unknown hybrid method: {method}")
        t_fusion = time.perf_counter()
            
        if top_k <= 0:
            fused = []
        else:
            fused = fused[:top_k]
            
        if return_diagnostics:
            diagnostics = {}
            bm25_map = dict(bm25_candidates)
            dense_map = dict(dense_candidates)
            for doc_id, score in fused:
                diagnostics[doc_id] = {
                    'lexical_score': bm25_map.get(doc_id),
                    'dense_score': dense_map.get(doc_id)
                }
            timing = {
                'lexical': t_lexical - t_start,
                'dense': t_dense - t_lexical,
                'fusion': t_fusion - t_dense
            }
            return fused, diagnostics, timing
            
        return fused
