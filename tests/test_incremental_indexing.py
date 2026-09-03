import os
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.storage.models import Base, DBDocument, IndexingStatus, IndexVersion
from src.core.indexer import IncrementalIndexer
from src.core.index import InvertedIndex

@pytest.fixture
def test_db_session():
    # In-memory SQLite for speed and isolation
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def temp_index_path(tmp_path):
    return os.path.join(tmp_path, "test_index.pkl")


def test_new_document_indexed(test_db_session, temp_index_path):
    """Phase 7: NEW document -> INDEXED"""
    doc = DBDocument(
        id="doc_new", title="New", content="hello world", url="http://new",
        content_hash="hash1", indexing_status=IndexingStatus.PENDING.value
    )
    test_db_session.add(doc)
    test_db_session.commit()

    indexer = IncrementalIndexer(temp_index_path)
    stats = indexer.sync(test_db_session)

    assert stats['added'] == 1
    assert stats['updated'] == 0
    
    # Verify DB status updated
    test_db_session.refresh(doc)
    assert doc.indexing_status == IndexingStatus.INDEXED.value
    
    # Verify index contains document
    assert indexer.index.total_docs == 1
    assert "doc_new" in indexer.index.ext_to_int_doc_id
    
    # Verify IndexVersion created
    iv = test_db_session.query(IndexVersion).first()
    assert iv is not None
    assert iv.version == 1
    assert iv.document_count == 1


def test_unchanged_document_skipped(test_db_session, temp_index_path):
    """Phase 7: UNCHANGED document -> SKIP"""
    # Create doc already marked INDEXED (ingestion marks unchanged as skipped)
    doc = DBDocument(
        id="doc_skip", title="Skip", content="hello world", url="http://skip",
        content_hash="hash_skip", indexing_status=IndexingStatus.INDEXED.value
    )
    test_db_session.add(doc)
    test_db_session.commit()

    indexer = IncrementalIndexer(temp_index_path)
    stats = indexer.sync(test_db_session)

    assert sum(stats.values()) == 0
    assert indexer.index.total_docs == 0  # Was never added since it wasn't PENDING


def test_modified_document_reindexed(test_db_session, temp_index_path):
    """Phase 7: MODIFIED document -> RE-INDEX"""
    # 1. Add initial version
    doc = DBDocument(
        id="doc_mod", title="Mod", content="first version", url="http://mod",
        content_hash="hash1", indexing_status=IndexingStatus.PENDING.value
    )
    test_db_session.add(doc)
    test_db_session.commit()

    indexer = IncrementalIndexer(temp_index_path)
    indexer.sync(test_db_session)
    
    # Term 'first' should be in index
    term_id_first = indexer.index.term_to_id.get("first")
    assert term_id_first is not None
    assert len(indexer.index.postings[term_id_first]) == 1

    # 2. Modify document
    doc.content = "second edition"
    doc.content_hash = "hash2"
    doc.version += 1
    doc.indexing_status = IndexingStatus.PENDING.value
    test_db_session.commit()

    # 3. Re-index
    stats = indexer.sync(test_db_session)
    assert stats['updated'] == 1
    assert stats['added'] == 0
    
    # 4. Verify old term is removed from document
    # postings[term_id_first] should now be empty (since this doc was the only one)
    assert len(indexer.index.postings[term_id_first]) == 0
    
    # Verify new term is present
    term_id_second = indexer.index.term_to_id.get("second")
    assert term_id_second is not None
    assert len(indexer.index.postings[term_id_second]) == 1


def test_deleted_document_tombstoned(test_db_session, temp_index_path):
    """Phase 7: DELETED document -> TOMBSTONE -> Purged from index"""
    # 1. Add doc
    doc = DBDocument(
        id="doc_del", title="Del", content="delete me", url="http://del",
        content_hash="hash1", indexing_status=IndexingStatus.PENDING.value
    )
    test_db_session.add(doc)
    test_db_session.commit()
    
    indexer = IncrementalIndexer(temp_index_path)
    indexer.sync(test_db_session)
    assert indexer.index.total_docs == 1

    # 2. Tombstone document
    doc.is_deleted = True
    doc.indexing_status = IndexingStatus.PENDING.value
    test_db_session.commit()
    
    # 3. Sync deletions
    stats = indexer.sync(test_db_session)
    assert stats['deleted'] == 1
    
    # 4. Verify removal from index
    assert indexer.index.total_docs == 0
    # delete_document preserves the integer mapping to prevent reuse bugs, 
    # but removes it from the forward_index and doc_lengths.
    internal_doc_id = indexer.index.ext_to_int_doc_id["doc_del"]
    assert internal_doc_id not in indexer.index.forward_index


def test_atomic_persistence_and_reload(test_db_session, temp_index_path):
    """Phase 7: Index consistency and atomic reload"""
    doc = DBDocument(
        id="doc_pers", title="Persist", content="save me", url="http://pers",
        content_hash="hash_pers", indexing_status=IndexingStatus.PENDING.value
    )
    test_db_session.add(doc)
    test_db_session.commit()

    # Create indexer and sync
    indexer1 = IncrementalIndexer(temp_index_path)
    indexer1.sync(test_db_session)
    
    assert os.path.exists(temp_index_path)
    
    # Create new indexer instance (simulating restart)
    indexer2 = IncrementalIndexer(temp_index_path)
    assert indexer2.index.total_docs == 1
    assert "doc_pers" in indexer2.index.ext_to_int_doc_id
    
    # Verify IndexVersion table tracks the generation
    versions = test_db_session.query(IndexVersion).order_by(IndexVersion.version).all()
    assert len(versions) == 1
    assert versions[0].document_count == 1
