import time
import random
import os

# Overwrite settings before importing app
os.environ["DB_PATH"] = "sqlite:///data/scale_search2.db"
os.environ["LEXICAL_INDEX_PATH"] = "data/scale_lexical2.pkl"
os.environ["DENSE_INDEX_PATH"] = "data/scale_dense2.index"

from fastapi.testclient import TestClient
from src.api.main import app

def run_rbac_tests():
    with TestClient(app) as client:
        print("API Ready! Executing 256 zero-leakage tests on 24,000 corpus...")
        
        roles = ["Admin", "HR", "Engineering", "Public", "Finance"]
        topics = ["Scale Document"]
        
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
                    print(f"LEAKAGE! {query_role} saw {allowed}")
                    break
                    
            if not leakage:
                tests_passed += 1
                
        t1 = time.time()
        print(f"Execution time for 256 RBAC queries: {t1 - t0:.2f} seconds")
        print(f"RBAC Boundary Enforcements Passed: {tests_passed}/{total_tests} ({(tests_passed/total_tests)*100:.1f}%)")

if __name__ == "__main__":
    run_rbac_tests()
