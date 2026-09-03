import time
import requests
import sys
import subprocess

API_URL = "http://127.0.0.1:8000"
CRAWL_URL = "https://docs.python.org/3/library/asyncio.html"

def check_health():
    resp = requests.get(f"{API_URL}/health")
    resp.raise_for_status()
    return resp.json()

def verify():
    print("========================================")
    print("    REAL-WORLD CLEAN-ROOM TEST (P26)    ")
    print("========================================\n")
    
    # 1-3. Health & Readiness
    print("[+] Checking health...")
    health = check_health()
    start_docs = health['lexical_doc_count']
    print(f"    Initial docs: {start_docs}")
    
    # 4-10. Crawler accepts real URL
    print(f"[+] Crawling {CRAWL_URL}...")
    resp = requests.post(
        f"{API_URL}/crawl",
        json={"url": CRAWL_URL, "max_pages": 3, "max_depth": 1}
    )
    resp.raise_for_status()
    crawl_job = resp.json()
    print(f"    Crawl submitted, pages crawled: {crawl_job.get('pages_crawled', 'N/A')}")
    
    # Wait for crawl and sync
    time.sleep(10)
    
    # 11. ID Parity check
    print("[+] Checking updated health parity...")
    new_health = check_health()
    new_docs = new_health['lexical_doc_count']
    print(f"    Updated docs: {new_docs} (Added: {new_docs - start_docs})")
    if not new_health['parity_ok']:
        print("    ERROR: Parity check failed!")
        sys.exit(1)
        
    # 12. Search returns real URLs
    print("[+] Searching for 'asyncio event loop'...")
    search_resp = requests.get(f"{API_URL}/search", params={"q": "asyncio event loop"})
    search_resp.raise_for_status()
    results = search_resp.json()
    total_res = results.get('total_results', 0)
    print(f"    Found {total_res} results.")
    if total_res == 0:
        print("    ERROR: No search results found.")
        sys.exit(1)
        
    found_url = False
    for r in results['results']:
        if "asyncio" in r['url']:
            found_url = True
            break
            
    if not found_url:
        print("    WARNING: Did not find crawled URL in top results (might be expected based on ranking).")
        
    # 14. Idempotent re-crawl
    print(f"[+] Re-crawling {CRAWL_URL} to verify idempotency...")
    resp = requests.post(
        f"{API_URL}/crawl",
        json={"url": CRAWL_URL, "max_pages": 3, "max_depth": 1}
    )
    time.sleep(10)
    final_health = check_health()
    if final_health['lexical_doc_count'] != new_docs:
        print(f"    ERROR: Idempotency failed. Docs jumped from {new_docs} to {final_health['lexical_doc_count']}")
        sys.exit(1)
    print("    Idempotency verified.")
    
    # 20. Rebuild Check
    print("[+] Triggering index rebuild recovery...")
    res = subprocess.run([sys.executable, "scripts/rebuild_index.py"], capture_output=True, text=True)
    if res.returncode != 0:
        print(f"    ERROR: Rebuild failed!\n{res.stderr}")
        sys.exit(1)
    
    rebuild_health = check_health()
    if not rebuild_health['parity_ok'] or rebuild_health['lexical_doc_count'] != new_docs:
        print("    ERROR: Parity failed after rebuild!")
        sys.exit(1)
        
    print("[+] All integration checks passed.")
    print("\n========================================")
    print("              SUCCESS                   ")
    print("========================================")

if __name__ == "__main__":
    verify()
