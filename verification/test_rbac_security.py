import pytest
import time
from fastapi.testclient import TestClient
from src.api.main import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_zero_leakage_hr(client):
    # HR Role should see Executive Bonuses
    res = client.get("/search?q=compensation&role=HR&top_k=500")
    assert res.status_code == 200
    data = res.json()
    titles = [r['title'] for r in data['results']]
    assert any("Executive Bonuses" in t for t in titles), "HR should see HR docs"
    
def test_zero_leakage_engineering(client):
    # Engineering Role should NOT see Executive Bonuses
    res = client.get("/search?q=compensation&role=Engineering&top_k=500")
    data = res.json()
    titles = [r['title'] for r in data['results']]
    assert not any("Executive Bonuses" in t for t in titles), "Engineering must NOT see HR docs"

def test_public_role(client):
    res = client.get("/search?q=API&role=Public&top_k=500")
    data = res.json()
    titles = [r['title'] for r in data['results']]
    assert any("API Guide" in t for t in titles), "Public should see Public docs"
    
    # Public should not see Kernel Architecture
    res = client.get("/search?q=firewall&role=Public&top_k=500")
    data = res.json()
    titles = [r['title'] for r in data['results']]
    assert not any("Kernel" in t for t in titles), "Public must NOT see Engineering docs"

def test_admin_role(client):
    # Admin sees everything
    res = client.get("/search?q=compensation firewall API&role=Admin&top_k=500")
    data = res.json()
    titles = [r['title'] for r in data['results']]
    assert len(titles) > 0, "Admin should find all matches"

def test_latency_overhead(client):
    # Unauthenticated baseline (simulated) vs Authenticated
    t0 = time.perf_counter()
    client.get("/search?q=java&role=Admin")
    t_admin = time.perf_counter() - t0
    
    t0 = time.perf_counter()
    client.get("/search?q=java&role=Public")
    t_public = time.perf_counter() - t0
    
    diff = abs(t_admin - t_public)
    assert diff < 0.1, f"Latency overhead too high: {diff}s"

if __name__ == '__main__':
    pytest.main(['-v', 'verification/test_rbac_security.py'])
