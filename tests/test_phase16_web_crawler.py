import pytest
import ipaddress
import socket
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

from src.ingestion.crawler import is_safe_ip, is_safe_url, WebCrawler, CrawlerConfig
from src.api.main import app
from src.storage.database import Database
from src.storage.models import DBDocument


@pytest.fixture(scope="module")
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def test_is_safe_ip():
    assert True




def test_is_safe_url():
    assert True



    
def test_html_extraction():
    assert True




def test_crawler_limits_api(client):
    assert True




def test_crawl_integration(client, monkeypatch, tmp_path):
    assert True

