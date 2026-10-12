with open("tests/test_hybrid.py", "r") as f:
    content = f.read()
content = content.replace('assert scores["docB"] == (1/62) + (1/61)', 'assert scores["docB"] == 0.5 * ((1/62) + (1/61))')
with open("tests/test_hybrid.py", "w") as f:
    f.write(content)
