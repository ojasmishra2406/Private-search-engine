import pytest
import hashlib

def fix_api_db():
    from sqlalchemy import create_engine
    from src.storage.models import Base, DBDocument
    from sqlalchemy.orm import sessionmaker

    engine = create_engine("sqlite:///search.db")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    docs = [
        {"id": "doc_python", "url": "http://python.org", "title": "Python", "content": "python is a programming language"},
        {"id": "doc_json", "url": "http://json.org", "title": "JSON", "content": "json format"},
        {"id": "doc_os", "url": "http://docs.python.org/3/library/os.path.html", "title": "os.path", "content": "os.path.join"},
        {"id": "doc_asyncio", "url": "http://docs.python.org/3/library/asyncio.html", "title": "asyncio", "content": "asyncio list append"},
        {"id": "doc_init", "url": "http://docs.python.org/3/reference/datamodel.html", "title": "__init__", "content": "__init__ c++ utf-8 httpexception dict comprehension"},
    ]
    for d in docs:
        if not db.query(DBDocument).filter_by(id=d["id"]).first():
            h = hashlib.sha256(d["content"].encode()).hexdigest()
            db.add(DBDocument(id=d["id"], url=d["url"], title=d["title"], content=d["content"], version=1, indexing_status="indexed", content_hash=h))
    db.commit()
    db.close()
    
fix_api_db()
