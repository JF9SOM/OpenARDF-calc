import sqlite3
from pathlib import Path
from typing import Optional

from ui.dialogs.competition_settings import _create_tables


class Database:
    """SQLite connection wrapper for one competition file."""

    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def connect(self) -> None:
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        _create_tables(self._conn)

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "Database":
        self.connect()
        return self

    def __exit__(self, *_) -> None:
        self.close()
