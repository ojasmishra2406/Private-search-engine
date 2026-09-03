import pytest
from fastapi.testclient import TestClient
from src.api.config import settings
from src.api.main import app

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_config_loaded_correctly():
    assert settings.ENV in ["development", "production", "test"]
    assert settings.MAX_TOP_K == 100
    assert settings.MAX_OFFSET == 10000
    assert "sqlite" in settings.DB_PATH

def test_deployment_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert "lexical_doc_count" in resp.json()
    
def test_deployment_readiness(client):
    pass

