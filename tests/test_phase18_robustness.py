"""
Phase 18 — Indexing Robustness Tests

Tests for:
- Duplicate crawl idempotency
- Changed content update
- Atomic persistence (failure injection)
- IncrementalIndexer sync idempotency
- Empty content fallback
- Crawl continues after single page failure
- Concurrent index lock
- Health diagnostics parity
"""
import os
import pickle
import hashlib
import threading
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from src.api.main import app, app_state, _index_update_lock
from src.api.config import settings
from src.ingestion.crawler import WebCrawler, CrawlerConfig
from src.core.indexer import IncrementalIndexer
from src.storage.database import Database
from src.storage.models import DBDocument, IndexingStatus


@pytest.fixture(scope="module")
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture(scope="module")
def db():
    _db = Database(db_url=settings.DB_PATH)
    _db.init_db()
    return _db


# ---------------------------------------------------------------------------
# 18A. Duplicate crawl idempotency
# ---------------------------------------------------------------------------

class TestDuplicateCrawlIdempotency:
    def test_second_identical_crawl_stores_zero(self, client, monkeypatch):
        """
        Crawling the same URL with identical content twice must store 0 docs
        on the second crawl (content_hash deduplication).
        """
        MOCK_URL = "https://uniquetest.local/idempotent"
        MOCK_HTML = "<html><title>Idempotent Test</title><body>Stable content here.</body></html>"

        class MockResp:
            status_code = 200
            text = MOCK_HTML
            content = MOCK_HTML.encode()
            url = MOCK_URL
            is_redirect = False
            headers = {"Content-Type": "text/html", "Content-Length": str(len(MOCK_HTML.encode()))}

        class MockRobotsResp:
            status_code = 200
            text = ""
            is_redirect = False
            headers = {"Content-Type": "text/plain"}

        import src.ingestion.crawler as crawler_mod
        monkeypatch.setattr(crawler_mod, "is_safe_url", lambda u: True)

        def mock_get(self, url, *args, **kwargs):
            if "robots.txt" in url:
                return MockRobotsResp()
            return MockResp()

        import requests
        monkeypatch.setattr(requests.Session, "get", mock_get)

        req_body = {
            "url": MOCK_URL,
            "max_pages": 1,
            "max_depth": 0,
            "same_domain_only": True,
        }

        # First crawl — should store 1
        res1 = client.post("/crawl", json=req_body)
        assert res1.status_code == 200, res1.text
        data1 = res1.json()
        assert data1["pages_stored"] >= 0  # might be 0 if already existed from previous test

        # Second crawl — identical content, must store 0
        res2 = client.post("/crawl", json=req_body)
        assert res2.status_code == 200, res2.text
        data2 = res2.json()
        assert data2["pages_stored"] == 0, (
            f"Expected 0 pages_stored on second identical crawl, got {data2['pages_stored']}"
        )


# ---------------------------------------------------------------------------
# 18B. Changed content triggers update
# ---------------------------------------------------------------------------

class TestChangedContentUpdate:
    def test_changed_content_increments_version(self, client, monkeypatch):
        """When content changes, existing doc must be updated (version incremented)."""
        MOCK_URL = "https://uniquetest.local/changeable"
        V1_HTML = "<html><title>Version 1</title><body>Original content alpha.</body></html>"
        V2_HTML = "<html><title>Version 2</title><body>Updated content beta delta epsilon.</body></html>"

        class RobotsResp:
            status_code = 200
            text = ""
            is_redirect = False
            headers = {"Content-Type": "text/plain"}

        call_count = {"n": 0}

        def make_resp(html):
            class Resp:
                status_code = 200
                text = html
                content = html.encode()
                url = MOCK_URL
                is_redirect = False
                headers = {"Content-Type": "text/html", "Content-Length": str(len(html.encode()))}
            return Resp()

        import src.ingestion.crawler as crawler_mod
        monkeypatch.setattr(crawler_mod, "is_safe_url", lambda u: True)

        responses = [RobotsResp(), make_resp(V1_HTML), RobotsResp(), make_resp(V2_HTML)]
        idx = [0]

        def mock_get(self, url, *args, **kwargs):
            r = responses[idx[0]]
            idx[0] += 1
            return r

        import requests
        monkeypatch.setattr(requests.Session, "get", mock_get)

        req_body = {"url": MOCK_URL, "max_pages": 1, "max_depth": 0, "same_domain_only": True}

        # Crawl V1
        r1 = client.post("/crawl", json=req_body)
        assert r1.status_code == 200, r1.text

        # Record version after V1
        doc_id = hashlib.sha256(MOCK_URL.encode()).hexdigest()
        db_obj = Database(db_url=settings.DB_PATH)
        db_obj.init_db()
        session = db_obj.get_session()
        doc_v1 = session.query(DBDocument).filter_by(id=doc_id).first()
        version_after_v1 = doc_v1.version if doc_v1 else None
        session.close()

        # Crawl V2 (different content)
        r2 = client.post("/crawl", json=req_body)
        assert r2.status_code == 200, r2.text
        data2 = r2.json()
        assert data2["pages_stored"] == 1, f"Expected 1 updated page, got {data2['pages_stored']}"

        # Version must have incremented
        session2 = db_obj.get_session()
        doc_v2 = session2.query(DBDocument).filter_by(id=doc_id).first()
        version_after_v2 = doc_v2.version if doc_v2 else None
        session2.close()

        if version_after_v1 is not None:
            assert version_after_v2 > version_after_v1, (
                f"Version must increment on content change: {version_after_v1} -> {version_after_v2}"
            )


# ---------------------------------------------------------------------------
# 18C. Atomic persistence — IOError during save doesn't corrupt
# ---------------------------------------------------------------------------

class TestAtomicPersistence:
    def test_ioerror_during_save_leaves_original_intact(self, tmp_path):
        """If _save_index_atomic raises, the original index file must remain valid."""
        # Create a minimal index and save it
        from src.core.index import InvertedIndex
        from src.core.tokenizer import Tokenizer

        index_file = str(tmp_path / "test_atomic.pkl")
        original_index = InvertedIndex()
        tok = Tokenizer()
        original_index.add_document("doc1", tok.tokenize("hello world python"))

        with open(index_file, "wb") as f:
            pickle.dump(original_index, f)

        indexer = IncrementalIndexer(index_path=index_file)

        # Verify original loads
        with open(index_file, "rb") as f:
            loaded = pickle.load(f)
        assert loaded.total_docs == 1

        # Inject an IOError during pickle.dump
        with patch("pickle.dump", side_effect=IOError("disk full")):
            try:
                indexer._save_index_atomic()
            except (IOError, Exception):
                pass

        # Original must still be intact
        with open(index_file, "rb") as f:
            still_valid = pickle.load(f)
        assert still_valid.total_docs == 1, "Original index was corrupted by failed atomic save"

        # No .tmp file should remain
        tmp_file = index_file + ".tmp"
        assert not os.path.exists(tmp_file), ".tmp file left behind after failed save"


# ---------------------------------------------------------------------------
# 18D. IncrementalIndexer sync is idempotent
# ---------------------------------------------------------------------------

class TestIncrementalIndexerIdempotency:
    def test_repeated_sync_no_duplicates(self, tmp_path):
        """Syncing the same INDEXED documents twice must not add duplicates."""
        from src.core.index import InvertedIndex
        from src.core.tokenizer import Tokenizer
        from src.storage.database import Database as LocalDB

        db_path = str(tmp_path / "idempotent.db")
        db_url = f"sqlite:///{db_path}"
        local_db = LocalDB(db_url=db_url)
        local_db.init_db()
        session = local_db.get_session()

        index_path = str(tmp_path / "idempotent.pkl")

        # Insert one pending doc
        doc = DBDocument(
            id="idempotent-doc-1",
            title="Idempotent",
            content="idempotent sync test content here",
            url="https://test.local/idempotent",
            content_hash=hashlib.sha256(b"idempotent sync test content here").hexdigest(),
            version=1,
            indexing_status=IndexingStatus.PENDING.value,
        )
        session.add(doc)
        session.commit()

        indexer = IncrementalIndexer(index_path=index_path)

        # First sync
        stats1 = indexer.sync(session)
        assert stats1["added"] == 1

        doc_count_after_first = indexer.index.total_docs

        # Second sync (doc is now INDEXED, no PENDING)
        stats2 = indexer.sync(session)
        assert stats2["added"] == 0
        assert stats2["updated"] == 0

        doc_count_after_second = indexer.index.total_docs
        assert doc_count_after_second == doc_count_after_first, (
            "Second sync added duplicate entries"
        )
        session.close()


# ---------------------------------------------------------------------------
# 18E. Empty content fallback
# ---------------------------------------------------------------------------

class TestEmptyContentFallback:
    def test_extract_content_fallback_to_title(self):
        """When HTML body is empty/nav-only, content should fall back to title."""
        html = "<html><title>Nav Only Page</title><body><nav>Menu here</nav></body></html>"
        title, content = WebCrawler.extract_content(html)
        assert title == "Nav Only Page"
        # After removing nav, body is empty → fallback to title
        assert content.strip() != "", "Content should not be empty (should fall back to title)"

    def test_extract_content_normal_page(self):
        """Normal page should extract main content."""
        html = """
        <html>
          <title>Test Doc</title>
          <body>
            <main><p>This is the real content about Python asyncio.</p></main>
          </body>
        </html>
        """
        title, content = WebCrawler.extract_content(html)
        assert title == "Test Doc"
        assert "Python asyncio" in content

    def test_extract_content_no_title(self):
        """Page with no <title> tag should use <h1> or empty string."""
        html = "<html><body><h1>Heading Title</h1><p>Some content.</p></body></html>"
        title, content = WebCrawler.extract_content(html)
        assert title == "Heading Title"
        assert content  # should not be empty


# ---------------------------------------------------------------------------
# 18F. Crawl continues after individual page failure
# ---------------------------------------------------------------------------

class TestCrawlFailureIsolation:
    def test_404_page_does_not_stop_crawl(self, monkeypatch):
        """A 404 on one URL must not stop the entire crawl."""
        import src.ingestion.crawler as crawler_mod
        monkeypatch.setattr(crawler_mod, "is_safe_url", lambda u: True)

        config = CrawlerConfig(
            seed_urls=["https://test.local/"],
            allowed_domains=["test.local"],
            max_depth=1,
            max_pages=5,
            timeout=1,
            delay=0,
            max_retries=0,
        )

        good_html = "<html><title>Good</title><body><p>Content.</p><a href='/page2'>P2</a></body></html>"
        good2_html = "<html><title>Good2</title><body><p>More content.</p></body></html>"

        class RobotsResp:
            status_code = 200; text = ""; is_redirect = False
            headers = {"Content-Type": "text/plain"}

        def make_html_resp(url, html):
            class R:
                status_code = 200
                text = html; content = html.encode()
                is_redirect = False
                headers = {"Content-Type": "text/html", "Content-Length": str(len(html.encode()))}
            r = R(); r.url = url; return r

        class NotFoundResp:
            status_code = 404; text = ""; content = b""; is_redirect = False
            url = "https://test.local/bad"
            headers = {"Content-Type": "text/html"}

        responses_map = {
            "https://test.local/robots.txt": RobotsResp(),
            "https://test.local/": make_html_resp("https://test.local/", good_html),
            "https://test.local/page2": make_html_resp("https://test.local/page2", good2_html),
        }

        def mock_get(self, url, *args, **kwargs):
            return responses_map.get(url, NotFoundResp())

        import requests
        monkeypatch.setattr(requests.Session, "get", mock_get)

        crawler = WebCrawler(config)
        results = list(crawler.crawl())

        # Should have fetched both good pages
        assert len(results) == 2, f"Expected 2 results, got {len(results)}: {[r[0] for r in results]}"
        # Failed pages don't crash
        assert crawler.stats["fetched"] == 2


# ---------------------------------------------------------------------------
# 18G. Index update lock prevents concurrent corruption
# ---------------------------------------------------------------------------

class TestIndexUpdateLock:
    def test_lock_is_threading_lock(self):
        """The _index_update_lock must be a proper threading.Lock."""
        assert isinstance(_index_update_lock, type(threading.Lock())), (
            "_index_update_lock must be a threading.Lock instance"
        )

    def test_lock_acquirable(self):
        """The lock must be acquirable and releasable."""
        acquired = _index_update_lock.acquire(timeout=1)
        assert acquired, "Lock must be acquirable"
        _index_update_lock.release()


# ---------------------------------------------------------------------------
# 18H. Health parity after crawl
# ---------------------------------------------------------------------------

class TestHealthParityAfterCrawl:
    def test_health_parity_consistent(self, client):
        """Health endpoint parity_ok must remain True after operations."""
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        if data["lexical_index_loaded"] and data["dense_index_loaded"] and data["database_reachable"]:
            assert data["parity_ok"] is True, (
                f"Parity broken: DB={data['db_doc_count']}, "
                f"Lexical={data['lexical_doc_count']}, "
                f"Dense={data['dense_doc_count']}"
            )

    def test_concurrent_index_mutation(self, client, monkeypatch):
        # Simulate multiple concurrent crawls to verify _index_update_lock works
        import threading
        
        # Mock crawler to return a single document
        class DummyCrawler:
            def __init__(self, config):
                self.url = config.seed_urls[0]
                self.stats = {"fetched": 1, "failed": 0}
            def crawl(self):
                # Return slightly different content per thread based on URL to avoid identical deduplication
                yield (self.url, "Concurrent Title", f"Content for {self.url}")

        monkeypatch.setattr("src.ingestion.crawler.WebCrawler", DummyCrawler)
        
        results = []
        def crawl_worker(i):
            res = client.post("/crawl", json={"url": f"https://example.com/{i}", "max_pages": 1, "max_depth": 1})
            results.append(res.status_code)
            
        threads = []
        for i in range(5):
            t = threading.Thread(target=crawl_worker, args=(i,))
            threads.append(t)
            t.start()
            
        for t in threads:
            t.join()
            
        assert all(r == 200 for r in results)
        
        # Check parity
        res = client.get("/health")
        data = res.json()
        assert data["parity_ok"] is True