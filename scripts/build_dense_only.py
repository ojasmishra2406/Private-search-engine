import time
from datasets import load_dataset
from src.dense.vector_index import VectorIndex
from src.dense.embeddings import EmbeddingModel

def build_dense():
    print("Loading SciFact dataset...")
    corpus = load_dataset("BeIR/scifact", "corpus")["corpus"]
    
    print(f"Indexing {len(corpus)} dense vectors...")
    v_index = VectorIndex(384, "data/scifact_dense.index")
    embed_model = EmbeddingModel()
    
    texts = []
    ids = []
    
    for i, doc in enumerate(corpus):
        text = doc.get("title", "") + " " + doc.get("text", "")
        texts.append(text)
        ids.append(i)
        
    print("Encoding dense vectors... (this may take ~45-60 seconds)")
    t0 = time.time()
    batch_size = 128
    for i in range(0, len(texts), batch_size):
        b_texts = texts[i:i+batch_size]
        b_ids = ids[i:i+batch_size]
        vecs = embed_model.encode(b_texts)
        
        import numpy as np
        v_index.add_vectors(np.array(b_ids, dtype=np.int64), vecs)

        print(f"Encoded {min(i+batch_size, len(texts))}/{len(texts)}...")
    
    v_index.save_atomic()
    t1 = time.time()
    print(f"Dense index built & saved in {t1-t0:.2f}s")

if __name__ == "__main__":
    build_dense()
