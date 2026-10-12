import numpy as np
from typing import List
import os

class EmbeddingModel:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2', device: str = 'cpu'):
        self.model_name = model_name
        self.dimension = 384
        
        onnx_path = "data/all-MiniLM-L6-v2.onnx" if os.path.exists("data/all-MiniLM-L6-v2.onnx") else "all-MiniLM-L6-v2.onnx"
        if os.path.exists(onnx_path):
            import onnxruntime as ort
            from transformers import AutoTokenizer
            self.tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
            sess_options = ort.SessionOptions()
            sess_options.intra_op_num_threads = 1
            sess_options.inter_op_num_threads = 1
            print("Creating inference session...")
            self.session = ort.InferenceSession(onnx_path, sess_options, providers=['CPUExecutionProvider'])
            print("Session created.")
            self.use_onnx = True
        else:
            try:
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer(model_name, device=device)
                self.use_onnx = False
            except ImportError:
                raise ImportError("sentence-transformers is not installed.")

    def mean_pooling(self, last_hidden_state, attention_mask):
        input_mask_expanded = np.expand_dims(attention_mask, -1)
        input_mask_expanded = np.broadcast_to(input_mask_expanded, last_hidden_state.shape)
        sum_embeddings = np.sum(last_hidden_state * input_mask_expanded, axis=1)
        sum_mask = np.clip(np.sum(input_mask_expanded, axis=1), a_min=1e-9, a_max=None)
        return sum_embeddings / sum_mask

    def encode(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)
            
        if self.use_onnx:
            all_embeddings = []
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i+batch_size]
                encoded_input = self.tokenizer(batch_texts, padding=True, truncation=True, return_tensors='np')
                
                ort_inputs = {
                    'input_ids': encoded_input['input_ids'].astype(np.int64),
                    'attention_mask': encoded_input['attention_mask'].astype(np.int64),
                    'token_type_ids': encoded_input['token_type_ids'].astype(np.int64)
                }
                
                ort_outs = self.session.run(['last_hidden_state', 'pooler_output'], ort_inputs)
                last_hidden_state = ort_outs[0]
                
                sentence_embeddings = self.mean_pooling(last_hidden_state, encoded_input['attention_mask'])
                
                # Normalize embeddings
                norms = np.linalg.norm(sentence_embeddings, axis=1, keepdims=True)
                sentence_embeddings = sentence_embeddings / np.clip(norms, a_min=1e-9, a_max=None)
                all_embeddings.extend(sentence_embeddings)
                
            return np.array(all_embeddings, dtype=np.float32)
        else:
            embeddings = self.model.encode(texts, batch_size=batch_size, normalize_embeddings=True, show_progress_bar=False)
            return embeddings.astype(np.float32)

    import functools
    @functools.lru_cache(maxsize=1000)
    def _encode_query_cached(self, query: str) -> np.ndarray:
        return self.encode([query])[0]

    def encode_query(self, query: str) -> np.ndarray:
        return self._encode_query_cached(query).copy()

class MockEmbeddingModel:
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        
    def encode(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)
            
        embeddings = []
        for text in texts:
            np.random.seed(abs(hash(text)) % (2**32))
            emb = np.random.randn(self.dimension)
            emb = emb / np.linalg.norm(emb)
            embeddings.append(emb)
            
        return np.array(embeddings, dtype=np.float32)

    import functools
    @functools.lru_cache(maxsize=1000)
    def _encode_query_cached(self, query: str) -> np.ndarray:
        return self.encode([query])[0]

    def encode_query(self, query: str) -> np.ndarray:
        return self._encode_query_cached(query).copy()
