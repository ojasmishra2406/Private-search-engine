import time
import os
from datasets import load_dataset
from src.evaluation.metrics import mrr_at_k, ndcg_at_k, precision_at_k, recall_at_k
from src.core.search import LexicalSearch
from src.core.indexer import IncrementalIndexer
import pickle

def evaluate_lexical_real():
    corpus = load_dataset("mteb/scifact", "corpus", split="corpus")
    queries = load_dataset("mteb/scifact", "queries", split="queries")
    qrels = load_dataset("BeIR/scifact-qrels", split="test")
    
    doc_ids = set([str(doc["_id"]) for doc in corpus])
    valid_qrels = [q for q in qrels if str(q["corpus-id"]) in doc_ids]
    valid_query_ids = set([str(q["query-id"]) for q in valid_qrels])
    queries = [q for q in queries if str(q["_id"]) in valid_query_ids]
    
    with open("scifact_lexical.pkl", "rb") as f:
        idx = pickle.load(f)
    # The tokenizer was initialized with the indexer
    indexer = IncrementalIndexer("scifact_lexical.pkl")
    indexer.index = idx
    
    lex_search = LexicalSearch(indexer.index, indexer.tokenizer)
    int_to_ext = {i: str(doc["_id"]) for i, doc in enumerate(corpus)}
    
    mrr_sum = 0.0
    ndcg_sum = 0.0
    prec_sum = 0.0
    rec_sum = 0.0
    count = 0
    
    qrel_dict = {}
    for q in valid_qrels:
        if q["score"] > 0:
            qrel_dict.setdefault(str(q["query-id"]), set()).add(str(q["corpus-id"]))
            
    for i, q in enumerate(queries):
        query_id = str(q["_id"])
        if query_id not in qrel_dict:
            continue
            
        ground_truth = qrel_dict[query_id]
        query_text = q["text"]
        
        res = lex_search.search(query_text, top_k=10)
        retrieved_ids = [int_to_ext[r.doc_id] for r in res]
        
        mrr_sum += mrr_at_k(retrieved_ids, ground_truth, k=10)
        ndcg_sum += ndcg_at_k(retrieved_ids, ground_truth, k=10)
        prec_sum += precision_at_k(retrieved_ids, ground_truth, k=10)
        rec_sum += recall_at_k(retrieved_ids, ground_truth, k=10)
        count += 1
        
    print("=========================================")
    print("--- SCIFACT LEXICAL EVALUATION RESULTS ---")
    print("=========================================")
    print(f"Total Queries Evaluated: {count}")
    if count > 0:
        print(f"Mean Reciprocal Rank (MRR@10): {mrr_sum/count:.4f}")
        print(f"Normalized DCG (nDCG@10): {ndcg_sum/count:.4f}")
        print(f"Precision (P@10): {prec_sum/count:.4f}")
        print(f"Recall (R@10): {rec_sum/count:.4f}")
    print("=========================================")

if __name__ == "__main__":
    evaluate_lexical_real()
