import sys
import os
import pickle

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.evaluation import EvaluationDataset, EvaluationRunner
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
    print("--- PHASE 11 EVALUATION ---")
    
    # 1. Load Dataset
    dataset_path = "evaluation/queries.json"
    if not os.path.exists(dataset_path):
        print(f"Dataset {dataset_path} not found.")
        sys.exit(1)
        
    dataset = EvaluationDataset.load_from_json(dataset_path)
    print(f"Loaded {len(dataset.queries)} queries.")
    
    # 2. Initialize Subsystems
    print("Initializing BM25...")
    with open('index.pkl', 'rb') as f:
        lex_index = pickle.load(f)
    tokenizer = Tokenizer()
    lex_retriever = LexicalSearch(lex_index, tokenizer)
    
    print("Initializing Dense Retriever...")
    embed_model = EmbeddingModel()
    vec_index = VectorIndex(dimension=embed_model.dimension, index_path="dense.index", map_path="dense_map.pkl")
    dense_retriever = DenseRetriever(embed_model, vec_index)
    
    print("Initializing Hybrid Retriever...")
    hybrid_retriever = HybridRetriever(lex_retriever, dense_retriever)
    
    print("Initializing Reranker...")
    ce_model = CrossEncoderModel()
    reranker = CrossEncoderReranker(ce_model)
    
    db = Database()
    db.init_db()
    session = db.get_session()
    
    # Pre-load text into memory for faster reranking during evaluation
    # (avoiding hitting sqlite for every candidate)
    docs = session.query(DBDocument).filter_by(is_deleted=False).all()
    doc_text_map = {d.id: (d.title or "", d.content or "") for d in docs}
    session.close()

    runner = EvaluationRunner(dataset)
    k_values = [1, 5, 10]
    
    def get_lexical(q):
        return [r.doc_id for r in lex_retriever.search(q, top_k=10)]
        
    def get_dense(q):
        return [r[0] for r in dense_retriever.search(q, top_k=10)]
        
    def get_hybrid_rrf(q):
        return [r[0] for r in hybrid_retriever.search(q, top_k=10, method="rrf")]
        
    def get_hybrid_weighted(q):
        return [r[0] for r in hybrid_retriever.search(q, top_k=10, method="weighted", alpha=0.5)]
        
    from src.api.snippets import SnippetGenerator
    snippet_gen = SnippetGenerator(tokenizer)
    
    def get_reranked(q):
        # Fetch 50 from hybrid
        hybrid_res = hybrid_retriever.search(q, top_k=50, candidate_pool_size=500, method="weighted", alpha=0.5)
        candidates = []
        for doc_id, score in hybrid_res:
            title, content = doc_text_map.get(doc_id, ("", ""))
            snippet = snippet_gen.generate(content, q)["text"]
            text = f"{title}\n{snippet}\n{content}"
            candidates.append(RerankCandidate(
                doc_id=doc_id,
                text=text,
                original_score=score
            ))
        reranked = reranker.rerank(q, candidates, top_k=10)
        return [r.doc_id for r in reranked]
        
    methods = {
        "BM25": get_lexical,
        "Dense": get_dense,
        "Hybrid RRF": get_hybrid_rrf,
        "Hybrid Weighted": get_hybrid_weighted,
        "Hybrid+Reranker": get_reranked
    }
    
    report = {}
    print("\nRunning evaluations...")
    for name, func in methods.items():
        print(f"  Evaluating {name}...")
        report[name] = runner.evaluate(func, k_values=k_values)
        
    print("\n===========================================================")
    print(f"{'Method':<20} | {'MRR@10':<7} | {'nDCG@10':<7} | {'Recall@10':<9} | {'p50 (ms)':<8}")
    print("-" * 65)
    for name, res in report.items():
        mrr = res["metrics"]["MRR@10"]
        ndcg = res["metrics"]["nDCG@10"]
        rec = res["metrics"]["Recall@10"]
        p50 = res["latency"]["p50"] * 1000
        print(f"{name:<20} | {mrr:.4f}  | {ndcg:.4f}  | {rec:.4f}   | {p50:.2f}")
    print("===========================================================\n")
    
    # Delta analysis
    base = report["Hybrid Weighted"]["metrics"]
    reranked = report["Hybrid+Reranker"]["metrics"]
    print("--- RERANKING DELTA (Hybrid Weighted -> Reranked) ---")
    print(f"MRR@10:    {reranked['MRR@10'] - base['MRR@10']:+.4f}")
    print(f"nDCG@10:   {reranked['nDCG@10'] - base['nDCG@10']:+.4f}")
    print(f"Recall@10: {reranked['Recall@10'] - base['Recall@10']:+.4f}")
    
if __name__ == "__main__":
    main()
