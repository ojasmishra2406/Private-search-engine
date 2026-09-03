import os
import hashlib
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from src.core.document import Document

class PythonDocParser:
    def parse_html(self, file_path: str, base_dir: str) -> Document:
        with open(file_path, 'r', encoding='utf-8') as f:
            html = f.read()

        # Relative path for deterministic ID
        rel_path = os.path.relpath(file_path, base_dir)
        # Always use forward slashes for cross-platform consistency in hashing
        rel_path = rel_path.replace("\\", "/")

        return self.parse_html_string(rel_path, html)

    def parse_html_string(self, url: str, html: str) -> Document:
        soup = BeautifulSoup(html, 'html.parser')

        # Extract title
        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        elif soup.find('h1'):
            title = soup.find('h1').get_text(strip=True)

        # Extract main content
        main_content = soup.find('div', class_='body')
        if not main_content:
            main_content = soup.find('main')
        if not main_content:
            main_content = soup.find('div', class_='document')
        if not main_content:
            main_content = soup.body

        if main_content:
            # Remove scripts and styles
            for script in main_content(["script", "style"]):
                script.decompose()
            text_content = main_content.get_text(separator=' ', strip=True)
        else:
            text_content = ""

        doc_id = hashlib.sha256(url.encode('utf-8')).hexdigest()
        content_hash = hashlib.sha256(text_content.encode('utf-8')).hexdigest()

        return Document(
            id=doc_id,
            title=title,
            content=text_content,
            url=url,
            content_hash=content_hash,
            created_at=datetime.now(timezone.utc)
        )
