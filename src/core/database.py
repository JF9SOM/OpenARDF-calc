import sqlite3
from pathlib import Path
from typing import Optional


class Database:
    """Thin wrapper around the SQLite connection for this competition file."""

    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def connect(self):
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._create_tables()

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *_):
        self.close()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _create_tables(self):
        assert self._conn
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS competition (
                id          INTEGER PRIMARY KEY,
                name        TEXT    NOT NULL,
                date        TEXT,
                location    TEXT,
                created_at  TEXT    DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS competitor (
                id          INTEGER PRIMARY KEY,
                si_number   TEXT,
                call_sign   TEXT,
                name        TEXT,
                category    TEXT,
                absent      INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS punch_record (
                id              INTEGER PRIMARY KEY,
                competitor_id   INTEGER REFERENCES competitor(id),
                control_code    TEXT,
                punch_time      TEXT
            );
            """
        )
        self._conn.commit()
