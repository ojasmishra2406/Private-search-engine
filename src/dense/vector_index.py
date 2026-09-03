import os
import faiss
import pickle
import numpy as np
from typing import List, Tuple
from src.core.logger import logger

class VectorIndex:
    def __init__(self, dimension: int = 384, index_path: str = "dense.index", map_path: str = "dense_map.pkl"):
        self.dimension = dimension
        self.index_path = index_path
        self.map_path = map_path
        
        # ID mappings: external_id (str) <-> internal_id (int64)
        self.ext_to_int = {}
        self.int_to_ext = {}
        self.next_int_id = 1
        
        self.index = self._load_or_create()

    def _load_or_create(self) -> faiss.IndexIDMap:
        """Reloads FAISS index and mappings if they exist; otherwise creates new."""
        if os.path.exists(self.index_path) and os.path.exists(self.map_path):
            try:
                idx = faiss.read_index(self.index_path)
                if idx.d != self.dimension:
                    raise ValueError(f"Index dimension mismatch. Expected {self.dimension}, got {idx.d}")
                with open(self.map_path, 'rb') as f:
                    mapping = pickle.load(f)
                    self.ext_to_int = mapping['ext_to_int']
                    self.int_to_ext = mapping['int_to_ext']
                    self.next_int_id = mapping['next_int_id']
                return idx
            except Exception as e:
                logger.logger.warning(f"Failed to load dense index, creating new: {e}")
                
        # Create new index using Inner Product (cosine similarity if normalized)
        base_index = faiss.IndexFlatIP(self.dimension)
        return faiss.IndexIDMap(base_index)

    def save_atomic(self):
        """Atomically persists the vector index and mapping."""
        tmp_idx = self.index_path + '.tmp'
        tmp_map = self.map_path + '.tmp'
        
        try:
            faiss.write_index(self.index, tmp_idx)
            with open(tmp_map, 'wb') as f:
                pickle.dump({
                    'ext_to_int': self.ext_to_int,
                    'int_to_ext': self.int_to_ext,
                    'next_int_id': self.next_int_id
                }, f)
                f.flush()
                os.fsync(f.fileno())
                
            os.replace(tmp_idx, self.index_path)
            os.replace(tmp_map, self.map_path)
        except Exception as e:
            for tmp in (tmp_idx, tmp_map):
                if os.path.exists(tmp):
                    try:
                        os.remove(tmp)
                    except OSError:
                        pass
            raise e

    def add_vectors(self, ext_ids: List[str], vectors: np.ndarray):
        """Adds or replaces vectors for the given document IDs."""
        if not ext_ids or len(ext_ids) != vectors.shape[0]:
            return
            
        int_ids = []
        for eid in ext_ids:
            # Replaces old vector if exists
            if eid in self.ext_to_int:
                self.remove_vectors([eid])
                
            iid = self.next_int_id
            self.ext_to_int[eid] = iid
            self.int_to_ext[iid] = eid
            self.next_int_id += 1
            int_ids.append(iid)
            
        ids_array = np.array(int_ids, dtype=np.int64)
        self.index.add_with_ids(vectors, ids_array)

    def remove_vectors(self, ext_ids: List[str]):
        """Removes vectors corresponding to the provided external IDs."""
        ids_to_remove = []
        for eid in ext_ids:
            if eid in self.ext_to_int:
                iid = self.ext_to_int[eid]
                ids_to_remove.append(iid)
                # Cleanup mappings
                del self.ext_to_int[eid]
                del self.int_to_ext[iid]
                
        if ids_to_remove:
            ids_array = np.array(ids_to_remove, dtype=np.int64)
            self.index.remove_ids(ids_array)

    def search(self, query_vector: np.ndarray, top_k: int = 5) -> List[Tuple[str, float]]:
        """Returns top_k (external_id, similarity_score) tuples."""
        if self.index.ntotal == 0:
            return []
            
        k = min(top_k, self.index.ntotal)
        scores, int_ids = self.index.search(query_vector, k)
        
        results = []
        for score, iid in zip(scores[0], int_ids[0]):
            if iid != -1 and iid in self.int_to_ext:
                results.append((self.int_to_ext[iid], float(score)))
                
        return results

    @property
    def total_docs(self) -> int:
        return self.index.ntotal
