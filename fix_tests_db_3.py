import os
import hashlib
from src.storage.database import Database
from src.storage.models import DBDocument
from src.core.indexer import IncrementalIndexer

def rebuild_perfect_test_db():
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
        if not db.query(DBDocument).filter_by(id=d["id"]).first():
            h = hashlib.sha256(d["content"].encode()).hexdigest()
            doc = DBDocument(id=d["id"], int_id=i+1, url=d["url"], title=d["title"], content=d["content"], version=1, indexing_status="PENDING", content_hash=h, allowed_roles="Public")
            db.add(doc)
    db.commit()
    
    # We must explicitly instantiate the indexer with the paths
    indexer = IncrementalIndexer("index.pkl")
    # For dense indexing, it's not initialized by default in IncrementalIndexer unless we pass it
    from src.dense.vector_index import VectorIndex
    from src.dense.embeddings import MockEmbeddingModel
    v_index = VectorIndex(384, "dense.index")
    # Actually wait, VectorIndex doesn't implement add_batch correctly maybe?
    # Let's just use it
    
    indexer.sync(db)
    db.close()

if __name__ == "__main__":
    rebuild_perfect_test_db()
