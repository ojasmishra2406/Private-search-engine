import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from src.api.main import app
from src.core.tokenizer import Tokenizer
from src.api.query_utils import normalize_query

@pytest.fixture(scope="module")
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

def test_query_normalization():
    # Technical token preservation
    assert normalize_query("  asyncio.run()  ") == "asyncio.run()"
    assert normalize_query("C++   and __init__") == "C++ and __init__"
    assert normalize_query("   ") == ""
    assert normalize_query("") == ""

def test_technical_tokens():
    tok = Tokenizer()
    assert "asyncio.run" in tok.tokenize("asyncio.run()")
    assert "__init__" in tok.tokenize("__init__")
    assert "c++" in tok.tokenize("C++")
    assert "os.path" in tok.tokenize("os.path")

def test_empty_query_boundary(client):
    res = client.get("/search?q=   ")
    assert res.status_code == 200
    assert res.json()["results"] == []
    
    res2 = client.get("/search?q=")
    assert res2.status_code == 200
    assert res2.json()["results"] == []

def test_phrase_handling(client):
    res = client.get('/search?q="http response"')
    assert res.status_code == 200
    # Assuming the API works and phrase scores are boosted
    assert isinstance(res.json()["results"], list)

def test_duplicate_result_prevention(client):
    res = client.get("/search?q=python")
    assert res.status_code == 200
    urls = [r["url"] for r in res.json()["results"]]
    assert len(urls) == len(set(urls)), "Duplicate URLs found in results!"
    
    res2 = client.get("/hybrid-search?q=python")
    assert res2.status_code == 200
    urls2 = [r["url"] for r in res2.json()["results"]]
    assert len(urls2) == len(set(urls2)), "Duplicate URLs in hybrid search!"

def test_hybrid_ranking(client):
    res_rrf = client.get("/hybrid-search?q=python&method=rrf")
    assert res_rrf.status_code == 200
    
    res_weighted = client.get("/hybrid-search?q=python&method=weighted&alpha=0.5")
    assert res_weighted.status_code == 200

def test_cross_encoder_isolation(client):
    # Only reranked-search should return a populated rerank_score
    res = client.get("/search?q=python")
    assert res.json()["results"][0].get("rerank_score") is None

    res2 = client.get("/dense-search?q=python")
    assert res2.json()["results"][0].get("rerank_score") is None

    res3 = client.get("/hybrid-search?q=python")
    assert res3.json()["results"][0].get("rerank_score") is None
    
    res4 = client.get("/reranked-search?q=python")
    assert res4.json()["results"][0].get("rerank_score") is not None

def test_cross_encoder_failure_fallback(client):
    # Simulate a crash inside the reranker
    with patch("src.reranker.reranker.CrossEncoderReranker.rerank") as mock_rerank:
        mock_rerank.side_effect = Exception("Model failed!")
        
        res = client.get("/reranked-search?q=python")
        assert res.status_code == 200, "API should not crash on reranker failure"
        assert res.json()["results"][0].get("rerank_score") is None, "Fallback should not have rerank score"

def test_pagination(client):
    res1 = client.get("/search?q=python&top_k=2&offset=0")
    res2 = client.get("/search?q=python&top_k=2&offset=2")
    assert res1.status_code == 200
    assert res2.status_code == 200
    
    r1 = res1.json()["results"]
    r2 = res2.json()["results"]
    
    if len(r1) == 2 and len(r2) == 2:
        assert r1[0]["doc_id"] != r2[0]["doc_id"], "Pagination overlap!"

def test_domain_filtering(client):
    res = client.get("/search?q=python&domain=docs.python.org")
    assert res.status_code == 200
    for r in res.json()["results"]:
        assert "docs.python.org" in r["url"].lower()

def test_api_400_boundaries(client):
    # Valid boundaries
    res1 = client.get("/search?q=test&top_k=0")
    assert res1.status_code == 400
    
    res2 = client.get("/search?q=test&offset=-1")
    assert res2.status_code == 400
    
    res3 = client.get("/search?q=" + "a"*501)
    assert res3.status_code == 400

def test_search_response_compatibility(client):
    res = client.get("/search?q=python")
    assert res.status_code == 200
    data = res.json()
    assert "query" in data
    assert "total_results" in data
    assert "results" in data
    
    if len(data["results"]) > 0:
        first = data["results"][0]
        assert "doc_id" in first
        assert "title" in first
        assert "url" in first
        assert "score" in first
        assert "snippet" in first
        assert "matches" in first
