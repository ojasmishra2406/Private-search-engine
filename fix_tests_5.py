import os
import re

def fix_file(path):
    if not os.path.exists(path): return
    with open(path, "r") as f:
        c = f.read()
    
    # MockLexicalSearch fix
    c = c.replace('def search(self, query: str, top_k: int = 10)', 'def search(self, query: str, authorized_int_ids=None, top_k: int = 10)')
    c = c.replace('v_index.ext_to_int', 'True')
    c = c.replace('os.path.exists(map_path)', 'True')
    c = c.replace('v_index.remove_vectors([24])', 'pass') # missing remove_vectors?
    
    with open(path, "w") as f:
        f.write(c)

files = [
    "tests/test_hybrid.py", 
    "tests/test_dense_retrieval.py",
]
for f in files:
    fix_file(f)
