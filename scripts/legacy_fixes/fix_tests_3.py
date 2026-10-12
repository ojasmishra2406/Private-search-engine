import os
import re

def fix_file(path):
    if not os.path.exists(path): return
    with open(path, "r") as f:
        c = f.read()
    
    # Remove map_path=map_path
    c = re.sub(r',\s*map_path\s*=\s*map_path', '', c)
    # Remove ext_to_int_doc_id entirely
    c = re.sub(r'index\.ext_to_int_doc_id\[[^\]]+\]', r'\g<0>', c) # Wait, it's assert postings[0].doc_id == index.ext_to_int_doc_id[1]
    # We replaced '"doc1"' with '1', so index.ext_to_int_doc_id[1] is just 1.
    c = re.sub(r'index\.ext_to_int_doc_id\[([^\]]+)\]', r'\1', c)
    # also remove string doc_id_str assignment
    c = c.replace('doc_id_str = "hash123"', 'doc_id_str = 123')
    
    with open(path, "w") as f:
        f.write(c)

files = [
    "tests/test_hybrid.py", 
    "tests/test_dense_retrieval.py", 
    "tests/test_incremental_indexing.py",
    "tests/test_index.py",
    "tests/test_metrics.py",
    "tests/test_api.py"
]
for f in files:
    fix_file(f)
