import sys
import os
import pickle
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.evaluation import EvaluationDataset, EvaluationRunner, recall_at_k, ndcg_at_k, mrr_at_k
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

def main():
    dataset = EvaluationDataset.load_from_json("evaluation/queries.json")
    
    with open('index.pkl', 'rb') as f:
        lex_index = pickle.load(f)
    tokenizer = Tokenizer()
    lex_retriever = LexicalSearch(lex_index, tokenizer)
    
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

    print("--- INVESTIGATING RECALL DROP ---")
    for q_obj in dataset.queries:
        q = q_obj.query
        relevant = set(q_obj.relevant_docs)
        
        # Base hybrid (top 10)
        base_res = hybrid_retriever.search(q, top_k=10, candidate_pool_size=500, method="weighted", alpha=0.5)
        base_ids = [r[0] for r in base_res]
        base_recall = recall_at_k(base_ids, relevant, 10)
        
        # Reranked (pool 50)
        pool_res = hybrid_retriever.search(q, top_k=50, candidate_pool_size=500, method="weighted", alpha=0.5)
        candidates = []
        for doc_id, score in pool_res:
            db_doc = doc_map.get(doc_id)
            text = f"{(db_doc.title or '')}\n{(db_doc.content or '')}"
            candidates.append(RerankCandidate(
                doc_id=doc_id,
                text=text,
                original_score=score
            ))
            
        reranked = reranker.rerank(q, candidates, top_k=10)
        reranked_ids = [r.doc_id for r in reranked]
        reranked_recall = recall_at_k(reranked_ids, relevant, 10)
        
        if reranked_recall < base_recall:
            print(f"\nQuery: {q}")
            print(f"Relevant Docs: {relevant}")
            print(f"Base Recall: {base_recall} | Reranked Recall: {reranked_recall}")
            print("Missing in Reranked Top 10:")
            for doc_id in relevant:
                if doc_id in base_ids and doc_id not in reranked_ids:
                    # Find its rank in reranked
                    all_reranked = reranker.rerank(q, candidates, top_k=50)
                    ranks = {r.doc_id: idx+1 for idx, r in enumerate(all_reranked)}
                    rank = ranks.get(doc_id, 'Not in pool')
                    print(f"  {doc_id} -> Reranked Rank: {rank}")
                    
                    # Print scores
                    if isinstance(rank, int):
                        cand = next((c for c in all_reranked if c.doc_id == doc_id), None)
                        if cand:
                            print(f"    Original Score: {cand.original_score:.4f}, Rerank Score: {cand.rerank_score:.4f}")
                            print(f"    Title: {doc_map[doc_id].title}")

if __name__ == "__main__":
    main()
