import time
from typing import List, Dict, Any
from .dataset import EvaluationDataset
from .metrics import recall_at_k, precision_at_k, mrr_at_k, ndcg_at_k

class EvaluationRunner:
    def __init__(self, dataset: EvaluationDataset):
        self.dataset = dataset

    def evaluate(self, retriever_func, k_values: List[int] = [1, 5, 10]) -> Dict[str, Any]:
        results = {}
        for k in k_values:
            results[f"Recall@{k}"] = []
            results[f"Precision@{k}"] = []
            results[f"MRR@{k}"] = []
            results[f"nDCG@{k}"] = []
            
        latencies = []
        per_query_results = []
        
        for query_obj in self.dataset.queries:
            q = query_obj.query
            relevant = set(query_obj.relevant_docs)
            
            t0 = time.perf_counter()
            retrieved_ids = retriever_func(q)
            t1 = time.perf_counter()
            
            latencies.append(t1 - t0)
            
            query_metrics = {}
            for k in k_values:
                rec = recall_at_k(retrieved_ids, relevant, k)
                prec = precision_at_k(retrieved_ids, relevant, k)
                mrr = mrr_at_k(retrieved_ids, relevant, k)
                ndcg = ndcg_at_k(retrieved_ids, relevant, k)
                
                results[f"Recall@{k}"].append(rec)
                results[f"Precision@{k}"].append(prec)
                results[f"MRR@{k}"].append(mrr)
                results[f"nDCG@{k}"].append(ndcg)
                
                query_metrics[f"nDCG@{k}"] = ndcg
                
            per_query_results.append({
                "query": q,
                "metrics": query_metrics
            })
            
        # Aggregate
        aggregated = {
            metric: sum(vals) / len(vals) if vals else 0.0
            for metric, vals in results.items()
        }
        
        latencies_sorted = sorted(latencies)
        p50 = latencies_sorted[len(latencies)//2] if latencies else 0.0
        p95 = latencies_sorted[int(len(latencies)*0.95)] if latencies else 0.0
        
        return {
            "metrics": aggregated,
            "latency": {
                "mean": sum(latencies) / len(latencies) if latencies else 0.0,
                "p50": p50,
                "p95": p95
            },
            "per_query": per_query_results
        }
