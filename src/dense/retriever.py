from typing import List, Tuple
from src.dense.vector_index import VectorIndex

class DenseRetriever:
    """
    Coordinates query encoding and ANN index searching.
    Expects a generic embedding model (either real or mock) supporting encode().
    """
    def __init__(self, model, vector_index: VectorIndex):
        self.model = model
        self.vector_index = vector_index

    def search(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        if not query or not query.strip():
            return []
            
        # Encode single query string utilizing LRU cache
        query_vector = self.model.encode_query(query)
        query_embedding = query_vector.reshape(1, -1)
        
        # Dispatch to FAISS ANN index
        return self.vector_index.search(query_embedding, top_k=top_k)
