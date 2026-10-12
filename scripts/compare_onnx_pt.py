import numpy as np
from sentence_transformers import SentenceTransformer
import onnxruntime as ort
from transformers import AutoTokenizer

def cosine_sim(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def mean_pooling(last_hidden_state, attention_mask):
    input_mask_expanded = np.expand_dims(attention_mask, -1)
    input_mask_expanded = np.broadcast_to(input_mask_expanded, last_hidden_state.shape)
    sum_embeddings = np.sum(last_hidden_state * input_mask_expanded, axis=1)
    sum_mask = np.clip(np.sum(input_mask_expanded, axis=1), a_min=1e-9, a_max=None)
    return sum_embeddings / sum_mask

def main():
    print("Loading PT Model...")
    pt_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    
    print("Loading ONNX Model...")
    tokenizer = AutoTokenizer.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
    session = ort.InferenceSession("all-MiniLM-L6-v2.onnx", providers=["CPUExecutionProvider"])
    
    queries = [
        "What is the impact of COVID-19 on global supply chains?",
        "How does machine learning improve medical diagnosis?",
        "quantum computing algorithms for factorization",
        "the role of artificial intelligence in autonomous vehicles",
        "climate change mitigation strategies using renewable energy",
        "scale document 42"
    ]
    
    print("\nComparing Embeddings:")
    for q in queries:
        pt_emb = pt_model.encode([q], normalize_embeddings=True)[0]
        
        encoded_input = tokenizer([q], padding=True, truncation=True, return_tensors='np')
        ort_inputs = {
            'input_ids': encoded_input['input_ids'].astype(np.int64),
            'attention_mask': encoded_input['attention_mask'].astype(np.int64),
            'token_type_ids': encoded_input['token_type_ids'].astype(np.int64)
        }
        ort_outs = session.run(['last_hidden_state', 'pooler_output'], ort_inputs)
        last_hidden_state = ort_outs[0]
        sentence_embeddings = mean_pooling(last_hidden_state, encoded_input['attention_mask'])
        
        norms = np.linalg.norm(sentence_embeddings, axis=1, keepdims=True)
        onnx_emb = (sentence_embeddings / np.clip(norms, a_min=1e-9, a_max=None))[0]
        
        sim = cosine_sim(pt_emb, onnx_emb)
        print(f"Query: '{q[:40]:<40}' -> Cosine Sim: {sim:.10f}")

if __name__ == '__main__':
    main()
