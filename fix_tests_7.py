from src.storage.database import get_db
from src.core.incremental_indexer import IncrementalIndexer
from src.storage.models import DBDocument

def build_test_indexes():
    db = next(get_db())
    # Assign int_ids sequentially if they don't have them
    docs = db.query(DBDocument).all()
    for i, d in enumerate(docs):
        d.int_id = i + 1
    db.commit()
    
    indexer = IncrementalIndexer()
    indexer.sync(db)

build_test_indexes()
