import json
import os
import sys
import time
import pickle
import hashlib
from typing import List, Dict

# Add root directory to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.search import LexicalSearch
from src.core.tokenizer import Tokenizer
from src.core.bm25 import BM25Scorer
from src.core.metrics import Metrics

def load_eval_data(filepath: str) -> List[Dict]:
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    for item in data:
        item["relevant_doc_ids"] = set(
            hashlib.sha256(url.encode('utf-8')).hexdigest()
            for url in item["relevant_urls"]
        )
    return data

def run_evaluation(engine: LexicalSearch, eval_data: List[Dict], k_values=(5, 10)) -> Dict:
    results = {
        "queries": [],
        "metrics": {
            "Precision@5": 0.0,
            "Recall@5": 0.0,
            "Precision@10": 0.0,
            "Recall@10": 0.0,
            "MRR": 0.0,
            "NDCG@5": 0.0,
            "NDCG@10": 0.0,
        }
    }
    
    for item in eval_data:
        query = item["query"]
        relevant_ids = item["relevant_doc_ids"]
        
        # Max K we need is 10
        max_k = max(k_values)
        retrieved_docs = engine.search(query, top_k=max_k)
        retrieved_ids = [res.doc_id for res in retrieved_docs]
        
        q_result = {
            "query": query,
            "expected_urls": item["relevant_urls"],
            "retrieved_top_10": [
                {"doc_id": res.doc_id, "score": res.score} for res in retrieved_docs
            ],
            "metrics": {}
        }
        
        # Calculate per-query metrics
        p5 = Metrics.precision_at_k(retrieved_ids, relevant_ids, 5)
        r5 = Metrics.recall_at_k(retrieved_ids, relevant_ids, 5)
        p10 = Metrics.precision_at_k(retrieved_ids, relevant_ids, 10)
        r10 = Metrics.recall_at_k(retrieved_ids, relevant_ids, 10)
        mrr = Metrics.mrr(retrieved_ids, relevant_ids)
        ndcg5 = Metrics.ndcg_at_k(retrieved_ids, relevant_ids, 5)
        ndcg10 = Metrics.ndcg_at_k(retrieved_ids, relevant_ids, 10)
        
        q_result["metrics"] = {
            "Precision@5": p5,
            "Recall@5": r5,
            "Precision@10": p10,
            "Recall@10": r10,
            "MRR": mrr,
            "NDCG@5": ndcg5,
            "NDCG@10": ndcg10
        }
        
        results["queries"].append(q_result)
        
        # Add to aggregate
        for m in results["metrics"]:
            results["metrics"][m] += q_result["metrics"][m]
            
    # Average metrics
    n = len(eval_data)
    for m in results["metrics"]:
        results["metrics"][m] /= n
        
    return results

def main():
    print("Loading InvertedIndex...")
    start_load = time.time()
    try:
        with open('index.pkl', 'rb') as f:
            index = pickle.load(f)
    except FileNotFoundError:
        print("Error: index.pkl not found. Run ingestion first.")
        sys.exit(1)
        
    tokenizer = Tokenizer()
    print(f"Loaded index with {index.total_docs} docs in {time.time() - start_load:.2f}s")
    
    eval_file = os.path.join("evaluation", "queries.json")
    eval_data = load_eval_data(eval_file)
    print(f"Loaded {len(eval_data)} evaluation queries.")
    
    # Baseline
    print("\n--- BASELINE EVALUATION (k1=1.5, b=0.75) ---")
    engine = LexicalSearch(index, tokenizer)
    engine.scorer.k1 = 1.5
    engine.scorer.b = 0.75
    
    base_start = time.time()
    baseline_results = run_evaluation(engine, eval_data)
    base_time = time.time() - base_start
    
    print(f"Runtime: {base_time:.4f}s")
    for m, val in baseline_results["metrics"].items():
        print(f"  {m}: {val:.4f}")
        
    # Parameter Sweep
    print("\n--- BM25 PARAMETER SWEEP ---")
    k1_values = [1.0, 1.5, 2.0]
    b_values = [0.5, 0.75, 1.0]
    
    sweep_results = []
    
    # header
    print(f"{'k1':<5} | {'b':<5} | {'P@5':<6} | {'R@5':<6} | {'MRR':<6} | {'NDCG@5':<6} | {'P@10':<6} | {'R@10':<6} | {'NDCG@10':<7}")
    print("-" * 75)
    
    for k1 in k1_values:
        for b in b_values:
            engine.scorer.k1 = k1
            engine.scorer.b = b
            res = run_evaluation(engine, eval_data)
            m = res["metrics"]
            
            sweep_results.append({
                "k1": k1,
                "b": b,
                "metrics": m
            })
            
            print(f"{k1:<5.1f} | {b:<5.2f} | {m['Precision@5']:<6.4f} | {m['Recall@5']:<6.4f} | {m['MRR']:<6.4f} | {m['NDCG@5']:<6.4f} | {m['Precision@10']:<6.4f} | {m['Recall@10']:<6.4f} | {m['NDCG@10']:<7.4f}")
            
    # Find best
    best_config = max(sweep_results, key=lambda x: x["metrics"]["NDCG@10"])
    print(f"\nBest Configuration (by NDCG@10): k1={best_config['k1']}, b={best_config['b']} (NDCG@10 = {best_config['metrics']['NDCG@10']:.4f})")
    
    # Save reproducible output
    output_data = {
        "baseline_k1_1.5_b_0.75": baseline_results,
        "parameter_sweep": sweep_results,
        "best_config": {
            "k1": best_config["k1"],
            "b": best_config["b"]
        }
    }
    
    out_file = os.path.join("evaluation", "results.json")
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2)
    print(f"\nSaved full results to {out_file}")

if __name__ == "__main__":
    main()
