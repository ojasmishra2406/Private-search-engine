import logging
import time
import urllib.parse
import urllib.robotparser
import socket
import ipaddress
from collections import deque
from dataclasses import dataclass, field
from typing import Set, List, Dict, Optional, Tuple, Iterator

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

DEFAULT_MAX_DOC_SIZE = 5 * 1024 * 1024  # 5 MB

def is_safe_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
            return False
        return True
    except ValueError:
        return False

def is_safe_url(url: str) -> bool:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in ("http", "https"):
        return False
    hostname = parsed.hostname
    if not hostname:
        return False
        
    try:
        addrinfo = socket.getaddrinfo(hostname, None)
        for result in addrinfo:
            ip = result[4][0]
            if not is_safe_ip(ip):
                return False
        return True
    except socket.gaierror:
        return False

@dataclass
class CrawlerConfig:
    seed_urls: List[str]
    allowed_domains: List[str]
    max_depth: int = 3
    max_pages: int = 50
    timeout: int = 5
    delay: float = 1.0       # seconds between requests to same domain
    user_agent: str = "PrivateSearchBot/1.0"
    max_retries: int = 3
    max_doc_size: int = DEFAULT_MAX_DOC_SIZE  # bytes
    same_domain_only: bool = True

class WebCrawler:
    def __init__(self, config: CrawlerConfig):
        self.config = config
        self.visited_urls: Set[str] = set()
        self.frontier = deque()  # (url, depth)
        self.robots_parsers: Dict[str, urllib.robotparser.RobotFileParser] = {}
        self.last_request_time: Dict[str, float] = {}
        self.stats = {
            "fetched": 0,
            "failed": 0,
            "rejected": 0,
            "discovered": 0,
            "duplicates_avoided": 0,
        }

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": config.user_agent})

        for seed in self.config.seed_urls:
            normalized = self.normalize_url(seed)
            if self.is_allowed_domain(normalized) and is_safe_url(normalized):
                self.frontier.append((normalized, 0))

    def normalize_url(self, url: str) -> str:
        """Removes fragments and trailing slashes, lowercases the domain."""
        parsed = urllib.parse.urlsplit(url)
        netloc = parsed.netloc.lower()
        path = parsed.path
        if path.endswith('/') and len(path) > 1:
            path = path[:-1]
        elif not path:
            path = '/'
        return urllib.parse.urlunsplit(
            (parsed.scheme, netloc, path, parsed.query, "")
        )

    def is_allowed_domain(self, url: str) -> bool:
        if not self.config.same_domain_only:
            return True
        parsed = urllib.parse.urlsplit(url)
        netloc = parsed.netloc.lower()
        return any(
            netloc == d or netloc.endswith("." + d)
            for d in self.config.allowed_domains
        )

    def can_fetch(self, url: str) -> bool:
        parsed = urllib.parse.urlsplit(url)
        netloc = parsed.netloc
        scheme = parsed.scheme

        if netloc not in self.robots_parsers:
            rp = urllib.robotparser.RobotFileParser()
            robots_url = f"{scheme}://{netloc}/robots.txt"
            rp.set_url(robots_url)
            try:
                # SSRF protection for robots.txt too
                if is_safe_url(robots_url):
                    resp = self.session.get(robots_url, timeout=self.config.timeout)
                    if resp.status_code == 200:
                        rp.parse(resp.text.splitlines())
                    elif resp.status_code in (401, 403):
                        rp.disallow_all = True
                    else:
                        rp.allow_all = True
            except Exception as e:
                logger.warning("Failed to fetch robots.txt for %s: %s", netloc, e)
                rp.allow_all = True
            self.robots_parsers[netloc] = rp

        return self.robots_parsers[netloc].can_fetch(self.config.user_agent, url)

    def _wait_for_rate_limit(self, url: str):
        netloc = urllib.parse.urlsplit(url).netloc
        now = time.time()
        if netloc in self.last_request_time:
            elapsed = now - self.last_request_time[netloc]
            if elapsed < self.config.delay:
                time.sleep(self.config.delay - elapsed)
        self.last_request_time[netloc] = time.time()

    def fetch_page(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        if not is_safe_url(url):
            self.stats["rejected"] += 1
            return None, None
            
        retries = 0
        redirect_count = 0
        while retries <= self.config.max_retries:
            self._wait_for_rate_limit(url)
            try:
                resp = self.session.get(
                    url,
                    timeout=self.config.timeout,
                    allow_redirects=False # Manually handle redirects to enforce SSRF
                )
                
                if resp.is_redirect:
                    redirect_count += 1
                    if redirect_count > 5:
                        logger.warning("Redirect loop detected for %s", url)
                        self.stats["failed"] += 1
                        return None, None
                    next_url = resp.headers.get("Location")
                    if not next_url:
                        return None, None
                    next_url = urllib.parse.urljoin(url, next_url)
                    if not is_safe_url(next_url):
                        logger.warning("Blocked unsafe redirect to %s", next_url)
                        return None, None
                    url = next_url
                    continue

                if resp.status_code == 200:
                    content_type = resp.headers.get("Content-Type", "").lower()
                    if "text/html" not in content_type:
                        logger.info("Rejected non-HTML %s", url)
                        self.stats["rejected"] += 1
                        return None, None

                    content_length_str = resp.headers.get("Content-Length")
                    if content_length_str is not None:
                        try:
                            cl = int(content_length_str)
                            if cl > self.config.max_doc_size:
                                logger.info("Rejected oversized page (%d bytes) %s", cl, url)
                                self.stats["rejected"] += 1
                                return None, None
                        except ValueError:
                            pass

                    if len(resp.content) > self.config.max_doc_size:
                        logger.info("Rejected oversized page (body %d bytes) %s", len(resp.content), url)
                        self.stats["rejected"] += 1
                        return None, None

                    return resp.text, resp.url

                elif resp.status_code in (429, 500, 502, 503, 504):
                    retries += 1
                    time.sleep(2 ** retries)
                else:
                    self.stats["failed"] += 1
                    return None, None

            except requests.RequestException as e:
                logger.warning("Request failed for %s: %s", url, e)
                retries += 1
                time.sleep(2 ** retries)

        self.stats["failed"] += 1
        return None, None

    def extract_links(self, html: str, base_url: str) -> List[str]:
        soup = BeautifulSoup(html, "html.parser")
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.lower().startswith(("javascript:", "mailto:", "tel:", "#")):
                continue
            absolute_url = urllib.parse.urljoin(base_url, href)
            links.append(absolute_url)
        return links

    @staticmethod
    def extract_canonical_url(html: str, base_url: str) -> Optional[str]:
        soup = BeautifulSoup(html, "html.parser")
        tag = soup.find("link", rel=lambda r: r and "canonical" in r)
        if tag and tag.get("href"):
            href = tag["href"].strip()
            if href:
                return urllib.parse.urljoin(base_url, href)
        return None

    @staticmethod
    def extract_content(html: str) -> Tuple[str, str]:
        soup = BeautifulSoup(html, "html.parser")
        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        elif soup.find("h1"):
            title = soup.find("h1").get_text(strip=True)
            
        # Remove scripts, styles, navs
        for tag in soup(["script", "style", "noscript", "template", "nav", "header", "footer"]):
            tag.decompose()
            
        main = soup.find("main") or soup.find("div", class_="body") or soup.find("article") or soup.body
        content = main.get_text(separator=" ", strip=True) if main else ""
        
        # Normalize whitespace
        content = " ".join(content.split())
        # Fallback: if content is empty after extraction, use title so we don't index empty docs
        if not content.strip():
            content = title
        return title, content

    def crawl(self) -> Iterator[Tuple[str, str, str]]:
        """
        Yields (url, title, content)
        """
        while self.frontier and self.stats["fetched"] < self.config.max_pages:
            url, depth = self.frontier.popleft()

            if url in self.visited_urls:
                continue

            self.visited_urls.add(url)

            if not self.can_fetch(url):
                logger.info("Robots.txt rejected %s", url)
                self.stats["rejected"] += 1
                continue

            html, final_url = self.fetch_page(url)
            if not html or not final_url:
                continue

            self.stats["fetched"] += 1

            normalized_final = self.normalize_url(final_url)
            self.visited_urls.add(normalized_final)

            canonical_url = self.extract_canonical_url(html, normalized_final)
            if canonical_url and is_safe_url(canonical_url):
                canonical_url = self.normalize_url(canonical_url)
            else:
                canonical_url = normalized_final
                
            self.visited_urls.add(canonical_url)

            title, content = self.extract_content(html)
            
            yield canonical_url, title, content

            if depth < self.config.max_depth:
                links = self.extract_links(html, canonical_url)
                for link in links:
                    norm_link = self.normalize_url(link)
                    if not is_safe_url(norm_link):
                        continue
                        
                    self.stats["discovered"] += 1
                    if norm_link not in self.visited_urls and self.is_allowed_domain(norm_link):
                        self.frontier.append((norm_link, depth + 1))
                    else:
                        if norm_link in self.visited_urls:
                            self.stats["duplicates_avoided"] += 1
