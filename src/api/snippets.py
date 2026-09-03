from typing import Dict, List, Any
from src.core.tokenizer import Tokenizer
import re

class SnippetGenerator:
    def __init__(self, tokenizer: Tokenizer):
        self.tokenizer = tokenizer

    def generate(self, content: str, query: str, window_size: int = 150) -> Dict[str, Any]:
        """
        Generates a text snippet from the document content surrounding the query terms.
        """
        if not content:
            return {"text": "", "matches": []}
            
        query_tokens = set(self.tokenizer.tokenize(query))
        if not query_tokens:
            return {
                "text": content[:window_size] + "..." if len(content) > window_size else content,
                "matches": []
            }
            
        content_lower = content.lower()
        best_pos = -1
        best_match = ""
        
        # Find the first occurrence of any query token
        # For V1, this is a simple text search rather than relying on index positions
        for token in query_tokens:
            pos = content_lower.find(token)
            if pos != -1:
                # Prioritize exact word boundaries if possible, but fallback to substring
                best_pos = pos
                best_match = token
                break
                
        if best_pos == -1:
            # Fallback if tokens were normalized in a way that exact substring fails
            return {
                "text": content[:window_size] + "..." if len(content) > window_size else content,
                "matches": []
            }
            
        # Extract a window around the match
        start = max(0, best_pos - (window_size // 2))
        end = min(len(content), best_pos + len(best_match) + (window_size // 2))
        
        # Snap to word boundaries for cleaner snippets
        if start > 0:
            next_space = content.find(" ", start)
            if next_space != -1 and next_space < best_pos:
                start = next_space + 1
                
        end_space = content.find(" ", end)
        if end_space != -1:
            end = end_space
            
        snippet_text = content[start:end].strip()
        
        # Determine which query tokens appear in the final snippet
        snippet_lower = snippet_text.lower()
        matches = [t for t in query_tokens if t in snippet_lower]
        
        prefix = "..." if start > 0 else ""
        suffix = "..." if end < len(content) else ""
        
        return {
            "text": f"{prefix}{snippet_text}{suffix}",
            "matches": matches
        }
