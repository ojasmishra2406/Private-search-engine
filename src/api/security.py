from typing import Set, Tuple
from sqlalchemy.orm import Session
from src.storage.models import DBDocument
import functools

ROLE_INHERITANCE = {
    "Admin": ["Admin", "Engineering", "HR", "Finance", "Public"],
    "Engineering": ["Engineering", "Public"],
    "HR": ["HR", "Public"],
    "Finance": ["Finance", "Public"],
    "Public": ["Public"]
}

_ROLE_CACHE = {}

class AuthorizedIdSet(set):
    """Subclass of set that carries an explicit immutable cache key for safe FAISS selector caching."""
    def __init__(self, iterable=None, cache_key: str = None):
        super().__init__(iterable or ())
        self.cache_key = cache_key

def get_authorized_doc_ids(db: Session, simulated_role: str) -> Tuple[Set[str], Set[int], int]:
    """
    Returns (authorized_str_ids, authorized_int_ids, total_blocked_count)
    """
    role = simulated_role if simulated_role in ROLE_INHERITANCE else "Public"
    
    if role in _ROLE_CACHE:
        return _ROLE_CACHE[role]
        
    allowed = ROLE_INHERITANCE[role]
    
    # Get authorized IDs
    results = db.query(DBDocument.id, DBDocument.int_id).filter(
        DBDocument.allowed_roles.in_(allowed),
        DBDocument.is_deleted == False
    ).all()
    
    # Get total database count for 'Show Blocked Results Count' (Option A)
    total_docs = db.query(DBDocument.id).filter(DBDocument.is_deleted == False).count()
    
    auth_str = set(r[0] for r in results)
    auth_int = AuthorizedIdSet((r[1] for r in results if r[1] is not None), cache_key=f"role:{role}")
    
    blocked_count = total_docs - len(auth_str)
    
    _ROLE_CACHE[role] = (auth_str, auth_int, blocked_count)
    return _ROLE_CACHE[role]