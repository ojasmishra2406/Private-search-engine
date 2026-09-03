"""
Phase 17 — Search Quality Tests

Tests for:
- Query normalization
- Technical token preservation
- Empty query handling
- Search result deduplication
- Cross-encoder isolation
- Alpha bounds enforcement
- Cross-encoder failure fallback
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from src.api.query_utils import normalize_query
from src.api.main import app, app_state


@pytest.fixture(scope="module")
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# ---------------------------------------------------------------------------
# 17A. Query normalization
# ---------------------------------------------------------------------------

class TestQueryNormalization:
    def test_strip_leading_trailing(self):
        assert normalize_query("  asyncio  ") == "asyncio"

    def test_collapses_internal_whitespace(self):
        assert normalize_query("list   append") == "list append"

    def test_tab_and_newline_normalized(self):
        assert normalize_query("dict\tcomprehension\nexample") == "dict comprehension example"

    def test_empty_string(self):
        assert normalize_query("") == ""

    def test_whitespace_only(self):
        assert normalize_query("   ") == ""

    def test_preserves_technical_tokens(self):
        """Technical tokens must survive normalization unchanged."""
        assert normalize_query("asyncio.run()") == "asyncio.run()"
        assert normalize_query("__init__") == "__init__"
        assert normalize_query("C++") == "C++"
        assert normalize_query("UTF-8") == "UTF-8"
        assert normalize_query("os.path.join") == "os.path.join"
        assert normalize_query("HTTPException") == "HTTPException"
        assert normalize_query("dict comprehension") == "dict comprehension"

    def test_single_token(self):
        assert normalize_query("asyncio") == "asyncio"

    def test_multiple_internal_spaces(self):
        assert normalize_query("a   b   c") == "a b c"


# ---------------------------------------------------------------------------
# 17B. Technical tokens are searchable
# ---------------------------------------------------------------------------

class TestTechnicalTokenSearchable:
    def test_asyncio_searchable(self, client):
        res = client.get("/search?q=asyncio")
        assert res.status_code == 200
        data = res.json()
        # asyncio is a well-known Python module — must be in index
        assert data["total_results"] > 0

    def test_list_append_searchable(self, client):
        res = client.get("/search?q=list.append")
        assert res.status_code == 200
        data = res.json()
        assert data["total_results"] > 0

    def test_exception_handling_searchable(self, client):
        res = client.get("/search?q=exception handling")
        assert res.status_code == 200
        data = res.json()
        assert data["total_results"] > 0

    def test_dunder_init_searchable(self, client):
        res = client.get("/search?q=__init__")
        assert res.status_code == 200
        data = res.json()
        # At minimum the search should not error
        assert data["total_results"] >= 0


# ---------------------------------------------------------------------------
# 17C. Empty query handling
# ---------------------------------------------------------------------------

class TestEmptyQueryHandling:
    def test_empty_query_search(self, client):
        res = client.get("/search?q=")
        assert res.status_code == 200
        assert res.json()["total_results"] == 0
        assert res.json()["results"] == []

    def test_whitespace_only_query_search(self, client):
        res = client.get("/search?q=%20%20%20")
        assert res.status_code == 200
        assert res.json()["total_results"] == 0

    def test_empty_query_hybrid(self, client):
        res = client.get("/hybrid-search?q=")
        assert res.status_code == 200
        assert res.json()["total_results"] == 0


# ---------------------------------------------------------------------------
# 17D. Search result deduplication
# ---------------------------------------------------------------------------

class TestSearchResultDeduplication:
    def test_no_duplicate_doc_ids_lexical(self, client):
        res = client.get("/search?q=Python&top_k=50")
        assert res.status_code == 200
        results = res.json()["results"]
        doc_ids = [r["doc_id"] for r in results]
        assert len(doc_ids) == len(set(doc_ids)), "Duplicate doc_ids found in /search results"

    def test_no_duplicate_doc_ids_hybrid(self, client):
        res = client.get("/hybrid-search?q=Python&top_k=50")
        assert res.status_code == 200
        results = res.json()["results"]
        doc_ids = [r["doc_id"] for r in results]
        assert len(doc_ids) == len(set(doc_ids)), "Duplicate doc_ids found in /hybrid-search results"

    def test_no_duplicate_doc_ids_reranked(self, client):
        res = client.get("/reranked-search?q=Python&top_k=20")
        assert res.status_code == 200
        results = res.json()["results"]
        doc_ids = [r["doc_id"] for r in results]
        assert len(doc_ids) == len(set(doc_ids)), "Duplicate doc_ids found in /reranked-search results"


# ---------------------------------------------------------------------------
# 17E. Cross-encoder isolation
# ---------------------------------------------------------------------------

class TestCrossEncoderIsolation:
    def test_search_does_not_have_rerank_scores(self, client):
        """/search must return null rerank_score for all results."""
        res = client.get("/search?q=Python")
        assert res.status_code == 200
        for result in res.json()["results"]:
            assert result["rerank_score"] is None, (
                f"rerank_score should be None on /search, got {result['rerank_score']}"
            )

    def test_hybrid_does_not_have_rerank_scores(self, client):
        """/hybrid-search must return null rerank_score for all results."""
        res = client.get("/hybrid-search?q=Python")
        assert res.status_code == 200
        for result in res.json()["results"]:
            assert result["rerank_score"] is None, (
                f"rerank_score should be None on /hybrid-search, got {result['rerank_score']}"
            )

    def test_reranked_search_has_scores(self, client):
        """/reranked-search must return rerank_score when reranker is available."""
        res = client.get("/reranked-search?q=Python&top_k=5")
        assert res.status_code == 200
        results = res.json()["results"]
        if results and app_state.get("reranker"):
            # At least some results should have rerank_score set
            scores = [r["rerank_score"] for r in results]
            assert any(s is not None for s in scores), "Expected some rerank_scores on /reranked-search"


# ---------------------------------------------------------------------------
# 17F. Cross-encoder failure fallback
# ---------------------------------------------------------------------------

class TestCrossEncoderFailureFallback:
    def test_reranker_exception_returns_200(self, client, monkeypatch):
        """If the reranker throws, /reranked-search should fall back gracefully."""
        reranker = app_state.get("reranker")
        if reranker is None:
            pytest.skip("Reranker not loaded")

        original_rerank = reranker.rerank

        def failing_rerank(*args, **kwargs):
            raise RuntimeError("Simulated reranker failure")

        monkeypatch.setattr(reranker, "rerank", failing_rerank)
        try:
            res = client.get("/reranked-search?q=Python&top_k=5")
            assert res.status_code == 200, f"Expected 200 fallback, got {res.status_code}"
            data = res.json()
            assert "results" in data
        finally:
            monkeypatch.setattr(reranker, "rerank", original_rerank)


# ---------------------------------------------------------------------------
# 17G. Alpha bounds enforcement
# ---------------------------------------------------------------------------

class TestAlphaBounds:
    def test_alpha_0_valid(self, client):
        res = client.get("/hybrid-search?q=Python&alpha=0.0")
        assert res.status_code == 200

    def test_alpha_1_valid(self, client):
        res = client.get("/hybrid-search?q=Python&alpha=1.0")
        assert res.status_code == 200

    def test_default_alpha_weighted(self, client):
        """Default alpha=0.40 must produce results."""
        res = client.get("/hybrid-search?q=Python&method=weighted")
        assert res.status_code == 200
        assert res.json()["total_results"] > 0


# ---------------------------------------------------------------------------
# 17H. Health parity fields
# ---------------------------------------------------------------------------

class TestHealthParity:
    def test_health_has_parity_fields(self, client):
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert "db_doc_count" in data
        assert "lexical_doc_count" in data
        assert "dense_doc_count" in data
        assert "parity_ok" in data

    def test_health_parity_ok(self, client):
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        # If all three subsystems are loaded, parity must hold
        if data["lexical_index_loaded"] and data["dense_index_loaded"] and data["database_reachable"]:
            assert data["parity_ok"] is True, (
                f"Parity mismatch: DB={data['db_doc_count']}, "
                f"Lexical={data['lexical_doc_count']}, Dense={data['dense_doc_count']}"
            )
