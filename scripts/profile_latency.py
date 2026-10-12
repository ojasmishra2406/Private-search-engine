import time
import json
import statistics
import os
from fastapi.testclient import TestClient

os.environ["DB_PATH"] = "sqlite:///data/search.db"
os.environ["LEXICAL_INDEX_PATH"] = "data/lexical_index.pkl"
os.environ["DENSE_INDEX_PATH"] = "data/dense_index.bin"
os.environ["CROSS_ENCODER_MODEL_NAME"] = "ms-marco-TinyBERT-L-2-v2"

from src.api.main import app

QUERIES = [
    "kubernetes cluster configuration", "financial earnings report Q3", "employee onboarding process",
    "annual performance review templates", "database backup strategy", "network security policies",
    "remote work guidelines", "project management agile methodology", "Q4 revenue projections",
    "software architecture design patterns", "machine learning model deployment", "customer support escalation matrix",
    "internal communications strategy", "legal compliance data privacy", "marketing campaign launch plans",
    "sales pipeline forecast", "cloud infrastructure cost optimization", "disaster recovery protocols",
    "human resources holiday schedule", "product roadmap 2027", "executive leadership changes",
    "vendor risk assessment", "API integration documentation", "user experience research findings",
    "brand guidelines and assets", "employee benefits package", "office reopening safety measures",
    "software release notes", "technical debt reduction plan", "quarterly all-hands meeting deck"
]

def run_profiling():
    with TestClient(app) as client:
        print("Warming up...")
        client.get("/health")
        client.get("/reranked-search", params={"q": "test", "role": "Admin", "top_k": 10})
        
        print(f"Running {len(QUERIES)} profiling queries...")
        timings = {"lexical": [], "dense": [], "fusion": [], "hydration": [], "reranking": [], "total": []}
        results = []
        
        for q in QUERIES:
            resp = client.get("/reranked-search", params={"q": q, "role": "Admin", "top_k": 10})
            if resp.status_code != 200:
                print(f"Error on query {q}: {resp.status_code}")
                continue
            timing = resp.json().get("timing", {})
            if timing:
                for k in timings.keys():
                    timings[k].append(timing.get(k, 0) * 1000)
                results.append({"query": q, "timing_ms": {k: v * 1000 for k, v in timing.items()}})
        
        print("\n--- FRESH PROFILING RESULTS (ms) ---")
        for key, vals in timings.items():
            if vals:
                print(f"{key.capitalize():>10}: p50 = {statistics.median(vals):6.2f} ms")
        if timings["total"]:
            sorted_total = sorted(timings["total"])
            print(f"\nOverall P50: {statistics.median(sorted_total):.2f} ms")
            print(f"Overall P95: {sorted_total[int(len(sorted_total) * 0.95)]:.2f} ms")

if __name__ == "__main__":
    run_profiling()
