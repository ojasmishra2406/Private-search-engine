import os
import pickle
import time
from typing import Dict
from sqlalchemy.orm import Session
from src.storage.models import DBDocument, IndexingStatus, IndexVersion
from src.core.index import InvertedIndex
from src.core.tokenizer import Tokenizer


class IncrementalIndexer:
    """
    Phase 7 Incremental Indexing Daemon.
    
    Responsible for synchronizing the authoritative SQLite metadata state
    with the fast in-memory inverted index, and safely persisting the result.
    """
    def __init__(self, index_path: str = 'index.pkl'):
        self.index_path = index_path
        self.tokenizer = Tokenizer()
        self.index = self._load_or_create_index()

    def _load_or_create_index(self) -> InvertedIndex:
        from src.core.logger import logger
        if os.path.exists(self.index_path):
            try:
                with open(self.index_path, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                logger.logger.warning("Warning: Failed to load index from %s, creating new: %s", self.index_path, e)
        return InvertedIndex()

    def _save_index_atomic(self):
        """Safely persist the index to disk using a temporary file and atomic replace."""
        tmp_path = self.index_path + '.tmp'
        # Atomic write pattern to prevent corruption on crash
        try:
            with open(tmp_path, 'wb') as f:
                pickle.dump(self.index, f)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, self.index_path)
        except Exception as e:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
            raise e

    def sync(self, session: Session, dense_indexer=None) -> Dict[str, int]:
        """
        Synchronize PENDING documents into the inverted index.
        Returns a dictionary of statistics.
        """
        from src.core.logger import logger
        stats = {'added': 0, 'updated': 0, 'deleted': 0, 'failed': 0, 'skipped': 0}

        # 1. Handle Deletions (TOMBSTONES)
        # Any document marked is_deleted=True and indexing_status=PENDING
        deleted_docs = session.query(DBDocument).filter_by(
            is_deleted=True, indexing_status=IndexingStatus.PENDING.value
        ).all()

        deleted_ids = []
        for doc in deleted_docs:
            try:
                self.index.delete_document(doc.int_id)
                deleted_ids.append(doc.int_id)
                doc.indexing_status = IndexingStatus.INDEXED.value
                stats['deleted'] += 1
            except Exception as e:
                logger.logger.error("Failed to remove document %s from index: %s", doc.id, e)
                doc.indexing_status = IndexingStatus.FAILED.value
                stats['failed'] += 1
                
        if dense_indexer and deleted_ids:
            try:
                dense_indexer.remove_batch(deleted_ids)
            except Exception as e:
                logger.logger.error("Dense indexer failed on deletion batch: %s", e)
                raise RuntimeError(f"Index sync failed during dense deletion batch: {e}")

        # 2. Handle New and Modified (ACTIVE)
        # Any document marked is_deleted=False and indexing_status=PENDING
        pending_docs = session.query(DBDocument).filter_by(
            is_deleted=False, indexing_status=IndexingStatus.PENDING.value
        ).all()

        # Collect batches for dense indexing if enabled
        dense_batch_texts = []
        dense_batch_ids = []

        for doc in pending_docs:
            try:
                # Lexical Indexing
                tokens = self.tokenizer.tokenize(doc.content)
                self.index.add_document(doc.int_id, tokens)
                
                # Dense Indexing collection
                if dense_indexer:
                    dense_batch_ids.append(doc.int_id)
                    dense_batch_texts.append(doc.content)
                
                doc.indexing_status = IndexingStatus.INDEXED.value
                
                if doc.version == 1:
                    stats['added'] += 1
                else:
                    stats['updated'] += 1
            except Exception as e:
                logger.logger.error("Failed to index document %s: %s", doc.id, e)
                doc.indexing_status = IndexingStatus.FAILED.value
                stats['failed'] += 1

        # Process the collected dense batch
        if dense_indexer and dense_batch_ids:
            try:
                dense_indexer.add_batch(dense_batch_ids, dense_batch_texts)
            except Exception as e:
                logger.logger.error("Dense indexer failed on batch: %s", e)
                raise RuntimeError(f"Index sync failed during dense batch addition: {e}")

        # 3. Persist and Track Consistency
        if stats['added'] > 0 or stats['updated'] > 0 or stats['deleted'] > 0:
            # First write to disk atomically
            self._save_index_atomic()
            if dense_indexer:
                try:
                    dense_indexer.save_atomic()
                except Exception as e:
                    logger.logger.error("Failed to persist dense index: %s", e)
                    raise RuntimeError(f"Index sync failed during dense index save: {e}")
            
            # Then record the new generation in SQLite
            max_v = session.query(IndexVersion).order_by(IndexVersion.version.desc()).first()
            new_version_num = (max_v.version + 1) if max_v else 1
            
            iv = IndexVersion(
                version=new_version_num,
                document_count=self.index.total_docs,
                status="COMPLETE"
            )
            session.add(iv)
            
            # Commit the indexing_status changes and the new IndexVersion together
            session.commit()
            
        return stats
