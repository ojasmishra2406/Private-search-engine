with open("src/api/main.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("search_resp = await reranked_search(", "search_resp = reranked_search(")

with open("src/api/main.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Removed await")
