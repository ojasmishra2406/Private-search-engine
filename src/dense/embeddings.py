import numpy as np
from typing import List

class EmbeddingModel:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2', device: str = 'cpu'):
        self.model_name = model_name
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name, device=device)
            self.dimension = self.model.get_embedding_dimension()
        except ImportError:
            raise ImportError("sentence-transformers is not installed.")
            
    def encode(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)
        # Normalize embeddings to 1 for cosine similarity using dot product (Inner Product in FAISS)
        embeddings = self.model.encode(texts, batch_size=batch_size, normalize_embeddings=True, show_progress_bar=False)
        return embeddings.astype(np.float32)

    import functools
    @functools.lru_cache(maxsize=1000)
    def _encode_query_cached(self, query: str) -> np.ndarray:
        return self.encode([query])[0]

    def encode_query(self, query: str) -> np.ndarray:
        return self._encode_query_cached(query).copy()

class MockEmbeddingModel:
    """Deterministic mock embedding provider for fast unit testing."""
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        
    def encode(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)
            
        embeddings = []
        for text in texts:
            # Deterministic random generator based on content hash
            np.random.seed(abs(hash(text)) % (2**32))
            emb = np.random.randn(self.dimension)
            # Normalize
            emb = emb / np.linalg.norm(emb)
            embeddings.append(emb)
            
        return np.array(embeddings, dtype=np.float32)

    import functools
    @functools.lru_cache(maxsize=1000)
    def _encode_query_cached(self, query: str) -> np.ndarray:
        return self.encode([query])[0]

    def encode_query(self, query: str) -> np.ndarray:
        return self._encode_query_cached(query).copy()
