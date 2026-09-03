import json
import time
from src.core.tokenizer import Tokenizer
from src.core.index import InvertedIndex
from src.core.search import LexicalSearch
from src.dense.embeddings import EmbeddingModel
from src.dense.vector_index import VectorIndex
from src.dense.retriever import DenseRetriever
from src.hybrid.retriever import HybridRetriever
from src.evaluation.runner import EvaluationRunner

def main():
    import pickle
    with open('index.pkl', 'rb') as f:
        idx = pickle.load(f)
    lex = LexicalSearch(idx, Tokenizer())
    
    emb = EmbeddingModel()
    vec = VectorIndex(dimension=emb.dimension)
    den = DenseRetriever(emb, vec)
    
    hyb = HybridRetriever(lex, den)
    
    from src.evaluation.dataset import EvaluationDataset
    dataset = EvaluationDataset.load_from_json('evaluation/queries.json')
    
    runner = EvaluationRunner(dataset)
    
    alphas = [0.25, 0.40, 0.50, 0.60, 0.75]
    for alpha in alphas:
        def get_res(q):
            return [r[0] for r in hyb.search(q, top_k=10, method="weighted", alpha=alpha)]
        print(f"\n--- Alpha {alpha} ---")
        result = runner.evaluate(get_res)
        metrics = result["metrics"]
        for k, v in metrics.items():
            print(f"{k}: {v:.4f}")

if __name__ == "__main__":
    main()
