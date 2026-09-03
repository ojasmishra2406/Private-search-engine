import os
import sys
import glob
import time
from datetime import datetime

# Add root directory to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.storage.database import Database
from src.storage.models import DBDocument, IndexingStatus
from src.ingestion.python_docs import PythonDocParser
from src.core.indexer import IncrementalIndexer

def run_ingestion(data_dir: str):
    db = Database()
    db.init_db()
    session = db.get_session()
    
    parser = PythonDocParser()
    
    html_files = glob.glob(os.path.join(data_dir, '**', '*.html'), recursive=True)
    
    stats = {
        'discovered': len(html_files),
        'created': 0,
        'updated': 0,
        'skipped': 0,
        'failed': 0
    }
    
    print(f"Found {stats['discovered']} HTML files. Starting ingestion...")
    start_time = time.time()
    
    for file_path in html_files:
        try:
            doc = parser.parse_html(file_path, data_dir)
            
            # Check if exists
            existing = session.query(DBDocument).filter_by(id=doc.id).first()
            if existing:
                if existing.content_hash == doc.content_hash:
                    # Phase 7: UNCHANGED -> SKIP
                    stats['skipped'] += 1
                else:
                    # Phase 7: MODIFIED -> RE-INDEX (mark PENDING)
                    existing.title = doc.title
                    existing.content = doc.content
                    existing.content_hash = doc.content_hash
                    existing.url = doc.url
                    existing.version += 1
                    existing.indexing_status = IndexingStatus.PENDING.value
                    existing.updated_at = datetime.utcnow()
                    stats['updated'] += 1
            else:
                # Phase 7: NEW -> INDEX (mark PENDING)
                db_doc = DBDocument(
                    id=doc.id,
                    title=doc.title,
                    content=doc.content,
                    url=doc.url,
                    content_hash=doc.content_hash,
                    created_at=doc.created_at,
                    version=1,
                    indexing_status=IndexingStatus.PENDING.value
                )
                session.add(db_doc)
                stats['created'] += 1
                
        except Exception as e:
            print(f"Failed to parse {file_path}: {e}")
            stats['failed'] += 1
            
        if (stats['created'] + stats['updated'] + stats['skipped'] + stats['failed']) % 100 == 0:
            print(f"Processed {sum(stats.values()) - stats['discovered']} / {stats['discovered']}...")
            
    session.commit()
    print(f"Database ingestion complete in {time.time() - start_time:.2f} seconds.")
    print(f"Stats: {stats}")
    
    print("Running Incremental Indexer...")
    indexer_start = time.time()
    indexer = IncrementalIndexer('index.pkl')
    
    # Phase 8: Dense Retrieval integration
    try:
        from src.dense.indexer import DenseIndexer
        from src.dense.embeddings import EmbeddingModel
        from src.dense.vector_index import VectorIndex
        
        print("Initializing Dense Indexer...")
        emb_model = EmbeddingModel()
        vector_index = VectorIndex()
        dense_indexer = DenseIndexer(emb_model, vector_index)
    except Exception as e:
        print(f"Dense indexer failed to initialize: {e}")
        dense_indexer = None
        
    sync_stats = indexer.sync(session, dense_indexer=dense_indexer)
    
    print(f"Incremental indexing complete in {time.time() - indexer_start:.2f} seconds.")
    print(f"Indexer Stats: {sync_stats}")
    print(f"Lexical Index size: {indexer.index.total_docs} docs")
    if dense_indexer:
        print(f"Dense Index size: {dense_indexer.vector_index.total_docs} vectors")
    
    print("Ingestion and indexing complete.")

if __name__ == "__main__":
    target_dir = os.path.join("data", "python-3.12-docs-html")
    run_ingestion(target_dir)
