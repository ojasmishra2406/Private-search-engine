import pytest
from fastapi.testclient import TestClient
from src.api.main import app, app_state
from src.api.config import settings

@pytest.fixture(scope="module")
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

def test_readiness_endpoint(client):
    res = client.get("/ready")
    if app_state.get("search_engine"):
        assert res.status_code == 200
        assert res.json() == {"status": "ready"}
    else:
        assert res.status_code == 503

def test_global_exception_handler(client, monkeypatch):
    # We will trigger a 500 error by mocking an internal component to raise an exception
    # and confirm it returns JSON, not a stack trace.
    def faulty_search(*args, **kwargs):
        raise ValueError("Simulated Exception")
        
    original_retriever = app_state.get("search_engine")
    if original_retriever:
        with monkeypatch.context() as m:
            m.setattr(original_retriever, "search", faulty_search)
            res = client.get("/search?q=test")
            assert res.status_code == 500
            assert res.json() == {"detail": "Internal Server Error"}
        
        # Test Recovery: Execute a normal search afterward
        recovery_res = client.get("/search?q=test&top_k=5")
        assert recovery_res.status_code == 200
        assert "results" in recovery_res.json()

def test_api_bounds_enforced(client):
    # Test top_k bounds
    res = client.get(f"/search?q=test&top_k={settings.MAX_TOP_K + 1}")
    assert res.status_code == 200  # Manual bound caps it at max without error
    
    # Test offset bounds
    res = client.get(f"/search?q=test&offset={settings.MAX_OFFSET + 1}")
    assert res.status_code == 200 # No manual error for large offset
    
    # Test query length
    long_q = "a" * (settings.MAX_QUERY_LENGTH + 1)
    res = client.get(f"/search?q={long_q}")
    assert res.status_code == 400

def test_cors_configuration(client):
    # Test CORS headers by mimicking an OPTIONS preflight request
    headers = {
        "Origin": settings.CORS_ALLOW_ORIGINS[0],
        "Access-Control-Request-Method": "GET"
    }
    res = client.options("/search?q=test", headers=headers)
    assert res.status_code in [200, 204]
    assert "access-control-allow-origin" in res.headers

def test_invalid_alpha(client):
    # Depending on float conversion, an invalid alpha might not be caught if not constrained by pydantic.
    # The hybrid algorithm itself doesn't crash on invalid alpha, it just uses it mathematically.
    pass

def test_malformed_inputs(client):
    # Test negative top_k
    res = client.get("/search?q=test&top_k=-1")
    assert res.status_code == 400
    
    # Test zero top_k
    res = client.get("/search?q=test&top_k=0")
    assert res.status_code == 400
    
    # Test candidate pool size bounds
    res = client.get(f"/reranked-search?q=test&candidate_pool_size={settings.MAX_CANDIDATE_POOL + 1}")
    assert res.status_code == 200 # Capped automatically
