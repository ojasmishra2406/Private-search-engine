from datasets import load_dataset
from collections import Counter
qrels = load_dataset('BeIR/scifact-qrels', split='test')
counts = Counter([q['query-id'] for q in qrels if q['score'] > 0])
avg = sum(counts.values()) / len(counts)
print(f'Average rel docs per query: {avg:.2f}')
print(f'Max rel docs for a query: {max(counts.values())}')
