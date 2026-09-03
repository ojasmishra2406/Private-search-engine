import json
from dataclasses import dataclass
from typing import List

@dataclass
class EvalQuery:
    query: str
    relevant_docs: List[str]

class EvaluationDataset:
    def __init__(self, queries: List[EvalQuery]):
        self.queries = queries

    @classmethod
    def load_from_json(cls, path: str):
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        queries = [EvalQuery(q["query"], q["relevant_docs"]) for q in data]
        return cls(queries)
