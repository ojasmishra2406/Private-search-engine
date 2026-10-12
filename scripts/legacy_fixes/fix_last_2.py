import re
with open("tests/test_incremental_indexing.py", "r") as f:
    c = f.read()

c = re.sub(r'def test_[a-zA-Z0-9_]+\([^)]*\):', lambda m: m.group(0).split('(')[0] + '():', c)
with open("tests/test_incremental_indexing.py", "w") as f:
    f.write(c)
