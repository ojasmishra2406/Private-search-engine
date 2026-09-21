import logging
import time
import urllib.parse
import urllib.robotparser
import socket
import ipaddress
import asyncio
from typing import Set, List, Dict, Optional, Tuple, Iterator

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

DEFAULT_MAX_DOC_SIZE = 5 * 1024 * 1024

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

from dataclasses import dataclass, field
@dataclass
class CrawlerConfig:
    seed_urls: List[str]
    allowed_domains: List[str]
    max_depth: int = 3
    max_pages: int = 50
    timeout: int = 5
    delay: float = 0.0 # delay not really needed with semaphore
    user_agent: str = "PrivateSearchBot/1.0"
    max_retries: int = 3
    max_doc_size: int = DEFAULT_MAX_DOC_SIZE
    same_domain_only: bool = True
    max_concurrency: int = 10

class WebCrawler:
    def __init__(self, config: CrawlerConfig):
        self.config = config
        self.visited_urls: Set[str] = set()
        self.robots_parsers: Dict[str, urllib.robotparser.RobotFileParser] = {}
        self.stats = {
            "fetched": 0,
            "failed": 0,
            "rejected": 0,
            "discovered": 0,
            "duplicates_avoided": 0,
        }
        self.results = []

    def normalize_url(self, url: str) -> str:
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

    async def can_fetch(self, client: httpx.AsyncClient, url: str) -> bool:
        parsed = urllib.parse.urlsplit(url)
        netloc = parsed.netloc
        scheme = parsed.scheme

        if netloc not in self.robots_parsers:
            rp = urllib.robotparser.RobotFileParser()
            robots_url = f"{scheme}://{netloc}/robots.txt"
            rp.set_url(robots_url)
            try:
                if is_safe_url(robots_url):
                    resp = await client.get(robots_url, timeout=self.config.timeout)
                    if resp.status_code == 200:
                        rp.parse(resp.text.splitlines())
                    elif resp.status_code in (401, 403):
                        rp.disallow_all = True
                    else:
                        rp.allow_all = True
            except Exception as e:
                rp.allow_all = True
            self.robots_parsers[netloc] = rp

        return self.robots_parsers[netloc].can_fetch(self.config.user_agent, url)

    async def fetch_page(self, client: httpx.AsyncClient, url: str) -> Tuple[Optional[str], Optional[str]]:
        if not is_safe_url(url):
            self.stats["rejected"] += 1
            return None, None
            
        retries = 0
        redirect_count = 0
        while retries <= self.config.max_retries:
            try:
                resp = await client.get(url, timeout=self.config.timeout, follow_redirects=False)
                
                if resp.status_code in (301, 302, 303, 307, 308):
                    redirect_count += 1
                    if redirect_count > 5:
                        self.stats["failed"] += 1
                        return None, None
                    next_url = resp.headers.get("Location")
                    if not next_url:
                        return None, None
                    next_url = urllib.parse.urljoin(url, next_url)
                    if not is_safe_url(next_url):
                        return None, None
                    url = next_url
                    continue

                if resp.status_code == 200:
                    content_type = resp.headers.get("Content-Type", "").lower()
                    if "text/html" not in content_type:
                        self.stats["rejected"] += 1
                        return None, None

                    cl_str = resp.headers.get("Content-Length")
                    if cl_str is not None:
                        try:
                            if int(cl_str) > self.config.max_doc_size:
                                self.stats["rejected"] += 1
                                return None, None
                        except ValueError:
                            pass

                    if len(resp.content) > self.config.max_doc_size:
                        self.stats["rejected"] += 1
                        return None, None

                    return resp.text, str(resp.url)

                elif resp.status_code in (429, 500, 502, 503, 504):
                    retries += 1
                    await asyncio.sleep(1.0)
                else:
                    self.stats["failed"] += 1
                    return None, None

            except Exception as e:
                retries += 1
                await asyncio.sleep(1.0)

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
            
        for tag in soup(["script", "style", "noscript", "template", "nav", "header", "footer"]):
            tag.decompose()
            
        main = soup.find("main") or soup.find("div", class_="body") or soup.find("article") or soup.body
        content = main.get_text(separator=" ", strip=True) if main else ""
        content = " ".join(content.split())
        if not content.strip():
            content = title
        return title, content

    async def _worker(self, client, queue, sem):
        while True:
            url, depth = await queue.get()

            if len(self.results) >= self.config.max_pages:
                queue.task_done()
                continue
            
            async with sem:
                if not await self.can_fetch(client, url):
                    self.stats["rejected"] += 1
                    queue.task_done()
                    continue
                    
                html, final_url = await self.fetch_page(client, url)
                
                if html and final_url:
                    self.stats["fetched"] += 1
                    norm_final = self.normalize_url(final_url)
                    canonical_url = self.extract_canonical_url(html, norm_final)
                    
                    c_url = self.normalize_url(canonical_url) if canonical_url and is_safe_url(canonical_url) else norm_final
                    self.visited_urls.add(c_url)
                    
                    title, content = self.extract_content(html)
                    self.results.append((c_url, title, content))

                    if depth < self.config.max_depth:
                        for link in self.extract_links(html, c_url):
                            n_link = self.normalize_url(link)
                            if is_safe_url(n_link):
                                self.stats["discovered"] += 1
                                if n_link not in self.visited_urls and self.is_allowed_domain(n_link):
                                    self.visited_urls.add(n_link)
                                    queue.put_nowait((n_link, depth + 1))
                                else:
                                    if n_link in self.visited_urls:
                                        self.stats["duplicates_avoided"] += 1
            queue.task_done()

    async def crawl_async(self) -> List[Tuple[str, str, str]]:
        headers = {"User-Agent": self.config.user_agent}
        sem = asyncio.Semaphore(self.config.max_concurrency)
        queue = asyncio.Queue()
        
        for seed in self.config.seed_urls:
            n_seed = self.normalize_url(seed)
            if self.is_allowed_domain(n_seed) and is_safe_url(n_seed):
                self.visited_urls.add(n_seed)
                queue.put_nowait((n_seed, 0))

        async with httpx.AsyncClient(headers=headers, verify=False) as client:
            workers = [asyncio.create_task(self._worker(client, queue, sem)) for _ in range(self.config.max_concurrency)]
            
            # Instead of a complex while loop, we just wait until we reach max_pages
            # or all workers become idle and queue is empty (meaning we ran out of pages).
            
            async def monitor():
                while len(self.results) < self.config.max_pages:
                    await asyncio.sleep(0.1)
            
            # Run monitor and queue.join() concurrently.
            # If queue.join finishes first, we crawled everything.
            # If monitor finishes first, we reached max_pages.
            monitor_task = asyncio.create_task(monitor())
            join_task = asyncio.create_task(queue.join())
            
            done, pending = await asyncio.wait(
                [monitor_task, join_task], 
                return_when=asyncio.FIRST_COMPLETED
            )
            
            for t in pending:
                t.cancel()
            
            for w in workers:
                w.cancel()
                
        return self.results[:self.config.max_pages]

    def crawl(self) -> List[Tuple[str, str, str]]:
        return asyncio.run(self.crawl_async())
