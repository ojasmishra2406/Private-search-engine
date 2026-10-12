with open("src/hybrid/fusion.py", "r") as f:
    content = f.read()

# Restore original
content = content.replace("((1.0 - alpha) * (1.0 / (k + rank)))", "(alpha * (1.0 / (k + rank)))")

# Apply correctly to dense only
parts = content.split("for rank, (doc_id, _) in enumerate(dense_results, start=1):")
if len(parts) == 2:
    parts[1] = parts[1].replace("(alpha * (1.0 / (k + rank)))", "((1.0 - alpha) * (1.0 / (k + rank)))", 1)
    content = "for rank, (doc_id, _) in enumerate(dense_results, start=1):".join(parts)

with open("src/hybrid/fusion.py", "w") as f:
    f.write(content)
