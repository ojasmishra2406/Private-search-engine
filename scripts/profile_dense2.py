import time
import numpy as np
from src.dense.vector_index import VectorIndex

def main():
    print("Loading vector index...")
    v_index = VectorIndex(index_path="data/scale_dense.index")
    
    query_embedding = np.random.randn(1, 384).astype(np.float32)
    query_embedding = query_embedding / np.linalg.norm(query_embedding, axis=1, keepdims=True)
    
    # 1. FAISS Search without authorization
    print("Benchmarking FAISS search without auth...")
    t0 = time.perf_counter()
    res = v_index.search(query_embedding, top_k=10)
    t1 = time.perf_counter()
    print(f"FAISS Search without auth: {(t1 - t0)*1000:.2f} ms")
    
    # 2. FAISS Search with authorization
    allowed = set(range(10000, 24000))  # 14,000 allowed IDs
    print("Benchmarking FAISS search with 14k auth IDs...")
    t2 = time.perf_counter()
    res2 = v_index.search(query_embedding, authorized_int_ids=allowed, top_k=10)
    t3 = time.perf_counter()
    print(f"FAISS Search with auth: {(t3 - t2)*1000:.2f} ms")

if __name__ == "__main__":
    main()
