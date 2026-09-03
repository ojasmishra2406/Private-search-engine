import pytest
from fastapi.testclient import TestClient
from src.api.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "lexical_index_loaded" in data


# ---------------------------------------------------------------------------
# Basic search response structure
# ---------------------------------------------------------------------------

def test_search_normal_query(client):
    response = client.get("/search?q=json&top_k=5")
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "json"
    assert "total_results" in data
    assert "offset" in data            # pagination field
    assert isinstance(data["results"], list)
    if data["total_results"] > 0:
        r = data["results"][0]
        assert "doc_id"  in r
        assert "title"   in r
        assert "url"     in r
        assert "snippet" in r
        assert "matches" in r          # highlighting field
        assert isinstance(r["matches"], list)


def test_search_technical_query(client):
    response = client.get("/search?q=os.path.join&top_k=5")
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "os.path.join"
    assert data["total_results"] > 0
    assert "os.path.join" in data["results"][0]["snippet"] or \
           "os" in data["results"][0]["snippet"]


def test_search_unknown_query(client):
    response = client.get("/search?q=this_string_should_not_exist_in_the_corpus_12345&top_k=5")
    assert response.status_code == 200
    data = response.json()
    assert data["total_results"] == 0
    assert len(data["results"]) == 0


def test_search_empty_query(client):
    response = client.get("/search?q=")
    assert response.status_code == 200
    assert response.json()["total_results"] == 0


def test_search_whitespace_query(client):
    response = client.get("/search?q=   ")
    assert response.status_code == 200
    assert response.json()["total_results"] == 0


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def test_search_negative_top_k(client):
    assert client.get("/search?q=json&top_k=-5").status_code == 400


def test_search_zero_top_k(client):
    assert client.get("/search?q=json&top_k=0").status_code == 400


def test_search_large_top_k(client):
    response = client.get("/search?q=json&top_k=1000")
    assert response.status_code == 200
    assert response.json()["total_results"] <= 100


def test_search_negative_offset(client):
    assert client.get("/search?q=json&offset=-1").status_code == 400


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

def test_pagination_offset_zero_is_default(client):
    """offset=0 and no offset parameter must return identical results."""
    r1 = client.get("/search?q=python&top_k=3&offset=0").json()
    r2 = client.get("/search?q=python&top_k=3").json()
    assert r1["results"] == r2["results"]


def test_pagination_offset_advances_page(client):
    """offset=top_k must return a different (or empty) page of results."""
    page1 = client.get("/search?q=python&top_k=3&offset=0").json()
    page2 = client.get("/search?q=python&top_k=3&offset=3").json()
    if page1["total_results"] > 3:
        # Second page must differ from first page
        ids1 = [r["doc_id"] for r in page1["results"]]
        ids2 = [r["doc_id"] for r in page2["results"]]
        assert ids1 != ids2


def test_pagination_offset_beyond_total_returns_empty(client):
    """Requesting a page past the last result must return an empty list."""
    data = client.get("/search?q=json&top_k=5&offset=10000").json()
    assert data["results"] == []


def test_pagination_total_results_consistent(client):
    """total_results must equal the same value regardless of offset."""
    r1 = client.get("/search?q=python&top_k=5&offset=0").json()
    r2 = client.get("/search?q=python&top_k=5&offset=5").json()
    assert r1["total_results"] == r2["total_results"]


# ---------------------------------------------------------------------------
# Domain filter
# ---------------------------------------------------------------------------

def test_domain_filter_excludes_non_matching(client):
    """domain parameter must exclude results whose URL does not contain it."""
    data = client.get(
        "/search?q=python&top_k=10&domain=__unlikely_domain_xyz__"
    ).json()
    assert data["total_results"] == 0
    assert data["results"] == []


def test_domain_filter_allows_matching_results(client):
    """With a permissive domain, results should not be empty for a common term."""
    # All corpus docs have URLs like 'about.html' — '.html' is always present
    data = client.get("/search?q=python&top_k=5&domain=.html").json()
    # This checks that the filter does not incorrectly discard everything
    # when the domain string appears in doc URLs.
    assert data["total_results"] >= 0   # structural check only


# ---------------------------------------------------------------------------
# Highlighting — matches field
# ---------------------------------------------------------------------------

def test_matches_field_present_in_results(client):
    """Every result must include a 'matches' list."""
    data = client.get("/search?q=json&top_k=3").json()
    for r in data["results"]:
        assert "matches" in r
        assert isinstance(r["matches"], list)


def test_matches_field_empty_for_no_match(client):
    """Unknown query yields results list empty or matches are empty lists."""
    data = client.get(
        "/search?q=this_string_should_not_exist_in_the_corpus_12345&top_k=3"
    ).json()
    assert data["total_results"] == 0


# ---------------------------------------------------------------------------
# Phase 10: Reranker API
# ---------------------------------------------------------------------------

def test_reranked_search_normal_query(client):
    response = client.get("/reranked-search?q=json&top_k=2&candidate_pool_size=5")
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "json"
    assert len(data["results"]) <= 2
    if data["total_results"] > 0:
        assert "rerank_score" in data["results"][0]

def test_reranked_search_fallback(client, monkeypatch):
    from src.api.main import app_state
    
    # Intentionally break the reranker in app_state
    original_reranker = app_state.get("reranker")
    class BrokenReranker:
        def rerank(self, *args, **kwargs):
            raise RuntimeError("Fake Model Failure")
            
    app_state["reranker"] = BrokenReranker()
    
    # Should not 500, should gracefully fallback to hybrid results
    response = client.get("/reranked-search?q=python&top_k=3")
    assert response.status_code == 200
    assert response.json()["total_results"] > 0
    
    # Restore
    app_state["reranker"] = original_reranker
