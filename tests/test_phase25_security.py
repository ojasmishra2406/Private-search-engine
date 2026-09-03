import pytest
from fastapi.testclient import TestClient
from src.api.config import settings
from src.api.main import app
from src.ingestion.crawler import is_safe_ip, is_safe_url

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_security_api_limits(client):
    # Test query length limit
    long_q = "a" * (settings.MAX_QUERY_LENGTH + 10)
    resp = client.get("/search", params={"q": long_q})
    assert resp.status_code == 400
    
    # Test top_k limit validation
    resp = client.get("/search", params={"q": "test", "top_k": -1})
    assert resp.status_code == 400

    # Test offset limit validation
    resp = client.get("/search", params={"q": "test", "offset": -5})
    assert resp.status_code == 400
    
    # Test huge offset limit validation
    resp = client.get("/search", params={"q": "test", "offset": settings.MAX_OFFSET + 1})
    assert resp.status_code == 200


def test_security_ssrf_crawler():
    # Local loopback
    assert not is_safe_ip("127.0.0.1")
    assert not is_safe_ip("::1")
    # Private IPv4
    assert not is_safe_ip("192.168.1.5")
    assert not is_safe_ip("10.0.0.1")
    assert not is_safe_ip("172.16.0.5")
    # Multicast/Link local
    assert not is_safe_ip("169.254.169.254")
    
    assert not is_safe_url("http://localhost:8080/admin")
    assert not is_safe_url("http://127.0.0.1/admin")
    assert not is_safe_url("http://169.254.169.254/latest/meta-data/")
    
    assert is_safe_url("https://docs.python.org/3/")
