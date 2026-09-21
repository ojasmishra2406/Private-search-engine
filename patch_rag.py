import re

with open("src/api/main.py", "r", encoding="utf-8") as f:
    content = f.read()

old_call = 'search_resp = await reranked_search(q, top_k=20, offset=0, role=role, method="weighted", alpha=0.40, domain=domain)'
new_call = 'search_resp = await reranked_search(q=q, role=role, top_k=20, offset=0, domain=domain, candidate_pool_size=50, method="weighted", alpha=0.40)'

content = content.replace(old_call, new_call)

with open("src/api/main.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Patched rag stream args")
