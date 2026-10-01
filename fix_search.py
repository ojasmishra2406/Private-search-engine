import os

with open("src/core/search.py", "r") as f:
    c = f.read()

c = c.replace('scored.append((score, -doc_id, doc_id))', 'scored.append((score, -doc_id if isinstance(doc_id, int) else -hash(doc_id), doc_id))')

with open("src/core/search.py", "w") as f:
    f.write(c)
