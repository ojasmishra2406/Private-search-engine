import time
import numpy as np
import faiss
import json
import os
import sys

def measure_hnsw_scale():
    print("--- BENCHMARK: FAISS HNSW SCALE (24,000 Vectors) ---")
    d = 384
    num_vectors = 24000
    np.random.seed(42)
    vectors = np.random.random((num_vectors, d)).astype('float32')
    faiss.normalize_L2(vectors)
    
    t0 = time.time()
    base_index = faiss.IndexHNSWFlat(d, 32, faiss.METRIC_INNER_PRODUCT)
    index = faiss.IndexIDMap(base_index)
    index.add_with_ids(vectors, np.arange(num_vectors))
    t_build = time.time() - t0
    print(f"Index built in {t_build:.2f} seconds.")
    
    queries = np.random.random((100, d)).astype('float32')
    faiss.normalize_L2(queries)
    
    t0 = time.time()
    D, I = index.search(queries, 10)
    t_search = time.time() - t0
    
    avg_latency = (t_search / 100) * 1000
    print(f"HNSW ANN Search Latency (batch=100, k=10): {avg_latency:.2f} ms per query")
    return avg_latency

def measure_reranker_quantization():
    print("\n--- BENCHMARK: RERANKER QUANTIZATION (FP32 vs INT8) ---")
    query = "What is the architecture of the private search engine?"
    docs = [
        {"id": "1", "text": "The search engine uses a hybrid architecture with BM25 and FAISS."},
        {"id": "2", "text": "It features a Corrective RAG gate for hallucination prevention."},
        {"id": "3", "text": "Role based access control is enforced at the database level."},
        {"id": "4", "text": "ONNX runtime is used to quantize the cross-encoder to INT8."}
    ] * 4

    try:
        from sentence_transformers import CrossEncoder
        import torch
        print("Loading FP32 PyTorch CrossEncoder baseline...")
        # explicitly set num threads to avoid spikes
        torch.set_num_threads(4)
        fp32_model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", device="cpu")
        pairs = [[query, d["text"]] for d in docs]
        
        for _ in range(3): fp32_model.predict(pairs) # warmup
        
        t0 = time.time()
        iters = 10
        for _ in range(iters):
            fp32_model.predict(pairs)
        t_fp32 = (time.time() - t0) / iters * 1000
        print(f"FP32 PyTorch Latency (Batch=16): {t_fp32:.2f} ms")
    except Exception as e:
        print(f"Failed FP32: {e}")
        t_fp32 = 0
        
    try:
        from flashrank import Ranker, RerankRequest
        print("Loading INT8 ONNX FlashRank model...")
        import onnxruntime
        sess_options = onnxruntime.SessionOptions()
        sess_options.intra_op_num_threads = 4
        
        onnx_model = Ranker(model_name="ms-marco-MiniLM-L-12-v2", cache_dir="/tmp/flashrank")
        req = RerankRequest(query=query, passages=docs)
        
        for _ in range(3): onnx_model.rerank(req) # warmup
        
        t0 = time.time()
        iters = 10
        for _ in range(iters):
            onnx_model.rerank(req)
        t_int8 = (time.time() - t0) / iters * 1000
        print(f"INT8 ONNX Latency (Batch=16): {t_int8:.2f} ms")
        
        if t_fp32 > 0:
            reduction = (1 - (t_int8 / t_fp32)) * 100
            print(f"Latency Reduction: {reduction:.1f}%")
    except Exception as e:
        print(f"Failed ONNX: {e}")

if __name__ == "__main__":
    with open("docs/proofs/scale_and_quantization_proof.txt", "w") as f:
        sys.stdout = f
        measure_hnsw_scale()
        measure_reranker_quantization()
        sys.stdout = sys.__stdout__
    print("Proof generated: docs/proofs/scale_and_quantization_proof.txt")
