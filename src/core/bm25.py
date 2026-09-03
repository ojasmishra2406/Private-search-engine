"""
BM25 scoring implementation.

Uses the Okapi BM25 formula:
    score(D, Q) = Σ IDF(qi) * [tf(qi,D) * (k1+1)] / [tf(qi,D) + k1 * (1 - b + b * |D|/avgdl)]

where:
    IDF(qi) = ln(1 + (N - df(qi) + 0.5) / (df(qi) + 0.5))

Default parameters: k1=1.5, b=0.75
"""

import math
from typing import List, Dict, Tuple
from .index import InvertedIndex


class BM25Scorer:
    def __init__(self, index: InvertedIndex, k1: float = 1.5, b: float = 0.75):
        self.index = index
        self.k1 = k1
        self.b = b

    def idf(self, df: int) -> float:
        """Inverse document frequency for a term with document frequency df."""
        n = self.index.total_docs
        return math.log(1.0 + (n - df + 0.5) / (df + 0.5))

    def term_score(self, tf: int, doc_length: int, df: int) -> float:
        """BM25 score contribution of a single term in a single document."""
        avgdl = self.index.get_average_document_length()
        if avgdl == 0.0:
            return 0.0

        idf_value = self.idf(df)
        tf_component = (tf * (self.k1 + 1.0)) / (
            tf + self.k1 * (1.0 - self.b + self.b * doc_length / avgdl)
        )
        return idf_value * tf_component

    def score_document(self, doc_id: int, query_term_ids: List[int]) -> float:
        """
        Total BM25 score for a document against a set of unique query term IDs.
        """
        doc_length = self.index.doc_lengths.get(doc_id, 0)
        total = 0.0

        for tid in query_term_ids:
            posting_list = self.index.postings.get(tid, [])
            df = len(posting_list)
            if df == 0:
                continue

            # Find this document's posting in the list
            tf = 0
            for posting in posting_list:
                if posting.doc_id == doc_id:
                    tf = posting.term_freq
                    break

            if tf > 0:
                total += self.term_score(tf, doc_length, df)

        return total

    def score_document_fast(self, doc_id: int, query_term_ids: List[int], term_postings: dict, phrase_term_ids: List[List[int]] = None) -> float:
        """
        Optimized BM25 scorer that uses pre-computed postings dict.
        Also applies phrase boosts if phrase terms are adjacent.
        """
        doc_length = self.index.doc_lengths.get(doc_id, 0)
        if doc_length == 0:
            return 0.0
            
        total = 0.0

        for tid in query_term_ids:
            postings_dict = term_postings.get(tid)
            if not postings_dict:
                continue
            posting = postings_dict.get(doc_id)
            if posting:
                df = len(self.index.postings.get(tid, []))
                total += self.term_score(posting.term_freq, doc_length, df)
                
        # Phrase boost
        if phrase_term_ids:
            for phrase in phrase_term_ids:
                # Check if all terms exist in doc
                if not all(term_postings.get(t, {}).get(doc_id) for t in phrase):
                    continue
                
                # Check proximity
                # Start with positions of the first term
                valid_positions = term_postings[phrase[0]][doc_id].positions
                
                for i in range(1, len(phrase)):
                    next_tid = phrase[i]
                    next_positions = term_postings[next_tid][doc_id].positions
                    # Find sequences
                    new_valid = []
                    for pos in valid_positions:
                        if (pos + 1) in next_positions:
                            new_valid.append(pos + 1)
                    valid_positions = new_valid
                    if not valid_positions:
                        break
                        
                if valid_positions:
                    # Found exact phrase! Boost the total score significantly.
                    # We can boost by simulating an extra occurrence of all phrase terms, or a flat multiplier.
                    # A multiplier of 2.0 or adding 5.0 flat score. Flat boost based on phrase length is robust.
                    total += 5.0 * len(phrase)

        return total
