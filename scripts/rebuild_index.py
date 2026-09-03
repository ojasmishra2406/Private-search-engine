import os
import shutil
import pickle
import sys
from src.core.indexer import IncrementalIndexer
from src.dense.indexer import DenseIndexer
from src.dense.embeddings import EmbeddingModel
from src.dense.vector_index import VectorIndex
from src.storage.database import Database
from src.storage.models import DBDocument, IndexingStatus
from src.api.config import settings
from src.core.logger import logger

def rebuild_index():
    logger.logger.info("Starting safe index rebuild...")
    
    # 1. Setup paths for temporary rebuilt indexes
    tmp_lexical = settings.LEXICAL_INDEX_PATH + ".rebuild"
    tmp_dense = settings.DENSE_INDEX_PATH + ".rebuild"
    tmp_dense_map = settings.DENSE_MAP_PATH + ".rebuild"
    
    # Clean up any previous failed rebuilds
    for p in [tmp_lexical, tmp_dense, tmp_dense_map]:
        if os.path.exists(p):
            os.remove(p)
            
    try:
        db = Database()
        db.init_db()
        session = db.get_session()
        
        # We don't want to actually change the existing database state to PENDING 
        # until we successfully rebuild, or we might break the live system.
        # But `IncrementalIndexer.sync` relies on PENDING state.
        # Better: we just manually rebuild from all ACTIVE documents in SQLite into the new indexes.
        
        logger.logger.info("Fetching authoritative documents from DB...")
        active_docs = session.query(DBDocument).filter_by(is_deleted=False).all()
        
        logger.logger.info(f"Rebuilding {len(active_docs)} documents...")
        
        # 2. Recreate Lexical and Dense Indexes manually in memory
        lex_indexer = IncrementalIndexer(tmp_lexical)
        
        # Create a fresh dense model/index
        model = EmbeddingModel(model_name=settings.DENSE_MODEL_NAME)
        vec_index = VectorIndex(index_path=tmp_dense, map_path=tmp_dense_map)
        dense_indexer = DenseIndexer(model, vec_index)
        
        # Batch dense indexing for performance
        dense_batch_ids = []
        dense_batch_texts = []
        
        for doc in active_docs:
            tokens = lex_indexer.tokenizer.tokenize(doc.content)
            lex_indexer.index.add_document(doc.id, tokens)
            
            dense_batch_ids.append(doc.id)
            dense_batch_texts.append(doc.content)
            
            if len(dense_batch_ids) >= 100:
                dense_indexer.add_batch(dense_batch_ids, dense_batch_texts)
                dense_batch_ids = []
                dense_batch_texts = []
                
        if dense_batch_ids:
            dense_indexer.add_batch(dense_batch_ids, dense_batch_texts)
            
        # 3. Save new indexes to the tmp paths
        logger.logger.info("Saving rebuilt indexes to temporary files...")
        lex_indexer._save_index_atomic() # This writes to .tmp and renames to tmp_lexical
        dense_indexer.save_atomic() # This saves to tmp_dense
        
        # 4. Verify Parity
        if lex_indexer.index.total_docs != len(active_docs) or vec_index.total_docs != len(active_docs):
            raise RuntimeError("Parity mismatch during rebuild! Aborting atomic swap.")
            
        # 5. Atomic Replace
        logger.logger.info("Parity verified. Performing atomic swap of old artifacts...")
        os.replace(tmp_lexical, settings.LEXICAL_INDEX_PATH)
        os.replace(tmp_dense, settings.DENSE_INDEX_PATH)
        os.replace(tmp_dense_map, settings.DENSE_MAP_PATH)
        
        # Also ensure DB documents have status INDEXED
        for doc in active_docs:
            doc.indexing_status = IndexingStatus.INDEXED.value
        session.commit()
        
        logger.logger.info("Index rebuild completed successfully.")
        
    except Exception as e:
        logger.logger.error(f"Rebuild failed: {e}. Preserving original working index.")
        session.rollback()
        # Clean up tmp files
        for p in [tmp_lexical, tmp_dense, tmp_dense_map]:
            if os.path.exists(p):
                os.remove(p)
        sys.exit(1)
    finally:
        session.close()

if __name__ == "__main__":
    rebuild_index()
