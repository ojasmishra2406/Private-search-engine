import os
import sys
import time
import pickle
import logging

# Add root directory to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ingestion.crawler import WebCrawler, CrawlerConfig
from src.ingestion.python_docs import PythonDocParser
from src.storage.database import Database
from src.storage.models import DBDocument
from src.core.tokenizer import Tokenizer
from src.core.index import InvertedIndex
from src.core.search import LexicalSearch

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def run_crawler_smoke_test():
    # Setup DB
    db = Database()
    db.init_db()
    session = db.get_session()
    
    # Configure Crawler for Python Docs
    config = CrawlerConfig(
        seed_urls=["https://docs.python.org/3.12/library/os.html"],
        allowed_domains=["docs.python.org"],
        max_depth=1,
        max_pages=20,
        timeout=5,
        delay=0.1,  # Fast for smoke test
        max_retries=1
    )
    
    crawler = WebCrawler(config)
    parser = PythonDocParser()
    
    db_stats = {
        'created': 0,
        'updated': 0,
        'skipped': 0,
        'failed_parse': 0
    }
    
    print("Starting crawl...")
    start_time = time.time()
    
    for url, html in crawler.crawl():
        try:
            doc = parser.parse_html_string(url, html)
            
            existing = session.query(DBDocument).filter_by(id=doc.id).first()
            if existing:
                if existing.content_hash == doc.content_hash:
                    db_stats['skipped'] += 1
                else:
                    existing.title = doc.title
                    existing.content = doc.content
                    existing.content_hash = doc.content_hash
                    db_stats['updated'] += 1
            else:
                db_doc = DBDocument(
                    id=doc.id,
                    title=doc.title,
                    content=doc.content,
                    url=doc.url,
                    content_hash=doc.content_hash,
                    created_at=doc.created_at
                )
                session.add(db_doc)
                db_stats['created'] += 1
                
        except Exception as e:
            logging.error(f"Failed to parse {url}: {e}")
            db_stats['failed_parse'] += 1
            
    session.commit()
    crawl_time = time.time() - start_time
    
    print("\n--- Crawl & DB Ingestion Complete ---")
    print(f"Time: {crawl_time:.2f}s")
    print(f"Crawler Stats: {crawler.stats}")
    print(f"DB Stats: {db_stats}")
    
    print("\nBuilding Index from SQLite...")
    index = InvertedIndex()
    tokenizer = Tokenizer()
    
    all_docs = session.query(DBDocument).all()
    index_start = time.time()
    for db_doc in all_docs:
        tokens = tokenizer.tokenize(db_doc.content)
        index.add_document(db_doc.id, tokens)
        
    print(f"Index built in {time.time() - index_start:.2f}s")
    print(f"Index Stats: {index.total_docs} docs, {index.total_tokens} tokens")
    
    # Save index for any other tools
    with open('index.pkl', 'wb') as f:
        pickle.dump(index, f)
        
    print("\n--- Smoke Test Searches ---")
    engine = LexicalSearch(index, tokenizer)
    for q in ["os", "path", "python"]:
        results = engine.search(q, top_k=2)
        print(f"Query '{q}' found {len(results)} results:")
        for res in results:
            # Look up external URL from DB
            doc_record = session.query(DBDocument).filter_by(id=res.doc_id).first()
            url = doc_record.url if doc_record else res.doc_id
            print(f"  - {url} (Score: {res.score:.2f})")

if __name__ == "__main__":
    run_crawler_smoke_test()
