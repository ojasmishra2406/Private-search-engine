import pytest
from src.core.tokenizer import Tokenizer
from src.api.snippets import SnippetGenerator

def test_snippet_generation():
    tokenizer = Tokenizer()
    generator = SnippetGenerator(tokenizer)
    
    content = "This is a long document about Python programming. It explains how to use os.path.join effectively."
    query = "os.path.join"
    
    result = generator.generate(content, query, window_size=50)
    
    # Must contain the match
    assert "os.path.join" in result["text"]
    assert "os.path.join" in result["matches"]
    
def test_snippet_empty_query():
    tokenizer = Tokenizer()
    generator = SnippetGenerator(tokenizer)
    
    content = "Hello world."
    result = generator.generate(content, "", window_size=50)
    
    assert "Hello world." in result["text"]
    assert len(result["matches"]) == 0

def test_snippet_no_match():
    tokenizer = Tokenizer()
    generator = SnippetGenerator(tokenizer)
    
    content = "This document does not contain the target."
    query = "missing"
    
    result = generator.generate(content, query, window_size=20)
    # Should return prefix of document
    assert result["text"].startswith("This document")
    assert len(result["matches"]) == 0

def test_snippet_empty_content():
    tokenizer = Tokenizer()
    generator = SnippetGenerator(tokenizer)
    
    result = generator.generate("", "query", window_size=20)
    assert result["text"] == ""
    assert len(result["matches"]) == 0
