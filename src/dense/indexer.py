from typing import List
from src.dense.embeddings import EmbeddingModel, MockEmbeddingModel
from src.dense.vector_index import VectorIndex

class DenseIndexer:
    """
    Handles batched additions to the FAISS VectorIndex using an EmbeddingModel.
    Used by the IncrementalIndexer daemon to coordinate dense updates.
    """
    def __init__(self, model, vector_index: VectorIndex, batch_size: int = 32):
        self.model = model
        self.vector_index = vector_index
        self.batch_size = batch_size

    def add_batch(self, int_ids: List[int], texts: List[str]):
        """Encodes texts in batches and adds them to the vector index using int_ids."""
        if not int_ids or not texts or len(int_ids) != len(texts):
            return
            
        # Process in chunks of self.batch_size
        for i in range(0, len(int_ids), self.batch_size):
            batch_ids = int_ids[i : i + self.batch_size]
            batch_texts = texts[i : i + self.batch_size]
            
            # Generate embeddings
            embeddings = self.model.encode(batch_texts, batch_size=self.batch_size)
            
            # Add to FAISS index
            self.vector_index.add_vectors(batch_ids, embeddings)

    def remove_batch(self, int_ids: List[int]):
        """Removes the given integer IDs from the vector index."""
        self.vector_index.remove_vectors(int_ids)
        
    def save_atomic(self):
        """Persists the underlying vector index atomically."""
        self.vector_index.save_atomic()
