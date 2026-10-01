with open("tests/test_hybrid.py", "r") as f:
    c = f.read()

c = c.replace('def search(self, query: str, top_k: int = 10)', 'def search(self, query: str, authorized_int_ids=None, top_k: int = 10)')

with open("tests/test_hybrid.py", "w") as f:
    f.write(c)
