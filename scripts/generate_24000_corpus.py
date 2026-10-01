import os
import time
import numpy as np
import faiss
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.storage.models import Base, DBDocument
from src.core.indexer import IncrementalIndexer

def generate_corpus():
    print("Generating 24,000 documents and vectors for scale testing...")
    
    db_path = "data/scale_search2.db"
    lex_path = "data/scale_lexical2.pkl"
    idx_path = "data/scale_dense2.index"
    
    if os.path.exists(db_path):
        try: os.remove(db_path)
        except: pass
    if os.path.exists(lex_path):
        try: os.remove(lex_path)
        except: pass
    if os.path.exists(idx_path):
        try: os.remove(idx_path)
        except: pass
    
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    docs = []
    roles = ["Admin", "HR", "Engineering", "Public", "Finance"]
    t0 = time.time()
    for i in range(24000):
        docs.append(DBDocument(
            id=f"doc_{i}",
            int_id=i,
            url=f"http://internal/{i}",
            title=f"Scale Document {i}",
            content=f"This is a massive scale test document. Index {i}. Relevant to {roles[i%5]}.",
            content_hash=f"hash_{i}",
            allowed_roles=roles[i%5],
            indexing_status="PENDING"
        ))
        if len(docs) >= 5000:
            session.bulk_save_objects(docs)
            session.commit()
            docs = []
            print(f"Inserted {i+1} documents...")
            
    if docs:
        session.bulk_save_objects(docs)
        session.commit()
    t1 = time.time()
    print(f"SQLite insertion complete in {t1-t0:.2f}s")
    
    # Generate FAISS HNSW Index
    d = 384
    print(f"Generating 24,000 dense vectors (d={d})...")
    np.random.seed(42)
    vectors = np.random.random((24000, d)).astype('float32')
    faiss.normalize_L2(vectors)
    
    base_index = faiss.IndexHNSWFlat(d, 32, faiss.METRIC_INNER_PRODUCT)
    index = faiss.IndexIDMap(base_index)
    index.add_with_ids(vectors, np.arange(24000))
    faiss.write_index(index, idx_path)
    
    print(f"FAISS index written to {idx_path}")
    
    # Generate BM25
    print("Building BM25 Lexical Index...")
    t0 = time.time()
    indexer = IncrementalIndexer(lex_path)
    # We will simulate the sync so it just builds lexical
    indexer.sync(session, dense_indexer=None)
    t1 = time.time()
    print(f"Lexical index built in {t1-t0:.2f}s")
    
    print(f"Total FAISS Vectors: {index.ntotal}")
    print(f"Total SQLite Documents: {session.query(DBDocument).count()}")
    session.close()

if __name__ == "__main__":
    generate_corpus()
