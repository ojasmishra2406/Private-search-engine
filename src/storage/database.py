import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from .models import Base, IndexingStatus

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_url="sqlite:///search.db"):
        self.engine = create_engine(db_url)
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

    def init_db(self):
        """
        Create all tables that do not yet exist (safe for existing data),
        then apply any additive column migrations required for Phase 3.
        """
        Base.metadata.create_all(bind=self.engine)
        self._apply_migrations()

    def _apply_migrations(self):
        """
        Idempotent column-level migrations for the documents table.

        Uses PRAGMA table_info to check whether each Phase 3 column already
        exists before issuing ALTER TABLE. This is safe to run on every
        startup — it is a no-op when the schema is already current.

        All new columns have defaults that make existing rows valid without
        a full data reload.
        """
        pending_default = IndexingStatus.PENDING.value  # 'PENDING'

        # Map: column_name -> ddl_fragment (everything after the column name)
        # updated_at is NULLABLE — SQLite cannot add a NOT NULL column with a
        # literal NULL default to existing rows.  The ORM onupdate handles it.
        required_columns = {
            "updated_at":       "DATETIME",                          # nullable
            "version":          "INTEGER NOT NULL DEFAULT 1",
            "is_deleted":       "INTEGER NOT NULL DEFAULT 0",        # bool
            "indexing_status":  f"VARCHAR NOT NULL DEFAULT '{pending_default}'",
        }

        with self.engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(documents)"))
            existing_cols = {row[1] for row in result.fetchall()}

            for col_name, col_ddl in required_columns.items():
                if col_name not in existing_cols:
                    ddl = (
                        f"ALTER TABLE documents ADD COLUMN {col_name} {col_ddl}"
                    )
                    conn.execute(text(ddl))
                    logger.info(
                        "Migration: added column '%s' to documents table.",
                        col_name,
                    )

            conn.commit()

    def get_session(self):
        return self.SessionLocal()
