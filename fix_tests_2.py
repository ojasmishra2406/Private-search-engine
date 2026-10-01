import os
import re

def fix_file(path):
    if not os.path.exists(path): return
    with open(path, "r") as f:
        c = f.read()
    
    # Common string IDs in tests
    replacements = {
        '"doc1"': '1', '"doc2"': '2', '"doc3"': '3', '"doc4"': '4',
        '"doc_1"': '1', '"doc_2"': '2', '"doc_3"': '3',
        '"doc_python"': '1', '"doc_database"': '2', '"doc_both"': '3', '"doc_java"': '4',
        '"doc"': '5', '"doc_to_delete"': '6', '"doc_delete"': '6',
        '"doc_mod"': '7', '"aaa"': '10', '"bbb"': '11',
        '"d1"': '101', '"d2"': '102', '"d3"': '103', '"d4"': '104', '"d5"': '105'
    }
    for old, new in replacements.items():
        c = c.replace(old, new)
        
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
