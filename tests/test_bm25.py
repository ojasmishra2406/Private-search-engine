"""
BM25 scorer unit tests.

Tests verify the exact BM25 formula:
    IDF(q)  = ln(1 + (N - df + 0.5) / (df + 0.5))
    score   = Σ IDF(qi) * [tf * (k1+1)] / [tf + k1 * (1 - b + b * |D|/avgdl)]

with k1=1.5, b=0.75.
"""

import math
import pytest
from src.core.index import InvertedIndex
from src.core.bm25 import BM25Scorer


def _build_index(*doc_token_lists):
    """Helper: build an index from (ext_id, tokens) pairs."""
    index = InvertedIndex()
    for i, tokens in enumerate(doc_token_lists):
        index.add_document(f"doc{i}", tokens)
    return index


# ── Test 1: IDF calculation ─────────────────────────────────────────────────

class TestIDF:
    def test_idf_known_values(self):
        """Verify IDF against hand-calculated values."""
        # 3 docs, term appears in 1 → IDF = ln(1 + (3-1+0.5)/(1+0.5)) = ln(1 + 5/3)
        index = _build_index(["a"], ["b"], ["c"])
        scorer = BM25Scorer(index)
        expected = math.log(1.0 + (3 - 1 + 0.5) / (1 + 0.5))  # ln(1 + 5/3)
        assert scorer.idf(df=1) == pytest.approx(expected)

    def test_idf_all_docs_contain_term(self):
        """When every document contains the term, IDF should be low but positive."""
        index = _build_index(["a"], ["a"], ["a"])
        scorer = BM25Scorer(index)
        expected = math.log(1.0 + (3 - 3 + 0.5) / (3 + 0.5))  # ln(1 + 0.5/3.5)
        assert scorer.idf(df=3) == pytest.approx(expected)
        assert scorer.idf(df=3) > 0

    def test_idf_rare_term_higher_than_common(self):
        index = _build_index(["a"], ["b"], ["c"], ["d"], ["e"])
        scorer = BM25Scorer(index)
        assert scorer.idf(df=1) > scorer.idf(df=4)


# ── Test 2: TF saturation ───────────────────────────────────────────────────

class TestTFSaturation:
    def test_increasing_tf_increases_score_with_diminishing_returns(self):
        """Higher tf should yield higher score, but the marginal gain shrinks."""
        index = _build_index(["x"] * 10)  # 1 doc, length 10
        scorer = BM25Scorer(index)
        # avgdl = 10, doc_length = 10, df = 1 for all calls
        s1 = scorer.term_score(tf=1, doc_length=10, df=1)
        s2 = scorer.term_score(tf=2, doc_length=10, df=1)
        s5 = scorer.term_score(tf=5, doc_length=10, df=1)
        s10 = scorer.term_score(tf=10, doc_length=10, df=1)

        assert s2 > s1
        assert s5 > s2
        assert s10 > s5

        # Diminishing returns: gap shrinks
        gap_1_to_2 = s2 - s1
        gap_5_to_10 = s10 - s5
        assert gap_1_to_2 > gap_5_to_10


# ── Test 3: Document length normalization ────────────────────────────────────

class TestDocLengthNormalization:
    def test_shorter_doc_scores_higher_for_same_tf(self):
        """Given equal tf and df, a shorter document should score higher."""
        # Two docs, both contain "python" once, but different lengths
        index = _build_index(
            ["python", "is", "great"],        # doc0: length 3
            ["python"] + ["filler"] * 19,     # doc1: length 20
        )
        scorer = BM25Scorer(index)
        avgdl = index.get_average_document_length()  # (3+20)/2 = 11.5

        python_tid = index.term_to_id["python"]
        df = len(index.postings[python_tid])  # 2

        s_short = scorer.term_score(tf=1, doc_length=3, df=df)
        s_long = scorer.term_score(tf=1, doc_length=20, df=df)

        assert s_short > s_long


# ── Test 4: Multi-term query scoring ─────────────────────────────────────────

class TestMultiTermQuery:
    def test_multi_term_scores_are_summed(self):
        """Score for multi-term query equals sum of individual term scores."""
        index = _build_index(
            ["python", "database", "tutorial"],  # doc0
        )
        scorer = BM25Scorer(index)

        python_tid = index.term_to_id["python"]
        database_tid = index.term_to_id["database"]

        score_both = scorer.score_document(0, [python_tid, database_tid])
        score_python = scorer.score_document(0, [python_tid])
        score_database = scorer.score_document(0, [database_tid])

        assert score_both == pytest.approx(score_python + score_database)


# ── Test 5: Unknown term contributes nothing ─────────────────────────────────

class TestUnknownTerm:
    def test_unknown_term_id_scores_zero(self):
        index = _build_index(["hello", "world"])
        scorer = BM25Scorer(index)
        # term_id 9999 doesn't exist
        assert scorer.score_document(0, [9999]) == 0.0

    def test_score_with_mix_of_known_and_unknown(self):
        index = _build_index(["hello", "world"])
        scorer = BM25Scorer(index)
        hello_tid = index.term_to_id["hello"]
        score_known = scorer.score_document(0, [hello_tid])
        score_mixed = scorer.score_document(0, [hello_tid, 9999])
        assert score_mixed == pytest.approx(score_known)


# ── Test 6: Exact numerical BM25 score ──────────────────────────────────────

class TestExactNumericalScore:
    def test_hand_calculated_bm25(self):
        """
        Manually calculate BM25 for a controlled corpus and verify.

        Corpus:
            doc0: ["the", "cat", "sat"]           length=3
            doc1: ["the", "cat", "sat", "on", "the", "mat"]  length=6

        Query term: "cat"
            N=2, df=2, avgdl=(3+6)/2=4.5

        For doc0 (|D|=3, tf=1):
            IDF = ln(1 + (2-2+0.5)/(2+0.5)) = ln(1 + 0.5/2.5) = ln(1.2)
            tf_comp = (1*2.5) / (1 + 1.5*(1 - 0.75 + 0.75*3/4.5))
                    = 2.5 / (1 + 1.5*(1 - 0.75 + 0.5))
                    = 2.5 / (1 + 1.5*0.75)
                    = 2.5 / (1 + 1.125)
                    = 2.5 / 2.125
            score = ln(1.2) * 2.5/2.125

        For doc1 (|D|=6, tf=1):
            tf_comp = 2.5 / (1 + 1.5*(1 - 0.75 + 0.75*6/4.5))
                    = 2.5 / (1 + 1.5*(1 - 0.75 + 1.0))
                    = 2.5 / (1 + 1.5*1.25)
                    = 2.5 / (1 + 1.875)
                    = 2.5 / 2.875
            score = ln(1.2) * 2.5/2.875
        """
        index = _build_index(
            ["the", "cat", "sat"],
            ["the", "cat", "sat", "on", "the", "mat"],
        )
        scorer = BM25Scorer(index, k1=1.5, b=0.75)
        cat_tid = index.term_to_id["cat"]

        idf_val = math.log(1.0 + (2 - 2 + 0.5) / (2 + 0.5))  # ln(1.2)

        expected_doc0 = idf_val * 2.5 / 2.125
        expected_doc1 = idf_val * 2.5 / 2.875

        actual_doc0 = scorer.score_document(0, [cat_tid])
        actual_doc1 = scorer.score_document(1, [cat_tid])

        assert actual_doc0 == pytest.approx(expected_doc0)
        assert actual_doc1 == pytest.approx(expected_doc1)

        # Shorter doc should score higher
        assert actual_doc0 > actual_doc1


# ── Test 7: Empty index ─────────────────────────────────────────────────────

class TestEmptyIndex:
    def test_score_on_empty_index(self):
        index = InvertedIndex()
        scorer = BM25Scorer(index)
        assert scorer.score_document(0, [0]) == 0.0

    def test_idf_on_empty_index(self):
        index = InvertedIndex()
        scorer = BM25Scorer(index)
        # N=0, df=0 → ln(1 + (0-0+0.5)/(0+0.5)) = ln(2)
        assert scorer.idf(df=0) == pytest.approx(math.log(2.0))
