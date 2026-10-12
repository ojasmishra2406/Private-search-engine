import os

with open("src/dense/vector_index.py", "r", encoding="utf-8") as f:
    c = f.read()

c = c.replace('ids_array = np.array(int_ids, dtype=np.int64)', 'ids_array = np.array([i if isinstance(i, int) else hash(i) for i in int_ids], dtype=np.int64)')

with open("src/dense/vector_index.py", "w", encoding="utf-8") as f:
    f.write(c)
