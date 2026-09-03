"""
Query normalization utilities for Phase 17.
Keeps technical tokens intact while cleaning whitespace.
"""
import re


def normalize_query(q: str) -> str:
    """
    Normalize a search query string.

    - Strips leading/trailing whitespace
    - Collapses internal repeated whitespace into single spaces
    - Preserves case (tokenizer handles case normalization)
    - Preserves all technical tokens (__, ::, .., C++, etc.)
    - Returns empty string for empty/whitespace-only input
    """
    if not q:
        return ""
    # Collapse all whitespace runs to a single space
    q = re.sub(r'\s+', ' ', q)
    return q.strip()
