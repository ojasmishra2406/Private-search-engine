import pytest
from fastapi.testclient import TestClient
from src.api.main import app

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_benchmark_api_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ["ok", "healthy"]
    assert data["parity_ok"] is True

def test_api_performance_limits(client):
    # Search should finish reasonably fast
    resp = client.get("/search?q=test&top_k=5")
    assert resp.status_code == 200
    assert resp.elapsed.total_seconds() < 5.0 # Max boundary

def test_incremental_indexing_preserves_parity():
    # If we add a doc, it should remain correct
    pass

