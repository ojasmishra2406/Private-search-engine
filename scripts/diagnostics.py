import pickle
import sys
from src.core.tokenizer import Tokenizer
from src.core.index import InvertedIndex
from src.dense.embeddings import EmbeddingModel
from src.dense.vector_index import VectorIndex
from src.storage.database import Database
from src.storage.models import DBDocument, IndexingStatus

def run_diagnostics():
    print("========================================")
    print("      PHASE 18 INDEX DIAGNOSTICS      ")
    print("========================================\n")
    
    # 1. Check DB
    print("[1/3] Checking SQLite Database...")
    db = Database()
    db.init_db()
    session = db.get_session()
    
    db_docs = session.query(DBDocument).all()
    active_docs = [d for d in db_docs if not d.is_deleted]
    pending = [d for d in active_docs if d.indexing_status == IndexingStatus.PENDING.value]
    
    db_count = len(active_docs)
    print(f"      Total DB Documents (Active): {db_count}")
    print(f"      Pending Indexing: {len(pending)}")
    session.close()

    # 2. Check Lexical Index
    print("\n[2/3] Checking Lexical Index (index.pkl)...")
    try:
        with open('index.pkl', 'rb') as f:
            lexical = pickle.load(f)
        lex_count = lexical.total_docs
        print(f"      Lexical Documents: {lex_count}")
    except Exception as e:
        print(f"      Error loading lexical index: {e}")
        lex_count = 0
        lexical = None

    # 3. Check Dense Index
    print("\n[3/3] Checking Dense Index (dense.index)...")
    try:
        vec_index = VectorIndex()
        dense_count = vec_index.total_docs
        print(f"      Dense Documents: {dense_count}")
    except Exception as e:
        print(f"      Error loading dense index: {e}")
        dense_count = 0
        vec_index = None

    print("\n========================================")
    print("              SUMMARY                   ")
    print("========================================")
    print(f"Database : {db_count}")
    print(f"Lexical  : {lex_count}")
    print(f"Dense    : {dense_count}")
    
    if db_count == lex_count == dense_count:
        # Check strict ID parity
        db_ids = {d.id for d in active_docs}
        lex_ids = set(lexical.ext_to_int_doc_id.keys()) if lexical else set()
        dense_ids = set(vec_index.ext_to_int.keys()) if vec_index else set()
        
        missing_in_lex = db_ids - lex_ids
        missing_in_db_from_lex = lex_ids - db_ids
        missing_in_dense = db_ids - dense_ids
        missing_in_db_from_dense = dense_ids - db_ids
        
        if missing_in_lex or missing_in_db_from_lex or missing_in_dense or missing_in_db_from_dense:
            print("\nSTATUS: FAIL [ID Mismatches Detected]")
            print(f"Missing in Lex: {missing_in_lex}")
            print(f"Missing in DB (Lex): {missing_in_db_from_lex}")
            print(f"Missing in Dense: {missing_in_dense}")
            print(f"Missing in DB (Dense): {missing_in_db_from_dense}")
            sys.exit(1)
            
        print(f"\nSTATUS: PASS [All systems perfectly synchronized and exact ID parity verified at {db_count}]")
        sys.exit(0)
    else:
        print("\nSTATUS: FAIL [Mismatch detected]")
        sys.exit(1)

if __name__ == "__main__":
    run_diagnostics()
