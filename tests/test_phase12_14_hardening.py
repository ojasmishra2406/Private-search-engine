import pytest
import os
import numpy as np
from src.dense.embeddings import MockEmbeddingModel
from src.core.indexer import IncrementalIndexer
from fastapi.testclient import TestClient
from src.api.main import app, app_state
import pickle

client = TestClient(app)

def test_api_input_defense():
    """Verify input defense bounds on API endpoints."""
    # 1. Very long query (> 500 chars)
    long_q = "a" * 501
    res = client.get(f"/search?q={long_q}")
    assert res.status_code == 400
    assert "too long" in res.json()["detail"].lower()
    
    # 2. Exactly 500 chars (should pass validation)
    exact_q = "a" * 500
    res = client.get(f"/search?q={exact_q}")
    # 503 means search engine not initialized (if ran isolated), but it shouldn't be 400
    assert res.status_code != 400

    # 3. Empty / whitespace query
    res = client.get("/search?q=   ")
    assert res.status_code == 200
    assert res.json()["total_results"] == 0

def test_lru_cache_mutation_safety():
    """Verify cached embedding arrays cannot be corrupted by caller mutation."""
    model = MockEmbeddingModel()
    q = "test query"
    
    # Fetch first time
    emb1 = model.encode_query(q)
    # Mutate the returned array
    emb1[0] = 999.0
    
    # Fetch second time (should hit cache)
    emb2 = model.encode_query(q)
    
    # If the cache returned a reference to the same uncopied array, 
    # emb2[0] would incorrectly be 999.0
    assert emb2[0] != 999.0
    
def test_atomic_persistence_failure_cleanup(tmp_path, monkeypatch):
    """Verify that a failure during serialization cleans up the .tmp file."""
    index_path = str(tmp_path / "index.pkl")
    indexer = IncrementalIndexer(index_path)
    
    # Add a mock document so it has something to save
    indexer.index.add_document("doc1", ["hello"])
    
    # Force pickle.dump to throw an exception
    def mock_dump(*args, **kwargs):
        raise RuntimeError("Disk write failed!")
        
    monkeypatch.setattr(pickle, "dump", mock_dump)
    
    with pytest.raises(RuntimeError, match="Disk write failed!"):
        indexer._save_index_atomic()
        
    # The temp file should have been cleaned up
    tmp_file = index_path + '.tmp'
    assert not os.path.exists(tmp_file), "Temporary file was not cleaned up after failure!"
    
def test_health_check_degraded():
    """Verify /health correctly identifies degraded states without crashing."""
    # Temporarily remove dense retriever from state
    original_dense = app_state.get("dense_retriever")
    app_state["dense_retriever"] = None
    
    try:
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["dense_index_loaded"] is False
    finally:
        # Restore
        app_state["dense_retriever"] = original_dense
