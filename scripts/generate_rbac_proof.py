import time
import random
from fastapi.testclient import TestClient
from src.api.main import app
from src.api.config import settings
from src.storage.database import Database
from src.storage.models import DBDocument, Base
from src.core.indexer import IncrementalIndexer
from src.dense.vector_index import VectorIndex
from src.dense.embeddings import EmbeddingModel
from src.dense.indexer import DenseIndexer
import tempfile

def generate_rbac_test_data():
    docs = []
    roles = ["Admin", "HR", "Engineering", "Public", "Finance"]
    topics = ["bonus", "architecture", "holiday", "layoff", "revenue", "roadmap", "cafeteria"]
    
    for i in range(100):
        role = random.choice(roles)
        topic = random.choice(topics)
        docs.append(DBDocument(
            id=f"doc_{i}",
            int_id=i,
            url=f"http://internal/{i}",
            title=f"Topic: {topic}",
            content=f"Detailed confidential document about {topic} for {role} only.",
            content_hash=f"hash_{i}",
            allowed_roles=role,
            indexing_status="PENDING"
        ))
    return docs

def run_256_rbac_tests():
    print("--- BENCHMARK: 256 RBAC BOUNDARY TESTS ---")
    
    temp_dir = tempfile.mkdtemp()
    settings.DB_PATH = f"sqlite:///{temp_dir}/test_rbac.db"
    settings.LEXICAL_INDEX_PATH = f"{temp_dir}/test_rbac_index.pkl"
    settings.DENSE_INDEX_PATH = f"{temp_dir}/test_rbac_dense.index"
    
    db = Database(settings.DB_PATH)
    Base.metadata.create_all(db.engine)
    session = db.get_session()
    
    docs = generate_rbac_test_data()
    session.bulk_save_objects(docs)
    session.commit()
    
    indexer = IncrementalIndexer(settings.LEXICAL_INDEX_PATH)
    v_idx = VectorIndex(index_path=settings.DENSE_INDEX_PATH)
    emb_model = EmbeddingModel(settings.DENSE_MODEL_NAME)
    dense_indexer = DenseIndexer(emb_model, v_idx, batch_size=32)
    indexer.sync(session, dense_indexer=dense_indexer)
    
    # Must use 'with' to trigger FastAPI lifespan
    with TestClient(app) as client:
        print("API Ready! Executing 256 zero-leakage tests...")
        
        roles = ["Admin", "HR", "Engineering", "Public", "Finance"]
        topics = ["bonus", "architecture", "holiday", "layoff", "revenue", "roadmap", "cafeteria"]
        
        tests_passed = 0
        total_tests = 256
        
        t0 = time.time()
        
        for i in range(total_tests):
            query_role = random.choice(roles)
            query_topic = random.choice(topics)
            
            res = client.get(f"/reranked-search?q={query_topic}&role={query_role}&top_k=50")
            if res.status_code != 200:
                print(f"Test Failed: status {res.status_code}")
                continue
                
            data = res.json()
            
            leakage = False
            for r in data.get('results', []):
                allowed = r.get('allowed_roles', 'Public')
                if allowed != query_role and allowed != "Public" and query_role != "Admin":
                    leakage = True
                    break
                    
            if not leakage:
                tests_passed += 1
                
        t1 = time.time()
        print(f"Execution time for 256 RBAC queries: {t1 - t0:.2f} seconds")
        print(f"RBAC Boundary Enforcements Passed: {tests_passed}/{total_tests} ({(tests_passed/total_tests)*100:.1f}%)")

if __name__ == "__main__":
    with open("docs/proofs/rbac_256_tests_proof.txt", "w") as f:
        import sys
        sys.stdout = f
        run_256_rbac_tests()
        sys.stdout = sys.__stdout__
    print("Proof generated: docs/proofs/rbac_256_tests_proof.txt")
