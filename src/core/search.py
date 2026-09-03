"""
Lexical search pipeline.

Query flow:
    raw query string
        → Tokenizer (same as indexing)
        → term dictionary lookup
        → candidate doc IDs (union of posting lists)
        → BM25 scoring per candidate
        → top-K selection
        → SearchResult list (sorted by descending score, ties broken by ascending doc_id)
"""

import heapq
from dataclasses import dataclass
from typing import List, Optional, Dict
from .tokenizer import Tokenizer
from .index import InvertedIndex, Posting
from .bm25 import BM25Scorer


@dataclass
class SearchResult:
    doc_id: str  # external document ID
    score: float


class LexicalSearch:
    def __init__(self, index: InvertedIndex, tokenizer: Tokenizer,
                 k1: float = 1.5, b: float = 0.75):
        self.index = index
        self.tokenizer = tokenizer
        self.scorer = BM25Scorer(index, k1=k1, b=b)

    def search(self, query: str, top_k: int = 10) -> List[SearchResult]:
        """
        Execute a lexical BM25 search.

        Returns up to top_k results sorted by descending BM25 score.
        Ties are broken by ascending internal doc_id for determinism.
        """
        if top_k <= 0:
            return []

        # Tokenize query using the same tokenizer as indexing
        query_tokens = self.tokenizer.tokenize(query)
        if not query_tokens:
            return []

        # Deduplicate query terms so repeated terms don't inflate scores
        unique_terms = list(dict.fromkeys(query_tokens))

        # Map query terms to term IDs, skip unknown terms
        query_term_ids: List[int] = []
        for term in unique_terms:
            tid = self.index.term_to_id.get(term)
            if tid is not None:
                query_term_ids.append(tid)

        if not query_term_ids:
            return []

        # Gather candidate documents and their postings
        term_postings: Dict[int, Dict[int, Posting]] = {}
        candidate_doc_ids: set = set()
        for tid in query_term_ids:
            postings_dict = {p.doc_id: p for p in self.index.postings.get(tid, [])}
            term_postings[tid] = postings_dict
            candidate_doc_ids.update(postings_dict.keys())

        if not candidate_doc_ids:
            return []

        # Find phrases
        import re
        raw_phrases = re.findall(r'"([^"]+)"', query)
        phrase_term_ids: List[List[int]] = []
        for p in raw_phrases:
            p_tokens = self.tokenizer.tokenize(p)
            p_tids = [self.index.term_to_id.get(t) for t in p_tokens if self.index.term_to_id.get(t) is not None]
            if len(p_tids) > 1:
                phrase_term_ids.append(p_tids)

        # Score each candidate
        scored: List[tuple] = []
        for doc_id in candidate_doc_ids:
            score = self.scorer.score_document_fast(doc_id, query_term_ids, term_postings, phrase_term_ids)
            # Heap key: (score, -doc_id) - min-heap on score, max-heap on -doc_id
            scored.append((score, -doc_id, doc_id))

        # Top-K via nlargest (correct and clear for V1 corpus sizes)
        top = heapq.nlargest(top_k, scored, key=lambda x: (x[0], x[1]))

        results: List[SearchResult] = []
        for score, _neg_id, doc_id in top:
            ext_id = self.index.int_to_ext_doc_id[doc_id]
            results.append(SearchResult(doc_id=ext_id, score=score))

        return results
