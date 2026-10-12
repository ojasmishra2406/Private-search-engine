from typing import List, Tuple
from src.dense.vector_index import VectorIndex
import time

class DenseRetriever:
    """
    Coordinates query encoding and ANN index searching.
    Expects a generic embedding model (either real or mock) supporting encode().
    """
    def __init__(self, model, vector_index: VectorIndex):
        self.model = model
        self.vector_index = vector_index

    def search(self, query: str, authorized_int_ids: set = None, top_k: int = 5) -> List[Tuple[int, float]]:
        if not query or not query.strip():
            return []
            
        t_enc_start = time.perf_counter()
        query_vector = self.model.encode_query(query)
        query_embedding = query_vector.reshape(1, -1)
        t_enc_end = time.perf_counter()
        
        t_faiss_start = time.perf_counter()
        res = self.vector_index.search(query_embedding, authorized_int_ids=authorized_int_ids, top_k=top_k)
        t_faiss_end = time.perf_counter()
        
        print(f"DEBUG DENSE: encode={(t_enc_end - t_enc_start)*1000:.2f}ms, faiss={(t_faiss_end - t_faiss_start)*1000:.2f}ms")
        return res
