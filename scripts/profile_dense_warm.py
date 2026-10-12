import time
from src.dense.embeddings import EmbeddingModel

def main():
    print("Loading embedding model...")
    model = EmbeddingModel()
    
    query = "software architecture design patterns"
    
    print("Warming up (first encode)...")
    t_w0 = time.perf_counter()
    _ = model.encode_query(query)
    t_w1 = time.perf_counter()
    print(f"Warmup Encode time: {(t_w1 - t_w0)*1000:.2f} ms")
    
    print("Benchmarking encode (second time)...")
    t0 = time.perf_counter()
    query_vector = model.encode_query("a completely different query to avoid caching")
    t1 = time.perf_counter()
    print(f"Actual Encode time: {(t1 - t0)*1000:.2f} ms")

if __name__ == "__main__":
    main()
