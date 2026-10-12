import os
import re

def fix_test_search():
    with open("tests/test_search.py", "r") as f:
        content = f.read()
    
    # Replace doc_python with 1, doc_database with 2, doc_both with 3, doc_java with 4
    content = content.replace('"doc_python"', '1')
    content = content.replace('"doc_database"', '2')
    content = content.replace('"doc_both"', '3')
    content = content.replace('"doc_java"', '4')
    content = content.replace('"aaa"', '10')
    content = content.replace('"bbb"', '11')
    
    with open("tests/test_search.py", "w") as f:
        f.write(content)

fix_test_search()
