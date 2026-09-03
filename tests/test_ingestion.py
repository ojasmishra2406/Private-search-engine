import os
import hashlib
import pytest
from src.ingestion.python_docs import PythonDocParser
from src.core.tokenizer import Tokenizer
from src.storage.database import Database
from src.storage.models import DBDocument

@pytest.fixture
def parser():
    return PythonDocParser()

@pytest.fixture
def sample_html_file(tmp_path):
    html_content = """
    <html>
        <head><title>Test Title</title></head>
        <body>
            <div class="sphinxsidebar">Navigation</div>
            <div class="body">
                <h1>Test Title</h1>
                <p>This is the main content containing os.path.join.</p>
                <script>alert('hide me');</script>
            </div>
        </body>
    </html>
    """
    file_path = tmp_path / "test_doc.html"
    file_path.write_text(html_content, encoding='utf-8')
    return str(file_path), str(tmp_path)

@pytest.fixture
def malformed_html_file(tmp_path):
    html_content = "<html><body>Just some text"
    file_path = tmp_path / "malformed.html"
    file_path.write_text(html_content, encoding='utf-8')
    return str(file_path), str(tmp_path)

def test_title_and_content_extraction(parser, sample_html_file):
    file_path, base_dir = sample_html_file
    doc = parser.parse_html(file_path, base_dir)
    
    assert doc.title == "Test Title"
    assert "This is the main content containing os.path.join." in doc.content
    assert "Navigation" not in doc.content  # Outside .body
    assert "hide me" not in doc.content     # In script tag

def test_deterministic_id_and_hashing(parser, sample_html_file):
    file_path, base_dir = sample_html_file
    doc1 = parser.parse_html(file_path, base_dir)
    doc2 = parser.parse_html(file_path, base_dir)
    
    assert doc1.id == doc2.id
    assert doc1.content_hash == doc2.content_hash
    
    # ID should be hash of relative path
    rel_path = "test_doc.html"
    expected_id = hashlib.sha256(rel_path.encode('utf-8')).hexdigest()
    assert doc1.id == expected_id

def test_malformed_html(parser, malformed_html_file):
    file_path, base_dir = malformed_html_file
    doc = parser.parse_html(file_path, base_dir)
    
    # Title might be empty, content should have the text
    assert "Just some text" in doc.content

def test_technical_identifiers_intact(parser, sample_html_file):
    file_path, base_dir = sample_html_file
    doc = parser.parse_html(file_path, base_dir)
    
    tokenizer = Tokenizer()
    tokens = tokenizer.tokenize(doc.content)
    assert "os.path.join" in tokens

def test_duplicate_and_update_logic(parser, sample_html_file):
    # This tests the logic that would be in run_ingestion.py
    file_path, base_dir = sample_html_file
    doc = parser.parse_html(file_path, base_dir)
    
    db = Database("sqlite:///:memory:")
    db.init_db()
    session = db.get_session()
    
    # Insert new
    db_doc = DBDocument(id=doc.id, title=doc.title, content=doc.content, url=doc.url, content_hash=doc.content_hash)
    session.add(db_doc)
    session.commit()
    
    # Simulate Unchanged (same hash)
    existing = session.query(DBDocument).filter_by(id=doc.id).first()
    assert existing.content_hash == doc.content_hash
    
    # Simulate Changed
    doc.content = "New content"
    doc.content_hash = hashlib.sha256(doc.content.encode('utf-8')).hexdigest()
    
    existing.content = doc.content
    existing.content_hash = doc.content_hash
    session.commit()
    
    updated = session.query(DBDocument).filter_by(id=doc.id).first()
    assert updated.content == "New content"
