import enum
from sqlalchemy import Column, String, Text, DateTime, Integer, Boolean, Enum
from sqlalchemy.orm import declarative_base
from datetime import datetime, timezone

Base = declarative_base()


class IndexingStatus(enum.Enum):
    """
    Represents the synchronization state between the SQLite document record
    and the inverted index (index.pkl).

    Used by the Phase 7 incremental indexing daemon to determine which
    documents require action.

    PENDING   - Document stored in DB but not yet added to the inverted index.
    INDEXED   - Document is confirmed to exist in the persisted inverted index.
    FAILED    - Last indexing attempt for this document failed; needs retry.
    """
    PENDING = "PENDING"
    INDEXED = "INDEXED"
    FAILED  = "FAILED"


class DBDocument(Base):
    __tablename__ = 'documents'

    # --- Core identity (unchanged) ---
    id           = Column(String, primary_key=True)  # SHA256 of URL path
    title        = Column(String, nullable=False)
    content      = Column(Text,   nullable=False)
    url          = Column(String, nullable=True)
    content_hash = Column(String, nullable=False)    # SHA256 of text content

    # --- Timestamps ---
    created_at   = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at   = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                          onupdate=lambda: datetime.now(timezone.utc), nullable=True)

    # --- Version tracking ---
    # Monotonically incremented on every content-changing update.
    # Initial value is 1. Unchanged re-ingestion must NOT increment this.
    version      = Column(Integer, default=1, nullable=False)

    # --- Soft-delete / tombstone ---
    # When True, document is logically deleted. The record is preserved so
    # Phase 7 can detect the deletion and purge from index.pkl.
    # Physical removal of tombstones is deferred to a future compaction phase.
    is_deleted   = Column(Boolean, default=False, nullable=False)

    # --- Indexing status ---
    # Tracks whether this document's content is reflected in the live index.
    # Stored as a VARCHAR to survive SQLite migrations without enum DDL changes.
    indexing_status = Column(
        String, default=IndexingStatus.PENDING.value, nullable=False
    )


class IndexVersion(Base):
    """
    Tracks generations of the persisted inverted index (index.pkl).

    Each row represents one complete serialization of the in-memory index.
    Phase 7 will insert a new row after each successful incremental flush,
    allowing the system to detect consistency between the DB state and the
    index file on disk.
    """
    __tablename__ = 'index_versions'

    id            = Column(Integer, primary_key=True, autoincrement=True)
    # Sequential generation counter; starts at 1, increments each rebuild.
    version       = Column(Integer, nullable=False)
    created_at    = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    document_count = Column(Integer, nullable=False)
    # Optional: coarse checksum or build identifier for debugging.
    checksum      = Column(String, nullable=True)
    # BUILDING / COMPLETE / FAILED
    status        = Column(String, default="COMPLETE", nullable=False)
