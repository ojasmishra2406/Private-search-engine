import os
import time
import shutil
import numpy as np
import faiss
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.storage.models import Base, DBDocument
from src.core.indexer import IncrementalIndexer

def generate_corpus():
    TOTAL_DOCS = 100000
    print(f"Generating {TOTAL_DOCS:,} documents and vectors for scale testing...")
    
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
    for i in range(TOTAL_DOCS):
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
        if len(docs) >= 10000:
            session.bulk_save_objects(docs)
            session.commit()
            docs = []
            print(f"Inserted {i+1:,} documents...")
            
    if docs:
        session.bulk_save_objects(docs)
        session.commit()
    t1 = time.time()
    print(f"SQLite insertion complete in {t1-t0:.2f}s")
    
    # Generate FAISS HNSW Index
    d = 384
    print(f"Generating {TOTAL_DOCS:,} dense vectors (d={d})...")
    np.random.seed(42)
    vectors = np.random.random((TOTAL_DOCS, d)).astype('float32')
    faiss.normalize_L2(vectors)
    
    t0 = time.time()
    base_index = faiss.IndexHNSWFlat(d, 32, faiss.METRIC_INNER_PRODUCT)
    index = faiss.IndexIDMap(base_index)
    index.add_with_ids(vectors, np.arange(TOTAL_DOCS))
    faiss.write_index(index, idx_path)
    t1 = time.time()
    print(f"FAISS index built and written to {idx_path} in {t1-t0:.2f}s")
    
    # Generate BM25
    print("Building BM25 Lexical Index...")
    t0 = time.time()
    indexer = IncrementalIndexer(lex_path)
    indexer.sync(session, dense_indexer=None)
    t1 = time.time()
    print(f"Lexical index built in {t1-t0:.2f}s")
    
    # Copy to search.db, lexical_index.pkl, dense_index.bin for unified benchmarking
    shutil.copy2(db_path, "data/search.db")
    shutil.copy2(lex_path, "data/lexical_index.pkl")
    shutil.copy2(idx_path, "data/dense_index.bin")
    print("Copied 100k artifacts to data/search.db, data/lexical_index.pkl, data/dense_index.bin")
    
    print("\n--- FINAL 100K SCALE REPORT ---")
    print(f"Total FAISS Vectors: {index.ntotal:,}")
    print(f"Total SQLite Documents: {session.query(DBDocument).count():,}")
    print(f"Total Lexical Documents: {indexer.index.total_docs:,}")
    session.close()

if __name__ == "__main__":
    generate_corpus()
