import sqlite3
import pickle
import faiss

print("--- SQLITE DIRECT COUNT ---")
conn = sqlite3.connect("data/scale_search2.db")
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM documents")
print(f"COUNT(*): {c.fetchone()[0]}")
conn.close()

print("\n--- FAISS DIRECT COUNT ---")
index = faiss.read_index("data/scale_dense2.index")
print(f"index.ntotal: {index.ntotal}")

print("\n--- LEXICAL DIRECT COUNT ---")
with open("data/scale_lexical2.pkl", "rb") as f:
    lex = pickle.load(f)
print(f"total_docs: {lex.total_docs}")
