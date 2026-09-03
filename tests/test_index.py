import pytest
from src.core.index import InvertedIndex

def test_add_document():
    index = InvertedIndex()
    doc_id_str = "hash123"
    tokens = ["hello", "world", "hello"]
    
    index.add_document(doc_id_str, tokens)
    
    assert index.total_docs == 1
    assert index.total_tokens == 3
    
    internal_id = index.ext_to_int_doc_id[doc_id_str]
    assert internal_id == 0
    
    term_ids = index.forward_index[internal_id]
    assert len(term_ids) == 3
    
    hello_id = index.term_to_id["hello"]
    postings = index.postings[hello_id]
    assert len(postings) == 1
    assert postings[0].doc_id == internal_id
    assert postings[0].term_freq == 2
    assert postings[0].positions == [0, 2]

def test_delete_document():
    index = InvertedIndex()
    index.add_document("doc1", ["a", "b", "c"])
    index.add_document("doc2", ["c", "d", "e"])
    
    assert index.total_docs == 2
    
    c_term_id = index.term_to_id["c"]
    assert len(index.postings[c_term_id]) == 2
    
    index.delete_document("doc1")
    
    assert index.total_docs == 1
    assert index.total_tokens == 3
    
    internal_id_1 = index.ext_to_int_doc_id["doc1"]
    assert internal_id_1 not in index.forward_index
    
    assert len(index.postings[c_term_id]) == 1
    assert index.postings[c_term_id][0].doc_id == index.ext_to_int_doc_id["doc2"]

def test_update_document():
    index = InvertedIndex()
    index.add_document("doc1", ["old", "content"])
    
    index.add_document("doc1", ["new", "content", "added"])
    
    assert index.total_docs == 1
    assert index.total_tokens == 3
    
    old_id = index.term_to_id.get("old")
    if old_id is not None:
        assert len(index.postings[old_id]) == 0
        
    new_id = index.term_to_id["new"]
    assert len(index.postings[new_id]) == 1

def test_multiple_occurrences_in_one_document():
    index = InvertedIndex()
    index.add_document("doc1", ["apple", "banana", "apple", "cherry", "apple"])
    
    apple_id = index.term_to_id["apple"]
    postings = index.postings[apple_id]
    
    assert len(postings) == 1
    assert postings[0].term_freq == 3
    assert postings[0].positions == [0, 2, 4]

def test_term_shared_by_multiple_documents():
    index = InvertedIndex()
    index.add_document("doc1", ["apple", "banana"])
    index.add_document("doc2", ["cherry", "apple"])
    index.add_document("doc3", ["apple", "apple"])
    
    apple_id = index.term_to_id["apple"]
    postings = index.postings[apple_id]
    
    assert len(postings) == 3
    # Check correct term frequency in shared documents
    assert postings[0].doc_id == index.ext_to_int_doc_id["doc1"]
    assert postings[0].term_freq == 1
    assert postings[1].doc_id == index.ext_to_int_doc_id["doc2"]
    assert postings[1].term_freq == 1
    assert postings[2].doc_id == index.ext_to_int_doc_id["doc3"]
    assert postings[2].term_freq == 2

def test_deletion_does_not_affect_others():
    index = InvertedIndex()
    index.add_document("doc1", ["apple", "banana"])
    index.add_document("doc2", ["apple", "cherry"])
    
    apple_id = index.term_to_id["apple"]
    assert len(index.postings[apple_id]) == 2
    
    index.delete_document("doc1")
    
    assert len(index.postings[apple_id]) == 1
    assert index.postings[apple_id][0].doc_id == index.ext_to_int_doc_id["doc2"]
    assert index.postings[apple_id][0].term_freq == 1

def test_updating_document_removes_old_terms():
    index = InvertedIndex()
    index.add_document("doc1", ["apple", "banana"])
    
    banana_id = index.term_to_id["banana"]
    assert len(index.postings[banana_id]) == 1
    
    # Update document, removing 'banana'
    index.add_document("doc1", ["apple", "cherry"])
    
    assert len(index.postings[banana_id]) == 0
    cherry_id = index.term_to_id["cherry"]
    assert len(index.postings[cherry_id]) == 1
