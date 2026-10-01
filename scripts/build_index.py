import time
from datasets import load_dataset
from src.core.indexer import IncrementalIndexer
from src.dense.vector_index import VectorIndex
from src.dense.embeddings import EmbeddingModel
import os
import pickle

def build_index():
    print("Loading SciFact dataset...")
    corpus = load_dataset("mteb/scifact", "corpus", split="corpus")
    
    print(f"Indexing SciFact corpus ({len(corpus)} documents)...")
    indexer = IncrementalIndexer("scifact_lexical.pkl")
    v_index = VectorIndex(384, "scifact_dense.index")
    embed_model = EmbeddingModel()
    
    texts = []
    ids = []
    
    t0 = time.time()
    for i, doc in enumerate(corpus):
        text = doc["title"] + " " + doc["text"]
        indexer.index.add_document(i, indexer.tokenizer.tokenize(text))
        texts.append(text)
        ids.append(i)
        
    with open("scifact_lexical.pkl", "wb") as f:
        pickle.dump(indexer.index, f)
        
    t1 = time.time()
    print(f"Lexical index built & saved in {t1-t0:.2f}s")
    
    print("Encoding dense vectors... (this may take ~45-60 seconds)")
    t0 = time.time()
    batch_size = 128
    for i in range(0, len(texts), batch_size):
        b_texts = texts[i:i+batch_size]
        b_ids = ids[i:i+batch_size]
        vecs = embed_model.encode(b_texts)
        v_index.add_vectors(b_ids, vecs)
    
    v_index.save()
    t1 = time.time()
    print(f"Dense index built & saved in {t1-t0:.2f}s")

if __name__ == "__main__":
    build_index()
