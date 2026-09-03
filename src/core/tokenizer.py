import re
import unicodedata
from typing import List

class Tokenizer:
    def __init__(self):
        # Matches alphanumeric sequences with optional leading dot, internal hyphens/slashes/dots, and +/# at the end
        # e.g., "hello", "__init__", "os.path", "c++", "c#", ".net", "http/2", "utf-8"
        self.pattern = re.compile(r'\.?[a-zA-Z0-9_]+(?:[-./][a-zA-Z0-9_]+)*(?:\+\+|#)?')
        
    def normalize(self, text: str) -> str:
        # Unicode normalization (NFKC) and case folding
        text = unicodedata.normalize('NFKC', text)
        return text.lower()
        
    def tokenize(self, text: str) -> List[str]:
        text = self.normalize(text)
        return self.pattern.findall(text)
