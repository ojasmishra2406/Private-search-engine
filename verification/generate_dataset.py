import json
from src.storage.database import Database
from src.storage.models import DBDocument

db = Database()
db.init_db()
session = db.get_session()

# Fetch some interesting docs to formulate queries around
docs = session.query(DBDocument).filter_by(is_deleted=False).limit(100).all()

queries = []

# Manual mapping logic based on titles/content patterns we know exist in the Python 3.12 docs
manual_queries = [
    ("python string formatting", "format string syntax", "7. input and output"),
    ("dictionary comprehension", "6. expressions", "5. data structures"),
    ("metaclass programming", "abc - abstract base classes", "3. data model"),
    ("list sorting", "5. data structures", "sorting how to"),
    ("multithreading", "threading", "17. concurrent execution"),
    ("asyncio event loop", "asyncio", "coroutine"),
    ("regular expressions", "re - regular expression"),
    ("unit testing", "unittest", "testing"),
    ("garbage collection", "gc - garbage collector interface", "memory management"),
    ("json serialization", "json - json encoder"),
    ("csv parsing", "csv - csv file reading"),
    ("file input output", "7. input and output", "reading and writing files"),
    ("command line arguments", "argparse", "sys.argv"),
    ("sqlite3 database", "sqlite3 - db-api"),
    ("http requests", "urllib.request", "http.client"),
    ("time and date", "datetime - basic date"),
    ("random numbers", "random - generate pseudo-random"),
    ("math functions", "math - mathematical functions"),
    ("subprocess execution", "subprocess - subprocess management"),
    ("xml processing", "xml.etree.elementtree"),
    ("logging tutorial", "logging howto"),
    ("abstract syntax tree", "ast - abstract syntax trees"),
    ("dataclasses", "dataclasses - data classes"),
    ("type hinting", "typing - support for type hints"),
    ("memory profiling", "tracemalloc"),
    ("context managers", "contextlib - utilities for with"),
    ("c extension module", "extending and embedding", "building c and c++ extensions"),
    ("socket programming", "socket - low-level networking"),
    ("base64 encoding", "base64 - base16"),
    ("virtual environments", "venv - creation of virtual")
]

# We will search the corpus for these titles/keywords to find the exact doc_ids
for q_tuple in manual_queries:
    query_str = q_tuple[0]
    keywords = q_tuple[1:]
    
    relevant_ids = set()
    for doc in docs:
        title_lower = (doc.title or "").lower()
        if any(kw in title_lower for kw in keywords):
            relevant_ids.add(doc.id)
            
    # We only add it if we found at least one relevant document
    if relevant_ids:
        queries.append({
            "query": query_str,
            "relevant_docs": list(relevant_ids)
        })

# Wait, the limit(100) might miss many! Let's query all docs.
docs = session.query(DBDocument).filter_by(is_deleted=False).all()
queries = []
for q_tuple in manual_queries:
    query_str = q_tuple[0]
    keywords = q_tuple[1:]
    
    relevant_ids = set()
    for doc in docs:
        title_lower = (doc.title or "").lower()
        if any(kw in title_lower for kw in keywords):
            relevant_ids.add(doc.id)
            
    if relevant_ids:
        queries.append({
            "query": query_str,
            "relevant_docs": list(relevant_ids)
        })

print(f"Generated {len(queries)} queries.")

with open('evaluation/queries.json', 'w', encoding='utf-8') as f:
    json.dump(queries, f, indent=2)

session.close()
