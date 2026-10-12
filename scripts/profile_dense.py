import time
import numpy as np
from src.dense.vector_index import VectorIndex
from src.dense.embeddings import EmbeddingModel

def main():
    print("Loading embedding model...")
    model = EmbeddingModel()
    
    print("Loading vector index...")
    v_index = VectorIndex(index_path="data/scale_dense.index")
    
    print("Benchmarking encode...")
    query = "software architecture design patterns"
    
    t0 = time.perf_counter()
    query_vector = model.encode_query(query)
    t1 = time.perf_counter()
    print(f"Encode time: {(t1 - t0)*1000:.2f} ms")
    
    query_embedding = query_vector.reshape(1, -1)
    
    print("Benchmarking FAISS search...")
    t2 = time.perf_counter()
    res = v_index.search(query_embedding, top_k=10)
    t3 = time.perf_counter()
    print(f"FAISS Search time: {(t3 - t2)*1000:.2f} ms")

if __name__ == "__main__":
    main()
