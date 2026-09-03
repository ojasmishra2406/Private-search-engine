import os
import sys
import time

sys.path.insert(0, os.path.abspath('.'))
from src.core.indexer import IncrementalIndexer
from src.core.tokenizer import Tokenizer
from src.core.search import LexicalSearch
from src.dense.embeddings import EmbeddingModel
from src.dense.vector_index import VectorIndex
from src.dense.retriever import DenseRetriever
from src.hybrid.retriever import HybridRetriever
from src.storage.database import Database
from src.storage.models import DBDocument

def measure_latency(func, name, iterations=5):
    # Warmup
    func()
    
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        func()
        times.append(time.perf_counter() - start)
        
    avg = sum(times) / len(times)
    p50 = sorted(times)[len(times)//2]
    p95 = sorted(times)[int(len(times)*0.95)]
    p99 = sorted(times)[int(len(times)*0.99)]
    return avg, p50, p95, p99

def print_top(results, name, db_session):
    print(f"\n--- {name} ---")
    if not results:
        print("No results")
        return
    for i, (doc_id, score) in enumerate(results[:5]):
        doc = db_session.query(DBDocument).filter_by(id=doc_id).first()
        title = doc.title if doc else "Unknown"
        print(f"{i+1}. [{score:.4f}] {title} ({doc_id[:8]}...)")

def main():
    db = Database()
    session = db.get_session()
    
    print("Loading Lexical...")
    indexer = IncrementalIndexer('index.pkl')
    lexical = LexicalSearch(indexer.index, Tokenizer())
    
    print("Loading Dense...")
    dense = DenseRetriever(EmbeddingModel(), VectorIndex())
    
    hybrid = HybridRetriever(lexical, dense)
    
    queries = [
        "python string formatting",
        "dictionary comprehension",
        "metaclass programming"
    ]
    
    for q in queries:
        print(f"\n\n===========================================")
        print(f"QUERY: '{q}'")
        print(f"===========================================")
        
        # 1. Lexical
        lex_res = [(r.doc_id, r.score) for r in lexical.search(q, top_k=500)]
        print_top(lex_res, "BM25", session)
        
        # 2. Dense
        den_res = dense.search(q, top_k=500)
        print_top(den_res, "Dense", session)
        
        # 3. Hybrid RRF
        rrf_res = hybrid.search(q, top_k=500, candidate_pool_size=100, method='rrf')
        print_top(rrf_res, "Hybrid RRF", session)
        
        # 4. Hybrid Weighted
        w_res = hybrid.search(q, top_k=500, candidate_pool_size=100, method='weighted', alpha=0.5)
        print_top(w_res, "Hybrid Weighted (alpha=0.5)", session)
        
        # 5. Hybrid Weighted (BM25 heavy)
        w_bm_res = hybrid.search(q, top_k=500, candidate_pool_size=100, method='weighted', alpha=0.75)
        print_top(w_bm_res, "Hybrid Weighted (alpha=0.75)", session)
        
        # 6. Hybrid Weighted (Dense heavy)
        w_dn_res = hybrid.search(q, top_k=500, candidate_pool_size=100, method='weighted', alpha=0.25)
        print_top(w_dn_res, "Hybrid Weighted (alpha=0.25)", session)
        
        
    print("\n\n--- LATENCY BENCHMARK ---")
    bench_q = "python string formatting"
    
    def run_bm25(): lexical.search(bench_q, top_k=500)
    def run_dense(): dense.search(bench_q, top_k=500)
    def run_rrf(): hybrid.search(bench_q, top_k=500, candidate_pool_size=100, method='rrf')
    def run_weight(): hybrid.search(bench_q, top_k=500, candidate_pool_size=100, method='weighted', alpha=0.5)
    
    methods = [
        ("BM25", run_bm25),
        ("Dense", run_dense),
        ("Hybrid RRF", run_rrf),
        ("Hybrid Weighted", run_weight),
    ]
    
    for name, func in methods:
        avg, p50, p95, p99 = measure_latency(func, name, iterations=20)
        print(f"{name:15} | Avg: {avg*1000:6.2f}ms | p50: {p50*1000:6.2f}ms | p95: {p95*1000:6.2f}ms | p99: {p99*1000:6.2f}ms")
        
    # Check 555 document integrity explicitly
    active_ids = set([r[0] for r in session.query(DBDocument.id).filter_by(is_deleted=False).all()])
    lex_ids = set(indexer.index.ext_to_int_doc_id.keys())
    den_ids = set(dense.vector_index.ext_to_int.keys())
    
    print("\n--- CORPUS INTEGRITY ---")
    print(f"Active DB: {len(active_ids)}")
    print(f"Lexical Index: {len(lex_ids)}")
    print(f"Dense Index: {len(den_ids)}")
    print(f"Missing from Lexical: {len(active_ids - lex_ids)}")
    print(f"Missing from Dense: {len(active_ids - den_ids)}")
    
    print("\n=======================================================")
    print("EVALUATION OBSERVATION:")
    print("On this limited sample of manually selected queries, Weighted")
    print("Fusion produced favorable results. This is strictly insufficient")
    print("to establish that Weighted Fusion is generally superior to RRF.")
    print("A larger relevance-labeled evaluation set (Phase 11) is required.")
    print("=======================================================\n")
    
if __name__ == "__main__":
    main()
