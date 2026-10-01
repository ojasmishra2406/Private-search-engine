import time
from datasets import load_dataset
from src.evaluation.metrics import mrr_at_k, ndcg_at_k
from src.core.search import LexicalSearch
from src.core.indexer import IncrementalIndexer
from src.dense.vector_index import VectorIndex
from src.dense.embeddings import EmbeddingModel
from src.hybrid.retriever import HybridRetriever
from src.reranker.cross_encoder import CrossEncoderModel
from src.reranker.reranker import CrossEncoderReranker, RerankCandidate

def evaluate_full_pipeline():
    print("Loading SciFact dataset...")
    # Use mteb/scifact for corpus and queries because that's what the on-disk index was built with!
    corpus = load_dataset("mteb/scifact", "corpus", split="corpus")
    queries = load_dataset("mteb/scifact", "queries", split="queries")
    qrels = load_dataset("BeIR/scifact-qrels", split="test")
    
    doc_ids = set([str(doc["_id"]) for doc in corpus])
    valid_qrels = [q for q in qrels if str(q["corpus-id"]) in doc_ids]
    valid_query_ids = set([str(q["query-id"]) for q in valid_qrels])
    queries = [q for q in queries if str(q["_id"]) in valid_query_ids]
    
    print("Loading pre-built indexes and models...")
    indexer = IncrementalIndexer("scifact_lexical.pkl")
    v_index = VectorIndex(384, "scifact_dense.index")
    embed_model = EmbeddingModel()
    
    ce_model = CrossEncoderModel(model_name="ms-marco-TinyBERT-L-2-v2")
    reranker = CrossEncoderReranker(ce_model)
    
    lex_search = LexicalSearch(indexer.index, indexer.tokenizer)
    from src.dense.retriever import DenseRetriever
    dense_search = DenseRetriever(embed_model, v_index)
    hybrid_search = HybridRetriever(lex_search, dense_search)
    
    # Map internal IDs back to SciFact IDs EXACTLY as they were built
    int_to_ext = {i: str(doc["_id"]) for i, doc in enumerate(corpus)}
    
    # Pre-compute document texts for reranking text hydration
    doc_texts = {i: doc["title"] + " " + doc["text"] for i, doc in enumerate(corpus)}
    
    mrr_sum = 0.0
    ndcg_sum = 0.0
    count = 0
    
    qrel_dict = {}
    for q in valid_qrels:
        if q["score"] > 0:
            qrel_dict.setdefault(str(q["query-id"]), set()).add(str(q["corpus-id"]))
            
    print(f"Evaluating {len(queries)} queries via FULL PIPELINE (Hybrid + Cross-Encoder Reranker)...")
    for i, q in enumerate(queries):
        query_id = str(q["_id"])
        if query_id not in qrel_dict:
            continue
            
        ground_truth = qrel_dict[query_id]
        query_text = q["text"]
        
        # 1. Hybrid Search (fetch top 50 candidates)
        hybrid_res = hybrid_search.search(query_text, top_k=50, method='rrf')
        
        # 2. Text Hydration
        candidates = []
        for doc_id, score in hybrid_res:
            candidates.append(RerankCandidate(
                doc_id=doc_id, # keep internal integer id for now
                text=doc_texts[doc_id],
                original_score=score
            ))
            
        # 3. Rerank
        if candidates:
            reranked_cands = reranker.rerank(query_text, candidates, top_k=0)
            
            # Map back to string IDs based on reranked order
            retrieved_ids = [int_to_ext[c.doc_id] for c in reranked_cands[:10]] # Top 10 for eval
        else:
            retrieved_ids = []
        
        mrr = mrr_at_k(retrieved_ids, ground_truth, k=10)
        ndcg = ndcg_at_k(retrieved_ids, ground_truth, k=10)
        
        mrr_sum += mrr
        ndcg_sum += ndcg
        count += 1
        
        if (i+1) % 50 == 0:
            print(f"Evaluated {i+1}/{len(queries)} queries...")
        
    print("\n=========================================")
    print("--- SCIFACT FULL PIPELINE (HYBRID+RERANK) EVALUATION RESULTS ---")
    print("=========================================")
    print(f"Total Queries Evaluated: {count}")
    if count > 0:
        print(f"Mean Reciprocal Rank (MRR@10): {mrr_sum/count:.4f}")
        print(f"Normalized DCG (nDCG@10): {ndcg_sum/count:.4f}")
    print("=========================================")

if __name__ == "__main__":
    evaluate_full_pipeline()
