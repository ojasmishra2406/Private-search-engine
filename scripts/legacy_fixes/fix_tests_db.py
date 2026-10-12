import os
import shutil
import hashlib
from src.storage.database import Database
from src.storage.models import DBDocument
from src.core.indexer import IncrementalIndexer

def rebuild_perfect_test_db():
    # 1. Wipe root artifacts
    for f in ["search.db", "index.pkl", "dense.index", "dense_map.pkl"]:
        if os.path.exists(f): os.remove(f)
        
    # 2. Create DB
    db_manager = Database("sqlite:///search.db")
    db_manager.init_db()
    db = db_manager.get_session()
    
    docs = [
        {"id": "doc_python", "url": "http://python.org", "title": "Python", "content": "python is a programming language json"},
        {"id": "doc_os", "url": "http://docs.python.org/3/library/os.path.html", "title": "os.path", "content": "os.path.join"},
        {"id": "doc_asyncio", "url": "http://docs.python.org/3/library/asyncio.html", "title": "asyncio", "content": "asyncio list append"},
        {"id": "doc_init", "url": "http://docs.python.org/3/reference/datamodel.html", "title": "__init__", "content": "__init__ c++ utf-8 httpexception dict comprehension"},
        {"id": "doc_scale", "url": "http://scale", "title": "Scale Document", "content": "Scale Document"},
        {"id": "doc_api_1", "url": "http://api1", "title": "api1", "content": "python database " * 150},
        {"id": "doc_api_2", "url": "http://api2", "title": "api2", "content": "json " * 150}
    ]
    
    for i, d in enumerate(docs):
        h = hashlib.sha256(d["content"].encode()).hexdigest()
        doc = DBDocument(id=d["id"], int_id=i+1, url=d["url"], title=d["title"], content=d["content"], version=1, indexing_status="pending", content_hash=h, allowed_roles="Public")
        db.add(doc)
    db.commit()
    
    # 3. Build Indexes via IncrementalIndexer
    os.environ["DB_PATH"] = "sqlite:///search.db"
    os.environ["LEXICAL_INDEX_PATH"] = "index.pkl"
    os.environ["DENSE_INDEX_PATH"] = "dense.index"
    
    indexer = IncrementalIndexer()
    indexer.sync(db)
    db.close()

if __name__ == "__main__":
    rebuild_perfect_test_db()
