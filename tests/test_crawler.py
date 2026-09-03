import src.ingestion.crawler as crawler_mod
import pytest
from unittest.mock import patch, MagicMock
from src.ingestion.crawler import WebCrawler, CrawlerConfig


@pytest.fixture(autouse=True)
def patch_is_safe_url(monkeypatch):
    monkeypatch.setattr(crawler_mod, 'is_safe_url', lambda u: True)

@pytest.fixture
def config():
    return CrawlerConfig(
        seed_urls=["http://docs.python.org/3/"],
        allowed_domains=["docs.python.org"],
        max_depth=1,
        max_pages=5,
        timeout=1,
        delay=0,
        max_retries=1,
    )


# ---------------------------------------------------------------------------
# URL utilities
# ---------------------------------------------------------------------------

def test_url_normalization(config):
    crawler = WebCrawler(config)

    assert crawler.normalize_url("http://Example.com/Path/") == "http://example.com/Path"
    assert crawler.normalize_url("https://example.com#fragment") == "https://example.com/"
    assert crawler.normalize_url("http://example.com?q=1#frag") == "http://example.com/?q=1"


def test_is_allowed_domain(config):
    crawler = WebCrawler(config)
    assert crawler.is_allowed_domain("http://docs.python.org/3/") is True
    assert crawler.is_allowed_domain("https://sub.docs.python.org/") is True
    assert crawler.is_allowed_domain("http://evil.com/") is False
    assert crawler.is_allowed_domain("http://python.org/") is False


# ---------------------------------------------------------------------------
# Canonical URL extraction
# ---------------------------------------------------------------------------

def test_extract_canonical_url_present(config):
    """extract_canonical_url returns the canonical href when present."""
    crawler = WebCrawler(config)
    html = (
        '<html><head>'
        '<link rel="canonical" href="https://docs.python.org/3/index.html"/>'
        '</head><body></body></html>'
    )
    result = crawler.extract_canonical_url(html, "http://docs.python.org/3/")
    assert result == "https://docs.python.org/3/index.html"


def test_extract_canonical_url_absent(config):
    """extract_canonical_url returns None when no canonical tag exists."""
    crawler = WebCrawler(config)
    html = "<html><head></head><body></body></html>"
    assert crawler.extract_canonical_url(html, "http://docs.python.org/3/") is None


def test_extract_canonical_url_relative(config):
    """Relative canonical hrefs are resolved against the base URL."""
    crawler = WebCrawler(config)
    html = '<html><head><link rel="canonical" href="index.html"/></head><body></body></html>'
    result = crawler.extract_canonical_url(html, "http://docs.python.org/3/")
    assert result == "http://docs.python.org/3/index.html"


# ---------------------------------------------------------------------------
# Document size limit
# ---------------------------------------------------------------------------

def test_oversized_document_rejected_via_content_length(config):
    """Pages advertised as too large via Content-Length must be rejected."""
    config.max_doc_size = 100  # very small limit for test

    crawler = WebCrawler(config)

    mock_resp = MagicMock()
    mock_resp.is_redirect = False
    mock_resp.status_code = 200
    mock_resp.headers = {"Content-Type": "text/html", "Content-Length": "9999"}

    with patch.object(crawler.session, 'get', return_value=mock_resp):
        html, url = crawler.fetch_page("http://docs.python.org/3/")

    assert html is None
    assert crawler.stats["rejected"] == 1


def test_oversized_document_rejected_via_body(config):
    """Pages with no Content-Length but oversized body must be rejected."""
    config.max_doc_size = 10

    crawler = WebCrawler(config)

    mock_resp = MagicMock()
    mock_resp.is_redirect = False
    mock_resp.status_code = 200
    mock_resp.headers = {"Content-Type": "text/html"}  # no Content-Length
    mock_resp.content = b"x" * 9999
    mock_resp.text = "x" * 9999

    with patch.object(crawler.session, 'get', return_value=mock_resp):
        html, url = crawler.fetch_page("http://docs.python.org/3/")

    assert html is None
    assert crawler.stats["rejected"] == 1


# ---------------------------------------------------------------------------
# Crawl happy path
# ---------------------------------------------------------------------------

@patch('urllib.robotparser.RobotFileParser.can_fetch', return_value=True)
def test_successful_fetch(mock_can_fetch, config):
    mock_resp_robots = MagicMock()
    mock_resp_robots.status_code = 200
    mock_resp_robots.text = ""

    mock_resp = MagicMock()
    mock_resp.is_redirect = False
    mock_resp.status_code = 200
    mock_resp.headers = {"Content-Type": "text/html; charset=utf-8"}
    # No Content-Length → fallback body-size check
    mock_resp.content = b"<html><body><a href='/link'>link</a></body></html>"
    mock_resp.text    = "<html><body><a href='/link'>link</a></body></html>"
    mock_resp.url     = "http://docs.python.org/3/"

    config.max_pages = 1
    crawler = WebCrawler(config)

    with patch.object(crawler.session, 'get', side_effect=[mock_resp_robots, mock_resp]):
        results = list(crawler.crawl())

    assert len(results) == 1
    assert results[0][0] == "http://docs.python.org/3"
    assert "link" in results[0][2]
    # crawl() now yields 3-tuple (url, html, canonical_url)
    
    assert len(crawler.frontier) == 1
    assert crawler.frontier[0][0] == "http://docs.python.org/link"


@patch('urllib.robotparser.RobotFileParser.can_fetch', return_value=True)
def test_non_html_rejection(mock_can_fetch, config):
    mock_resp_robots = MagicMock()
    mock_resp_robots.status_code = 200
    mock_resp_robots.text = ""

    mock_resp = MagicMock()
    mock_resp.is_redirect = False
    mock_resp.status_code = 200
    mock_resp.headers = {"Content-Type": "application/pdf"}

    crawler = WebCrawler(config)

    with patch.object(crawler.session, 'get', side_effect=[mock_resp_robots, mock_resp]):
        results = list(crawler.crawl())

    assert len(results) == 0
    assert crawler.stats["rejected"] == 1


@patch('urllib.robotparser.RobotFileParser.can_fetch', return_value=True)
def test_retry_on_5xx(mock_can_fetch, config):
    mock_resp_robots = MagicMock()
    mock_resp_robots.status_code = 200
    mock_resp_robots.text = ""

    mock_resp_500 = MagicMock()
    mock_resp_500.is_redirect = False
    mock_resp_500.status_code = 500

    mock_resp_200 = MagicMock()
    mock_resp_200.is_redirect = False
    mock_resp_200.status_code = 200
    mock_resp_200.headers = {"Content-Type": "text/html"}
    mock_resp_200.content = b"<html></html>"
    mock_resp_200.text    = "<html></html>"
    mock_resp_200.url     = "http://docs.python.org/3/"

    crawler = WebCrawler(config)

    with patch('time.sleep'), \
         patch.object(crawler.session, 'get',
                      side_effect=[mock_resp_robots, mock_resp_500, mock_resp_200]) as mock_get:
        results = list(crawler.crawl())

    assert len(results) == 1
    assert mock_get.call_count == 3


@patch('urllib.robotparser.RobotFileParser.can_fetch', return_value=True)
def test_discard_on_404(mock_can_fetch, config):
    mock_resp_robots = MagicMock()
    mock_resp_robots.status_code = 200
    mock_resp_robots.text = ""

    mock_resp_404 = MagicMock()
    mock_resp_404.is_redirect = False
    mock_resp_404.status_code = 404

    crawler = WebCrawler(config)

    with patch.object(crawler.session, 'get',
                      side_effect=[mock_resp_robots, mock_resp_404]):
        results = list(crawler.crawl())

    assert len(results) == 0
    assert crawler.stats["failed"] == 1


def test_robots_rejection(config):
    with patch('urllib.robotparser.RobotFileParser.can_fetch', return_value=False):
        crawler = WebCrawler(config)
        results = list(crawler.crawl())

    assert len(results) == 0
    assert crawler.stats["rejected"] == 1


def test_duplicate_url_prevention(config):
    crawler = WebCrawler(config)
    crawler.visited_urls.add(crawler.normalize_url("http://docs.python.org/3/"))
    crawler.frontier.append((crawler.normalize_url("http://docs.python.org/3/"), 0))

    results = list(crawler.crawl())
    assert len(results) == 0


# ---------------------------------------------------------------------------
# Connection pooling
# ---------------------------------------------------------------------------

def test_session_object_exists(config):
    """WebCrawler must initialise a requests.Session for connection pooling."""
    import requests
    crawler = WebCrawler(config)
    assert isinstance(crawler.session, requests.Session)


def test_session_has_user_agent_header(config):
    """The session must carry the configured user-agent header."""
    crawler = WebCrawler(config)
    assert crawler.session.headers.get("User-Agent") == config.user_agent
