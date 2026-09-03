from typing import List, Tuple
try:
    from sentence_transformers import CrossEncoder
except ImportError:
    CrossEncoder = None

class CrossEncoderModel:
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2", device: str = "cpu"):
        if CrossEncoder is None:
            raise ImportError("sentence-transformers is required for CrossEncoderModel")
        # Load the model once
        self.model = CrossEncoder(model_name, device=device)
        self.device = device
        self.model_name = model_name

    def predict_batch(self, query_doc_pairs: List[Tuple[str, str]], batch_size: int = 16) -> List[float]:
        """
        Batch inference for query/document pairs.
        Returns a list of raw Cross-Encoder relevance scores.
        """
        if not query_doc_pairs:
            return []
            
        # CrossEncoder.predict handles batching inherently when passed a list of pairs,
        # but we can enforce the batch_size explicitly.
        scores = self.model.predict(query_doc_pairs, batch_size=batch_size, show_progress_bar=False)
        # It usually returns a numpy array, convert to python floats
        return [float(score) for score in scores]
