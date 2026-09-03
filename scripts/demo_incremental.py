import os
import sys
import shutil

sys.path.insert(0, os.path.abspath('.'))
from src.storage.database import Database
from src.storage.models import DBDocument, IndexingStatus
from src.core.indexer import IncrementalIndexer
from src.core.search import LexicalSearch
import pickle

def search_term(q: str):
    with open('demo_index.pkl', 'rb') as f:
        idx = pickle.load(f)
    from src.core.tokenizer import Tokenizer
    engine = LexicalSearch(idx, Tokenizer())
    results = engine.search(q, top_k=5)
    return [r.doc_id for r in results]

print('--- INIT ---')
if os.path.exists('demo_search.db'):
    os.remove('demo_search.db')
if os.path.exists('demo_index.pkl'):
    os.remove('demo_index.pkl')

db = Database('sqlite:///demo_search.db')
db.init_db()
session = db.get_session()
indexer = IncrementalIndexer('demo_index.pkl')

print('\n1. Add a new document -> it becomes searchable')
doc = DBDocument(id='doc1', title='Demo', content='apple banana', url='http://1', content_hash='hash1', indexing_status=IndexingStatus.PENDING.value)
session.add(doc)
session.commit()
indexer.sync(session)
print('Search "apple":', search_term('apple'))

print('\n2. Process the same document again unchanged -> it is skipped')
# simulate ingestion checking hash and doing nothing
stats = indexer.sync(session)
print('Sync stats:', stats)

print('\n3. Modify its content -> old searchable terms disappear and new terms appear')
doc.content = 'cherry date'
doc.content_hash = 'hash2'
doc.version += 1
doc.indexing_status = IndexingStatus.PENDING.value
session.commit()
indexer.sync(session)
print('Search "apple":', search_term('apple'))
print('Search "cherry":', search_term('cherry'))

print('\n4. Delete it -> it no longer appears in search')
doc.is_deleted = True
doc.indexing_status = IndexingStatus.PENDING.value
session.commit()
indexer.sync(session)
print('Search "cherry":', search_term('cherry'))

print('\n5. Repeat the same operation -> behavior is idempotent')
stats = indexer.sync(session)
print('Sync stats:', stats)

print('\n6. Restart/reload the index -> state remains consistent')
indexer_restarted = IncrementalIndexer('demo_index.pkl')
print('Index total docs:', indexer_restarted.index.total_docs)
