import os
import numpy as np
from datasets import load_dataset
from src.evaluation.metrics import mrr_at_k, ndcg_at_k

from src.core.search import LexicalSearch
from src.core.indexer import IncrementalIndexer
from src.dense.vector_index import VectorIndex
from src.dense.embeddings import EmbeddingModel
from src.dense.retriever import DenseRetriever
from src.hybrid.retriever import HybridRetriever

def run_grid_search():
    print("Loading datasets...")
    corpus = load_dataset("BeIR/scifact", "corpus")["corpus"]
    queries = load_dataset("BeIR/scifact", "queries")["queries"]
    qrels = load_dataset("BeIR/scifact-qrels")["test"]

    qrel_dict = {}
    for row in qrels:
        qid = str(row["query-id"])
        docid = str(row["corpus-id"])
        score = row["score"]
        if qid not in qrel_dict:
            qrel_dict[qid] = {}
        qrel_dict[qid][docid] = score

    print("Loading indices...")
    indexer = IncrementalIndexer("scifact_lexical.pkl")
    v_index = VectorIndex(384, "scifact_dense.index")
    embed_model = EmbeddingModel()
    
    lex_search = LexicalSearch(indexer.index, indexer.tokenizer)
    dense_search = DenseRetriever(embed_model, v_index)
    hybrid_search = HybridRetriever(lex_search, dense_search)
    
    int_to_ext = {i: str(doc["_id"]) for i, doc in enumerate(corpus)}
    
    alphas = [0.1, 0.3, 0.5, 0.7, 0.9]
    results = {}
    
    for alpha in alphas:
        all_query_metrics = []
        count = 0
        for q in queries:
            query_id = str(q["_id"])
            if query_id not in qrel_dict:
                continue
                
            ground_truth = set(qrel_dict[query_id].keys())
            query_text = q["text"]
            
            hybrid_res = hybrid_search.search(query_text, top_k=50, method='rrf', alpha=alpha)
            
            mapped_candidates = []
            for int_id, score in hybrid_res:
                ext_id = int_to_ext.get(int_id)
                if ext_id:
                    mapped_candidates.append(ext_id)
                    
            q_mrr = mrr_at_k(mapped_candidates, ground_truth, k=10)
            q_ndcg = ndcg_at_k(mapped_candidates, ground_truth, k=10)
            all_query_metrics.append((q_mrr, q_ndcg))
            
            count += 1
            
                
        mean_mrr = np.mean([m[0] for m in all_query_metrics])
        mean_ndcg = np.mean([m[1] for m in all_query_metrics])
        print(f"Alpha {alpha}: MRR@10={mean_mrr:.4f}, nDCG@10={mean_ndcg:.4f}")
        results[alpha] = mean_mrr
        
    best_alpha = max(results, key=results.get)
    print(f"\nBest alpha: {best_alpha}")

if __name__ == "__main__":
    run_grid_search()
