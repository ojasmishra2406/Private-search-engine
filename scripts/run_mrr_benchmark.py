import time
import numpy as np
import os
from fastapi.testclient import TestClient
from src.api.main import app
from src.api.config import settings

def run_mrr():
    with TestClient(app) as client:
        print("API Ready! Executing MRR Benchmark and 50x Latency Loop...")
        
        # 1. Latency loop (50 runs)
        latencies = []
        # warmup
        client.get("/reranked-search?q=scale+document&role=Admin")
        
        for _ in range(50):
            t0 = time.time()
            client.get("/reranked-search?q=scale+document&role=Admin")
            latencies.append((time.time() - t0)*1000)
            
        print(f"\n--- Latency Benchmark ({len(latencies)} runs) ---")
        print(f"P50 Latency: {np.percentile(latencies, 50):.2f} ms")
        print(f"P95 Latency: {np.percentile(latencies, 95):.2f} ms")
        
        # 2. MRR Eval
        res = client.get("/reranked-search?q=Index+42&role=Admin").json()
        items = res.get("results", [])
        mrr = 0.0
        for i, item in enumerate(items):
            if "Index 42" in item.get("snippet", "") or "doc_42" == item.get("doc_id", ""):
                rank = i + 1
                mrr = 1.0 / rank
                break
                
        print(f"\n--- MRR@5 Evaluation ---")
        print(f"Query: 'Index 42'")
        print(f"Admin MRR@5: {mrr:.2f}")

if __name__ == "__main__":
    run_mrr()
