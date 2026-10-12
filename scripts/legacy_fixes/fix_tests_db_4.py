from src.storage.database import Database
from src.storage.models import DBDocument
from src.core.indexer import IncrementalIndexer

db_manager = Database("sqlite:///search.db")
db = db_manager.get_session()
for doc in db.query(DBDocument).all():
    doc.indexing_status = "PENDING"
db.commit()

indexer = IncrementalIndexer("index.pkl")
indexer.sync(db)
db.close()
