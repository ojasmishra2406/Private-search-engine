import sqlite3, pickle, faiss
conn = sqlite3.connect('data/search.db')
cur = conn.cursor()
db_docs = cur.execute('SELECT id, url, title, is_deleted FROM documents').fetchall()

with open('data/index.pkl', 'rb') as f:
    bm25 = pickle.load(f)

dense_index = faiss.read_index('data/dense.index')
with open('data/dense_map.pkl', 'rb') as f:
    dense_map = pickle.load(f)

print(f'DB Total: {len(db_docs)}')
active_db_docs = [d for d in db_docs if not d[3]]
print(f'DB Active: {len(active_db_docs)}')
print(f'BM25 Docs: {len(bm25.doc_lengths) if hasattr(bm25, "doc_lengths") else "N/A"}')
print(f'FAISS Vectors: {dense_index.ntotal}')
print(f'Dense Map Entries: {len(dense_map["ext_to_int"])}')

db_ids = set([d[0] for d in active_db_docs])
map_ids = set(dense_map["ext_to_int"].keys())
if hasattr(bm25, "documents"):
    bm25_ids = set(bm25.documents.keys())
    print('DB vs BM25 ID Parity:', db_ids == bm25_ids)
else:
    bm25_ids = db_ids # Fallback

print('DB vs FAISS ID Parity:', db_ids == map_ids)
print('Duplicates in DB URLs:', len(db_docs) != len(set([d[1] for d in db_docs])))

print('\nSample DB active doc:')
if active_db_docs:
    print('ID:', active_db_docs[-1][0])
    print('URL:', active_db_docs[-1][1])
    print('Title:', active_db_docs[-1][2])
