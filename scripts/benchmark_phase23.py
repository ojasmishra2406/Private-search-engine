import time
import requests
import statistics

API_URL = "http://127.0.0.1:8000"

def measure_latency(endpoint, params):
    start = time.perf_counter()
    resp = requests.get(f"{API_URL}{endpoint}", params=params)
    resp.raise_for_status()
    duration = time.perf_counter() - start
    return duration

def benchmark():
    print("========================================")
    print("      PHASE 23 PERFORMANCE BENCHMARK    ")
    print("========================================\n")
    
    # Check health and startup time surrogate
    print("[1/5] Checking API Health...")
    t0 = time.perf_counter()
    health_resp = requests.get(f"{API_URL}/health")
    health_time = time.perf_counter() - t0
    if health_resp.status_code == 200:
        health_data = health_resp.json()
        print(f"      Health Check Latency : {health_time * 1000:.2f} ms")
        print(f"      Status             : {health_data['status']}")
        print(f"      Lexical Docs       : {health_data['lexical_doc_count']}")
        print(f"      Dense Docs         : {health_data['dense_doc_count']}")
    else:
        print("      API is unreachable.")
        return

    queries = [
        "python coroutines",
        "asyncio.run()",
        "how does garbage collection work",
        "__init__ method",
        "C++ extensions",
        "PEP 8",
        "def",
        "class MyClass:",
        "exception handling",
        "import sys"
    ]
    
    endpoints = [
        "/search",
        "/dense-search",
        "/hybrid-search",
        "/reranked-search"
    ]
    
    print("\n[2/5] Benchmarking Search Endpoints...")
    for endpoint in endpoints:
        latencies = []
        for q in queries:
            try:
                lat = measure_latency(endpoint, {"q": q, "top_k": 10})
                latencies.append(lat * 1000)
            except Exception as e:
                print(f"Error on {endpoint}: {e}")
        
        if latencies:
            latencies.sort()
            mean_lat = statistics.mean(latencies)
            median_lat = statistics.median(latencies)
            p95 = latencies[int(len(latencies) * 0.95)]
            p99 = latencies[int(len(latencies) * 0.99)] if len(latencies) >= 100 else p95
            
            print(f"      Endpoint: {endpoint}")
            print(f"        Mean   : {mean_lat:.2f} ms")
            print(f"        Median : {median_lat:.2f} ms")
            print(f"        p95    : {p95:.2f} ms")
            print(f"        p99    : {p99:.2f} ms")

    print("\n========================================")
    print("              COMPLETE                  ")
    print("========================================")

if __name__ == "__main__":
    benchmark()
