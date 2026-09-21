import sqlite3
import os
import pickle
import faiss

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "search.db")

def check_parity():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # DB Count
    cursor.execute("SELECT COUNT(*) FROM documents WHERE is_deleted=False")
    db_count = cursor.fetchone()[0]
    
    # Lexical Count
    with open('index.pkl', 'rb') as f:
        idx = pickle.load(f)
    lex_count = idx.total_docs
    
    # Dense Count
    f_idx = faiss.read_index('dense.index')
    dense_count = f_idx.ntotal
    
    print("\n--- STATE PARITY VERIFICATION ---")
    print(f"Active SQLite Documents: {db_count}")
    print(f"BM25 Inverted Index Docs: {lex_count}")
    print(f"FAISS Vector Index Docs: {dense_count}")
    
    if db_count == lex_count == dense_count:
        print("PARITY ACHIEVED: TRUE")
    else:
        print("PARITY MISMATCH DETECTED!")
        
if __name__ == '__main__':
    check_parity()
