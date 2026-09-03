import os
import pytest
import numpy as np
from src.dense.embeddings import MockEmbeddingModel
from src.dense.vector_index import VectorIndex
from src.dense.retriever import DenseRetriever

@pytest.fixture
def mock_model():
    return MockEmbeddingModel(dimension=384)

@pytest.fixture
def temp_paths(tmp_path):
    return (
        os.path.join(tmp_path, "test.index"),
        os.path.join(tmp_path, "test_map.pkl")
    )

def test_embedding_generation_dimensionality(mock_model):
    """Test 1: embedding generation returns expected dimensionality"""
    embeddings = mock_model.encode(["hello world", "test"])
    assert embeddings.shape == (2, 384)

def test_identical_text_stable_embeddings(mock_model):
    """Test 2: identical text produces stable embeddings"""
    emb1 = mock_model.encode(["stable text"])
    emb2 = mock_model.encode(["stable text"])
    np.testing.assert_array_almost_equal(emb1, emb2)

def test_query_embedding_works(mock_model):
    """Test 3: query embedding works"""
    emb = mock_model.encode(["query"])
    assert emb.shape == (1, 384)
    # Check normalization
    assert np.isclose(np.linalg.norm(emb[0]), 1.0)

def test_vector_index_add_vectors_and_mapping(temp_paths):
    """Test 4 & 6: vector index can add vectors and mapping is correct"""
    idx_path, map_path = temp_paths
    v_index = VectorIndex(dimension=384, index_path=idx_path, map_path=map_path)
    
    vecs = np.random.randn(2, 384).astype(np.float32)
    vecs = vecs / np.linalg.norm(vecs, axis=1, keepdims=True)
    
    v_index.add_vectors(["doc1", "doc2"], vecs)
    
    assert v_index.total_docs == 2
    assert "doc1" in v_index.ext_to_int
    assert "doc2" in v_index.ext_to_int
    assert v_index.ext_to_int["doc1"] == 1
    assert v_index.int_to_ext[1] == "doc1"

def test_nearest_neighbor_search(mock_model, temp_paths):
    """Test 5 & 14: nearest-neighbor search returns expected document and respects top-k"""
    idx_path, map_path = temp_paths
    v_index = VectorIndex(dimension=384, index_path=idx_path, map_path=map_path)
    
    # 3 distinct docs
    texts = ["apple", "banana", "cherry"]
    vecs = mock_model.encode(texts)
    v_index.add_vectors(["doc_apple", "doc_banana", "doc_cherry"], vecs)
    
    retriever = DenseRetriever(mock_model, v_index)
    
    # Query "apple" -> Should perfectly match doc_apple since mock model is deterministic
    results = retriever.search("apple", top_k=2)
    
    assert len(results) == 2
    assert results[0][0] == "doc_apple"
    # inner product of normalized identical vector is ~1.0
    assert np.isclose(results[0][1], 1.0, atol=1e-4)

def test_persistence_and_reload(mock_model, temp_paths):
    """Test 7: vector index persists and reloads correctly"""
    idx_path, map_path = temp_paths
    v_index = VectorIndex(dimension=384, index_path=idx_path, map_path=map_path)
    
    vecs = mock_model.encode(["save me"])
    v_index.add_vectors(["doc_save"], vecs)
    v_index.save_atomic()
    
    assert os.path.exists(idx_path)
    assert os.path.exists(map_path)
    
    # Reload
    v_index2 = VectorIndex(dimension=384, index_path=idx_path, map_path=map_path)
    assert v_index2.total_docs == 1
    assert v_index2.ext_to_int["doc_save"] == 1

def test_wrong_dimension_rejected(temp_paths):
    """Test 8: wrong embedding dimension is rejected"""
    idx_path, map_path = temp_paths
    v_index = VectorIndex(dimension=384, index_path=idx_path, map_path=map_path)
    vecs = np.random.randn(1, 384).astype(np.float32)
    v_index.add_vectors(["doc1"], vecs)
    v_index.save_atomic()
    
    # Try loading with wrong dimension expectation
    # VectorIndex catches it and creates a NEW index, printing a warning.
    # The new index should have 0 docs.
    v_index_wrong = VectorIndex(dimension=256, index_path=idx_path, map_path=map_path)
    assert v_index_wrong.total_docs == 0

def test_deleted_documents_not_returned(mock_model, temp_paths):
    """Test 9: deleted documents are not returned"""
    idx_path, map_path = temp_paths
    v_index = VectorIndex(dimension=384, index_path=idx_path, map_path=map_path)
    
    vecs = mock_model.encode(["delete me"])
    v_index.add_vectors(["doc_del"], vecs)
    assert v_index.total_docs == 1
    
    v_index.remove_vectors(["doc_del"])
    assert v_index.total_docs == 0
    
    retriever = DenseRetriever(mock_model, v_index)
    results = retriever.search("delete me", top_k=5)
    assert len(results) == 0

def test_modified_documents_updated(mock_model, temp_paths):
    """Test 11: modified documents receive updated embeddings (replacement)"""
    idx_path, map_path = temp_paths
    v_index = VectorIndex(dimension=384, index_path=idx_path, map_path=map_path)
    
    vec1 = mock_model.encode(["v1"])
    v_index.add_vectors(["doc_mod"], vec1)
    
    # modify
    vec2 = mock_model.encode(["v2"])
    v_index.add_vectors(["doc_mod"], vec2)
    
    # Still 1 doc, but internal ID incremented and replaced
    assert v_index.total_docs == 1
    assert v_index.ext_to_int["doc_mod"] == 2
    assert 1 not in v_index.int_to_ext

def test_empty_index_behaves_safely(mock_model, temp_paths):
    """Test 12: empty index behaves safely"""
    idx_path, map_path = temp_paths
    v_index = VectorIndex(dimension=384, index_path=idx_path, map_path=map_path)
    retriever = DenseRetriever(mock_model, v_index)
    
    results = retriever.search("query", top_k=5)
    assert results == []

def test_unknown_empty_query_behaves_safely(mock_model, temp_paths):
    """Test 13: unknown/empty query behaves safely"""
    idx_path, map_path = temp_paths
    v_index = VectorIndex(dimension=384, index_path=idx_path, map_path=map_path)
    vecs = mock_model.encode(["hello"])
    v_index.add_vectors(["doc1"], vecs)
    
    retriever = DenseRetriever(mock_model, v_index)
    
    assert retriever.search("", top_k=5) == []
    assert retriever.search("   ", top_k=5) == []
