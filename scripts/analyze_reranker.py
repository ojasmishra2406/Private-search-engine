import time
from datasets import load_dataset
from src.core.indexer import IncrementalIndexer
from src.dense.vector_index import VectorIndex
from src.dense.embeddings import EmbeddingModel
from src.hybrid.retriever import HybridRetriever
from src.core.search import LexicalSearch
from src.dense.retriever import DenseRetriever
from src.reranker.cross_encoder import CrossEncoderModel
from src.reranker.reranker import CrossEncoderReranker, RerankCandidate

def analyze_degradation():
    print("Loading datasets...")
    queries_ds = load_dataset("mteb/scifact", "queries", split="queries")
    corpus_ds = load_dataset("mteb/scifact", "corpus", split="corpus")
    qrels_ds = load_dataset("BeIR/scifact-qrels", split="test")

    corpus_ids = set([str(d["_id"]) for d in corpus_ds])
    qrels = [q for q in qrels_ds if str(q["corpus-id"]) in corpus_ids]
    valid_query_ids = set([str(q["query-id"]) for q in qrels])
    queries = [q for q in queries_ds if str(q["_id"]) in valid_query_ids]

    ground_truth_map = {}
    for q in qrels:
        qid = str(q["query-id"])
        cid = str(q["corpus-id"])
        if qid not in ground_truth_map:
            ground_truth_map[qid] = []
        ground_truth_map[qid].append(cid)

    print("Loading models and indexes...")
    indexer = IncrementalIndexer("data/scifact_lexical.pkl")
    v_index = VectorIndex(384, "data/scifact_dense.index")
    embed_model = EmbeddingModel()
    lex_search = LexicalSearch(indexer.index, indexer.tokenizer)
    dense_search = DenseRetriever(embed_model, v_index)
    hybrid_search = HybridRetriever(lex_search, dense_search)

    ce_model = CrossEncoderModel(model_name="ms-marco-TinyBERT-L-2-v2")
    reranker = CrossEncoderReranker(ce_model)

    corpus = list(corpus_ds)
    int_to_ext = {i: str(doc["_id"]) for i, doc in enumerate(corpus)}
    doc_texts = {i: doc["title"] + " " + doc["text"] for i, doc in enumerate(corpus)}

    better = 0
    worse = 0
    same = 0

    print("Analyzing 300 queries...")
    for i, q in enumerate(queries):
        qid = str(q["_id"])
        query_text = q["text"]
        truth = ground_truth_map.get(qid, [])

        hybrid_res = hybrid_search.search(query_text, top_k=50, method='rrf', alpha=0.7)
        
        hybrid_ext_ids = []
        candidates = []
        for int_id, score in hybrid_res:
            ext_id = int_to_ext.get(int_id)
            if ext_id:
                hybrid_ext_ids.append(ext_id)
                candidates.append(RerankCandidate(doc_id=int_id, text=doc_texts[int_id], original_score=0.0))
        
        hybrid_rank = float('inf')
        for rank, ext_id in enumerate(hybrid_ext_ids):
            if ext_id in truth:
                hybrid_rank = rank + 1
                break

        if not candidates:
            same += 1
            continue
            
        reranked_res = reranker.rerank(query_text, candidates, top_k=0)
        reranked_ext_ids = [int_to_ext[c.doc_id] for c in reranked_res]

        reranked_rank = float('inf')
        for rank, ext_id in enumerate(reranked_ext_ids):
            if ext_id in truth:
                reranked_rank = rank + 1
                break

        if reranked_rank < hybrid_rank:
            better += 1
        elif reranked_rank > hybrid_rank:
            worse += 1
        else:
            same += 1

    print("\n--- Reranker Impact ---")
    print(f"Queries Improved: {better}")
    print(f"Queries Degraded: {worse}")
    print(f"Queries Unchanged: {same}")

if __name__ == '__main__':
    analyze_degradation()
