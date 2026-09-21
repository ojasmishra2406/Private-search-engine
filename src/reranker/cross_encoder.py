from typing import List, Tuple
import math
from flashrank import Ranker, RerankRequest

from src.api.config import settings

class CrossEncoderModel:
    def __init__(self, model_name: str = "ms-marco-MiniLM-L-12-v2", device: str = "cpu"):
        # Load the ONNX INT8 model once
        self.model = Ranker(model_name=model_name, cache_dir=settings.CACHE_DIR)
        self.device = device
        self.model_name = model_name

    def predict_batch(self, query_doc_pairs: List[Tuple[str, str]], batch_size: int = 16) -> List[float]:
        """
        Batch inference for query/document pairs using FlashRank (ONNX).
        Returns a list of raw Cross-Encoder relevance scores (logits).
        """
        if not query_doc_pairs:
            return []
            
        # Group by query since flashrank expects a single query per request
        # Assuming all pairs in a batch usually belong to the same query (RAG pipeline)
        # We will iterate them or just pass them as a single query since the pipeline currently sends them together
        query = query_doc_pairs[0][0]
        passages = []
        for i, (q, doc) in enumerate(query_doc_pairs):
            passages.append({"id": str(i), "text": doc})
            
        req = RerankRequest(query=query, passages=passages)
        results = self.model.rerank(req)
        
        # FlashRank returns a list sorted by score, we must map them back to original order
        # FlashRank output format: [{'id': '0', 'text': '...', 'score': 0.99}, ...]
        score_map = {int(res["id"]): res["score"] for res in results}
        
        logits = []
        for i in range(len(query_doc_pairs)):
            p = float(score_map[i])
            # Inverse sigmoid (logit function) to retrieve raw logit for CRAG
            p = max(1e-9, min(p, 1.0 - 1e-9))
            logit = math.log(p / (1.0 - p))
            logits.append(logit)
            
        return logits
