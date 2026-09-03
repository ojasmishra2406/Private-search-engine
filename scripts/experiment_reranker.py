import sys
import os
import pickle
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.evaluation import EvaluationDataset, recall_at_k, ndcg_at_k, mrr_at_k
from src.core.search import LexicalSearch
from src.core.tokenizer import Tokenizer
from src.dense.embeddings import EmbeddingModel
from src.dense.vector_index import VectorIndex
from src.dense.retriever import DenseRetriever
from src.hybrid.retriever import HybridRetriever
from src.reranker.cross_encoder import CrossEncoderModel
from src.reranker.reranker import CrossEncoderReranker, RerankCandidate
from src.storage.database import Database
from src.storage.models import DBDocument
from src.api.snippets import SnippetGenerator

def main():
    dataset = EvaluationDataset.load_from_json("evaluation/queries.json")
    
    with open('index.pkl', 'rb') as f:
        lex_index = pickle.load(f)
    tokenizer = Tokenizer()
    lex_retriever = LexicalSearch(lex_index, tokenizer)
    snippet_gen = SnippetGenerator(tokenizer)
    
    embed_model = EmbeddingModel()
    vec_index = VectorIndex(dimension=embed_model.dimension, index_path="dense.index", map_path="dense_map.pkl")
    dense_retriever = DenseRetriever(embed_model, vec_index)
    hybrid_retriever = HybridRetriever(lex_retriever, dense_retriever)
    
    ce_model = CrossEncoderModel()
    reranker = CrossEncoderReranker(ce_model)
    
    db = Database()
    db.init_db()
    session = db.get_session()
    docs = session.query(DBDocument).filter_by(is_deleted=False).all()
    doc_map = {d.id: d for d in docs}
    session.close()

    print("--- 1. CANDIDATE POOL SIZE EXPERIMENT ---")
    pool_sizes = [20, 50, 100, 200]
    reranker.max_document_chars = 4000
    
    print(f"{'Pool':<6} | {'Recall@10':<9} | {'MRR@10':<7} | {'nDCG@10':<7} | {'p50 (ms)':<8}")
    print("-" * 50)
    for pool in pool_sizes:
        recalls, mrrs, ndcgs, lats = [], [], [], []
        for q_obj in dataset.queries:
            q = q_obj.query
            relevant = set(q_obj.relevant_docs)
            
            t0 = time.perf_counter()
            pool_res = hybrid_retriever.search(q, top_k=pool, candidate_pool_size=500, method="weighted", alpha=0.5)
            candidates = []
            for doc_id, score in pool_res:
                db_doc = doc_map.get(doc_id)
                # Text construction: Title + Snippet + Content
                title = db_doc.title or ""
                content = db_doc.content or ""
                snippet = snippet_gen.generate(content, q)["text"]
                text = f"{title}\n{snippet}\n{content}"
                candidates.append(RerankCandidate(
                    doc_id=doc_id,
                    text=text,
                    original_score=score
                ))
            
            reranked = reranker.rerank(q, candidates, top_k=10)
            t1 = time.perf_counter()
            
            reranked_ids = [r.doc_id for r in reranked]
            
            recalls.append(recall_at_k(reranked_ids, relevant, 10))
            mrrs.append(mrr_at_k(reranked_ids, relevant, 10))
            ndcgs.append(ndcg_at_k(reranked_ids, relevant, 10))
            lats.append(t1 - t0)
            
        p50 = sorted(lats)[len(lats)//2] * 1000
        print(f"{pool:<6} | {sum(recalls)/len(recalls):.4f}   | {sum(mrrs)/len(mrrs):.4f}  | {sum(ndcgs)/len(ndcgs):.4f}  | {p50:.2f}")

    print("\n--- 2. DOCUMENT TRUNCATION EXPERIMENT ---")
    truncs = [1000, 2000, 4000, 8000]
    pool = 50
    print(f"{'Chars':<6} | {'Recall@10':<9} | {'MRR@10':<7} | {'nDCG@10':<7} | {'p50 (ms)':<8}")
    print("-" * 50)
    for trunc in truncs:
        reranker.max_document_chars = trunc
        recalls, mrrs, ndcgs, lats = [], [], [], []
        for q_obj in dataset.queries:
            q = q_obj.query
            relevant = set(q_obj.relevant_docs)
            
            t0 = time.perf_counter()
            pool_res = hybrid_retriever.search(q, top_k=pool, candidate_pool_size=500, method="weighted", alpha=0.5)
            candidates = []
            for doc_id, score in pool_res:
                db_doc = doc_map.get(doc_id)
                # Text construction: Title + Snippet + Content
                title = db_doc.title or ""
                content = db_doc.content or ""
                snippet = snippet_gen.generate(content, q)["text"]
                text = f"{title}\n{snippet}\n{content}"
                candidates.append(RerankCandidate(
                    doc_id=doc_id,
                    text=text,
                    original_score=score
                ))
            
            reranked = reranker.rerank(q, candidates, top_k=10)
            t1 = time.perf_counter()
            
            reranked_ids = [r.doc_id for r in reranked]
            
            recalls.append(recall_at_k(reranked_ids, relevant, 10))
            mrrs.append(mrr_at_k(reranked_ids, relevant, 10))
            ndcgs.append(ndcg_at_k(reranked_ids, relevant, 10))
            lats.append(t1 - t0)
            
        p50 = sorted(lats)[len(lats)//2] * 1000
        print(f"{trunc:<6} | {sum(recalls)/len(recalls):.4f}   | {sum(mrrs)/len(mrrs):.4f}  | {sum(ndcgs)/len(ndcgs):.4f}  | {p50:.2f}")

if __name__ == "__main__":
    main()
