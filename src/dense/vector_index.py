import os
import faiss
import numpy as np
from typing import List, Tuple, Set
from src.core.logger import logger

class VectorIndex:
    def __init__(self, dimension: int = 384, index_path: str = "dense.index"):
        self.dimension = dimension
        self.index_path = index_path
        self.index = self._load_or_create()

    def _load_or_create(self) -> faiss.IndexIDMap:
        """Reloads FAISS index if it exists; otherwise creates new."""
        if os.path.exists(self.index_path):
            try:
                idx = faiss.read_index(self.index_path)
                if idx.d != self.dimension:
                    raise ValueError(f"Index dimension mismatch. Expected {self.dimension}, got {idx.d}")
                return idx
            except Exception as e:
                logger.logger.warning(f"Failed to load dense index, creating new: {e}")
                
        # Create new index using Inner Product
        base_index = faiss.IndexHNSWFlat(self.dimension, 32, faiss.METRIC_INNER_PRODUCT)
        return faiss.IndexIDMap(base_index)

    def save_atomic(self):
        """Atomically persists the vector index."""
        tmp_idx = self.index_path + '.tmp'
        
        try:
            faiss.write_index(self.index, tmp_idx)
            os.replace(tmp_idx, self.index_path)
            
            # Clean up legacy map file if it exists
            legacy_map = "dense_map.pkl"
            if os.path.exists(legacy_map):
                os.remove(legacy_map)
                logger.logger.info("Removed legacy dense_map.pkl mapping file.")
        except Exception as e:
            if os.path.exists(tmp_idx):
                try:
                    os.remove(tmp_idx)
                except OSError:
                    pass
            raise e

    def add_vectors(self, int_ids: List[int], vectors: np.ndarray):
        """Adds or replaces vectors for the given integer document IDs."""
        if not int_ids or len(int_ids) != vectors.shape[0]:
            return
            
        ids_array = np.array(int_ids, dtype=np.int64)
        
        # Remove existing vectors for these IDs to avoid duplicates (IndexIDMap appends)
        try:
            self.index.remove_ids(ids_array)
        except RuntimeError:
            pass
        
        # Add new vectors
        self.index.add_with_ids(vectors, ids_array)

    def remove_vectors(self, int_ids: List[int]):
        """Removes vectors corresponding to the provided integer IDs."""
        if not int_ids:
            return
        ids_array = np.array(int_ids, dtype=np.int64)
        try:
            self.index.remove_ids(ids_array)
        except RuntimeError as e:
            # HNSW does not support remove_ids. We catch this to allow atomic re-indexing to proceed.
            pass

    def search(self, query_vector: np.ndarray, authorized_int_ids: Set[int] = None, top_k: int = 5) -> List[Tuple[int, float]]:
        """Returns top_k (int_id, similarity_score) tuples, strictly pre-filtered."""
        if self.index.ntotal == 0:
            return []
            
        # Pre-Retrieval FAISS Masking
        params = None
        if authorized_int_ids is not None:
            if len(authorized_int_ids) == 0:
                # User has zero authorized documents, bail immediately
                return []
            allowed_ids_np = np.array(list(authorized_int_ids), dtype=np.int64)
            selector = faiss.IDSelectorArray(len(allowed_ids_np), faiss.swig_ptr(allowed_ids_np))
            params = faiss.SearchParameters(sel=selector)
            
        k = min(top_k, self.index.ntotal)
        if params is not None:
            scores, int_ids = self.index.search(query_vector, k, params=params)
        else:
            scores, int_ids = self.index.search(query_vector, k)
        
        results = []
        for score, iid in zip(scores[0], int_ids[0]):
            if iid != -1:
                results.append((int(iid), float(score)))
                
        return results

    @property
    def total_docs(self) -> int:
        return self.index.ntotal
