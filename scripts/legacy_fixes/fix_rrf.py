with open("src/hybrid/fusion.py", "r") as f:
    content = f.read()

content = content.replace("k: int = 60\n) -> List[Tuple[str, float]]:", "k: int = 60,\n    alpha: float = 0.5\n) -> List[Tuple[str, float]]:")

old_for_bm25 = """    for rank, (doc_id, _) in enumerate(bm25_results, start=1):
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (k + rank))
        
    for rank, (doc_id, _) in enumerate(dense_results, start=1):
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (k + rank))"""

new_for_bm25 = """    for rank, (doc_id, _) in enumerate(bm25_results, start=1):
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (alpha * (1.0 / (k + rank)))
        
    for rank, (doc_id, _) in enumerate(dense_results, start=1):
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + ((1.0 - alpha) * (1.0 / (k + rank)))"""

content = content.replace(old_for_bm25, new_for_bm25)

with open("src/hybrid/fusion.py", "w") as f:
    f.write(content)
print("done")
