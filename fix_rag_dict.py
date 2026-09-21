with open("src/api/main.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("search_resp.fallback_triggered", "search_resp.get('fallback_triggered', False)")
content = content.replace("search_resp.results", "search_resp.get('results', [])")

with open("src/api/main.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Fixed dict access")
