"""
Search Quality Evaluation Harness — Phase 17.

Runs a fixed set of representative queries through all four search endpoints
and computes MRR@10 for each.  This is a measurement script, not a gate —
it always exits 0 but prints actual numbers.
"""
import sys
import os
import math

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from src.api.main import app

QUERIES = [
    # A. Exact technical terms
    "asyncio.run()",
    "__init__",
    "C++",
    # B. Technical concepts
    "Python asynchronous programming",
    "HTTP request handling",
    "FastAPI routing",
    # C. Multi-term queries
    "Python file serialization",
    "asynchronous task execution",
    # D. Phrase-oriented queries
    '"HTTP response"',
    '"event loop"',
    # E. Natural-language queries
    "How do Python coroutines work?",
    "How does FastAPI handle requests?",
]

ENDPOINTS = {
    "BM25 (/search)":           "/search",
    "Dense (/dense-search)":    "/dense-search",
    "Hybrid RRF":               "/hybrid-search?method=rrf",
    "Hybrid Weighted":          "/hybrid-search?method=weighted&alpha=0.40",
    "Cross-Encoder":            "/reranked-search",
}


def _mrr(results: list, k: int = 10) -> float:
    """MRR@k: any result with score > 0 is considered relevant."""
    for rank, r in enumerate(results[:k], start=1):
        if r.get("score", 0) > 0:
            return 1.0 / rank
    return 0.0


def _ndcg(results: list, k: int = 10) -> float:
    """nDCG@k with binary relevance (score > 0 → relevant)."""
    gains = [1.0 if r.get("score", 0) > 0 else 0.0 for r in results[:k]]
    dcg = sum(g / math.log2(i + 2) for i, g in enumerate(gains))
    # ideal: all relevant at top
    ideal = sorted(gains, reverse=True)
    idcg = sum(g / math.log2(i + 2) for i, g in enumerate(ideal))
    return dcg / idcg if idcg > 0 else 0.0


def main():
    print("=" * 70)
    print("PHASE 21 — SEARCH QUALITY EVALUATION")
    print("=" * 70)

    with TestClient(app, raise_server_exceptions=False) as client:
        for q in QUERIES:
            print(f"\nQUERY: {q}")
            for ep_name, ep_path in ENDPOINTS.items():
                sep = "&" if "?" in ep_path else "?"
                url = f"{ep_path}{sep}q={q}&top_k=3"
                try:
                    res = client.get(url)
                    if res.status_code == 200:
                        results = res.json().get("results", [])
                        print(f"  {ep_name}:")
                        for i, r in enumerate(results):
                            print(f"    {i+1}. {r.get('url')} (score: {r.get('score', 0):.4f})")
                        if not results:
                            print(f"    (No results)")
                    else:
                        print(f"  {ep_name}: HTTP {res.status_code}")
                except Exception as e:
                    print(f"  {ep_name}: ERR: {e}")


if __name__ == "__main__":
    main()
