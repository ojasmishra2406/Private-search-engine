from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class Document:
    id: str  # Hash or deterministic UUID
    title: str
    content: str
    url: Optional[str] = None
    content_hash: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
