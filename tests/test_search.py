"""
Lexical search pipeline tests.

Covers:
    single-term query, multi-term query, unknown term, mixed known+unknown,
    empty query, whitespace query, top_k=0, top_k > candidates,
    multiple matching documents, deterministic tie ordering, repeated query terms,
    case-insensitive query normalization, empty index.
"""

import math
import pytest
from src.core.tokenizer import Tokenizer
from src.core.index import InvertedIndex
from src.core.search import LexicalSearch, SearchResult


@pytest.fixture
def search_env():
    """Build a small corpus for query pipeline tests."""
    tokenizer = Tokenizer()
    index = InvertedIndex()

    docs = {
        "doc_python": "Python is a programming language",
        "doc_database": "Database systems store and retrieve data",
        "doc_both": "Python can connect to a database using libraries",
        "doc_java": "Java is another programming language",
    }
    for ext_id, text in docs.items():
        tokens = tokenizer.tokenize(text)
        index.add_document(ext_id, tokens)

    engine = LexicalSearch(index, tokenizer)
    return engine, index


# ── Single-term query ────────────────────────────────────────────────────────

class TestSingleTermQuery:
    def test_single_term_returns_matching_docs(self, search_env):
        engine, _ = search_env
        results = engine.search("python")
        ext_ids = [r.doc_id for r in results]
        assert "doc_python" in ext_ids
        assert "doc_both" in ext_ids
        assert "doc_java" not in ext_ids

    def test_all_scores_positive(self, search_env):
        engine, _ = search_env
        results = engine.search("python")
        for r in results:
            assert r.score > 0


# ── Multi-term query ─────────────────────────────────────────────────────────

class TestMultiTermQuery:
    def test_multi_term_returns_union(self, search_env):
        engine, _ = search_env
        results = engine.search("python database")
        ext_ids = [r.doc_id for r in results]
        assert "doc_python" in ext_ids
        assert "doc_database" in ext_ids
        assert "doc_both" in ext_ids

    def test_doc_matching_both_terms_scores_highest(self, search_env):
        engine, _ = search_env
        results = engine.search("python database")
        # doc_both contains both terms, so it should score highest
        assert results[0].doc_id == "doc_both"


# ── Unknown term ─────────────────────────────────────────────────────────────

class TestUnknownTerm:
    def test_completely_unknown_returns_empty(self, search_env):
        engine, _ = search_env
        results = engine.search("xyznonexistent")
        assert results == []

    def test_mixed_known_unknown_returns_known_matches(self, search_env):
        engine, _ = search_env
        results = engine.search("python xyznonexistent")
        ext_ids = [r.doc_id for r in results]
        assert "doc_python" in ext_ids
        assert "doc_both" in ext_ids


# ── Empty and whitespace queries ─────────────────────────────────────────────

class TestEmptyQueries:
    def test_empty_query(self, search_env):
        engine, _ = search_env
        assert engine.search("") == []

    def test_whitespace_query(self, search_env):
        engine, _ = search_env
        assert engine.search("     ") == []

    def test_punctuation_only_query(self, search_env):
        engine, _ = search_env
        assert engine.search("!!!???") == []


# ── top_k edge cases ────────────────────────────────────────────────────────

class TestTopK:
    def test_top_k_zero(self, search_env):
        engine, _ = search_env
        assert engine.search("python", top_k=0) == []

    def test_top_k_larger_than_candidates(self, search_env):
        engine, _ = search_env
        results = engine.search("python", top_k=100)
        # Only 2 docs contain "python"
        assert len(results) == 2

    def test_top_k_limits_results(self, search_env):
        engine, _ = search_env
        results = engine.search("programming language", top_k=1)
        assert len(results) == 1


# ── Deterministic ordering ───────────────────────────────────────────────────

class TestDeterministicOrdering:
    def test_descending_score_order(self, search_env):
        engine, _ = search_env
        results = engine.search("python database")
        for i in range(len(results) - 1):
            assert results[i].score >= results[i + 1].score

    def test_same_query_same_results(self, search_env):
        engine, _ = search_env
        r1 = engine.search("python")
        r2 = engine.search("python")
        assert [(r.doc_id, r.score) for r in r1] == [(r.doc_id, r.score) for r in r2]

    def test_tie_broken_by_doc_id(self):
        """Two docs with identical content should tie on score; lower internal doc_id first."""
        tokenizer = Tokenizer()
        index = InvertedIndex()
        index.add_document("aaa", tokenizer.tokenize("identical content"))
        index.add_document("bbb", tokenizer.tokenize("identical content"))
        engine = LexicalSearch(index, tokenizer)

        results = engine.search("identical content")
        assert len(results) == 2
        assert results[0].score == pytest.approx(results[1].score)
        # aaa gets internal id 0, bbb gets 1 → aaa first (ascending doc_id)
        assert results[0].doc_id == "aaa"
        assert results[1].doc_id == "bbb"


# ── Repeated query terms ────────────────────────────────────────────────────

class TestRepeatedQueryTerms:
    def test_repeated_term_does_not_inflate_score(self, search_env):
        engine, _ = search_env
        r_single = engine.search("python")
        r_repeated = engine.search("python python python")

        assert len(r_single) == len(r_repeated)
        for a, b in zip(r_single, r_repeated):
            assert a.doc_id == b.doc_id
            assert a.score == pytest.approx(b.score)


# ── Case-insensitive normalization consistency ───────────────────────────────

class TestNormalizationConsistency:
    def test_uppercase_query_matches_lowercase_index(self, search_env):
        engine, _ = search_env
        r_lower = engine.search("python")
        r_upper = engine.search("PYTHON")
        r_mixed = engine.search("Python")

        ids_lower = [r.doc_id for r in r_lower]
        ids_upper = [r.doc_id for r in r_upper]
        ids_mixed = [r.doc_id for r in r_mixed]

        assert ids_lower == ids_upper == ids_mixed


# ── Empty index ──────────────────────────────────────────────────────────────

class TestEmptyIndex:
    def test_search_empty_index_returns_empty(self):
        tokenizer = Tokenizer()
        index = InvertedIndex()
        engine = LexicalSearch(index, tokenizer)
        assert engine.search("python") == []

    def test_search_empty_index_does_not_crash(self):
        tokenizer = Tokenizer()
        index = InvertedIndex()
        engine = LexicalSearch(index, tokenizer)
        # Should not raise any exception
        engine.search("")
        engine.search("   ")
        engine.search("unknown term")
