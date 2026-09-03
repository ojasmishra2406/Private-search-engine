import pytest
from src.core.tokenizer import Tokenizer

def test_tokenizer_preserves_technical_terms():
    tokenizer = Tokenizer()
    text = "The __init__ method in python, C++, and C# is os.path.join v1.2.3."
    tokens = tokenizer.tokenize(text)
    
    assert "__init__" in tokens
    assert "c++" in tokens
    assert "c#" in tokens
    assert "os.path.join" in tokens
    assert "v1.2.3" in tokens
    
def test_tokenizer_removes_general_punctuation():
    tokenizer = Tokenizer()
    text = "Hello, world! This is a test."
    tokens = tokenizer.tokenize(text)
    
    assert tokens == ["hello", "world", "this", "is", "a", "test"]

def test_tokenizer_normalization():
    tokenizer = Tokenizer()
    text = "ﬁnd"
    tokens = tokenizer.tokenize(text)
    assert tokens == ["find"]

def test_tokenizer_edge_cases():
    tokenizer = Tokenizer()
    
    assert tokenizer.tokenize("C++") == ["c++"]
    assert tokenizer.tokenize("C#") == ["c#"]
    assert tokenizer.tokenize(".NET") == [".net"]
    assert tokenizer.tokenize("HTTP/2") == ["http/2"]
    assert tokenizer.tokenize("UTF-8") == ["utf-8"]
    assert tokenizer.tokenize("v1.2.3") == ["v1.2.3"]
    assert tokenizer.tokenize("__init__") == ["__init__"]
    assert tokenizer.tokenize("os.path.join") == ["os.path.join"]
    assert tokenizer.tokenize("snake_case") == ["snake_case"]
    assert tokenizer.tokenize("CamelCase") == ["camelcase"]
    assert tokenizer.tokenize("O(n log n)") == ["o", "n", "log", "n"]
    assert tokenizer.tokenize("NullPointerException") == ["nullpointerexception"]
