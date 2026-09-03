import urllib.request
import json
import time
import subprocess

def wait_for_health():
    print('Waiting for health...')
    while True:
        try:
            res = urllib.request.urlopen('http://localhost:8000/health')
            if res.getcode() == 200:
                print('Health OK')
                break
        except Exception:
            pass
        time.sleep(5)

def crawl():
    print('Crawling...')
    req = urllib.request.Request(
        'http://localhost:8000/crawl', 
        data=json.dumps({'url':'https://docs.pytest.org/en/stable/','max_pages':10,'max_depth':2,'same_domain_only':True}).encode('utf-8'), 
        headers={'Content-Type': 'application/json'}
    )
    res = urllib.request.urlopen(req)
    print(res.read().decode('utf-8'))

def search():
    print('Searching...')
    req = urllib.request.Request('http://localhost:8000/search?q=pytest&top_k=2')
    res = urllib.request.urlopen(req)
    print(res.read().decode('utf-8'))

wait_for_health()
crawl()
search()
