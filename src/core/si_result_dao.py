from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Optional


def _hms_to_seconds(hms: str) -> int:
    """Convert 'HH:MM:SS' to total seconds."""
    parts = hms.split(":")
    if len(parts) != 3:
        raise ValueError(f"Invalid time format: {hms!r}")
    h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
    return h * 3600 + m * 60 + s


class SIResultDAO:
    """Read/write SI competition results (results + tx_punches tables)."""

    def __init__(self, db_path: Path):
        self._db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def get_competition(self) -> Optional[dict[str, Any]]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM competition LIMIT 1").fetchone()
        return dict(row) if row else None

    def get_si_number_map(self) -> dict[str, int]:
        """Return {si_number: competitor_id} for every competitor that has one."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, si_number FROM competitor "
                "WHERE si_number IS NOT NULL AND si_number != ''"
            ).fetchall()
        return {r["si_number"]: r["id"] for r in rows}

    def get_by_competitor_id(self, competitor_id: int) -> Optional[dict[str, Any]]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM results WHERE competitor_id=?", (competitor_id,)
            ).fetchone()
        return dict(row) if row else None

    # ------------------------------------------------------------------
    # Upsert
    # ------------------------------------------------------------------

    def upsert(
        self,
        competitor_id: int,
        finish_time: Optional[str],
        elapsed_seconds: Optional[int],
        punched_tx_count: int,
        overtime: bool,
        raw_status: Optional[str],
        tx_punches: dict[int, str],
    ) -> None:
        """Insert or replace a competitor's result and TX punch times."""
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO results
                    (competitor_id, finish_time, elapsed_seconds,
                     punched_tx_count, overtime, raw_status)
                VALUES (?,?,?,?,?,?)
                ON CONFLICT(competitor_id) DO UPDATE SET
                    finish_time      = excluded.finish_time,
                    elapsed_seconds  = excluded.elapsed_seconds,
                    punched_tx_count = excluded.punched_tx_count,
                    overtime         = excluded.overtime,
                    raw_status       = excluded.raw_status,
                    imported_at      = datetime('now')
                """,
                (
                    competitor_id,
                    finish_time,
                    elapsed_seconds,
                    punched_tx_count,
                    int(overtime),
                    raw_status,
                ),
            )
            conn.execute(
                "DELETE FROM tx_punches WHERE competitor_id=?",
                (competitor_id,),
            )
            for tx_num, punch_time in tx_punches.items():
                conn.execute(
                    "INSERT INTO tx_punches (competitor_id, tx_number, punch_time) "
                    "VALUES (?,?,?)",
                    (competitor_id, tx_num, punch_time),
                )

    # ------------------------------------------------------------------
    # Bulk import helper
    # ------------------------------------------------------------------

    def import_records(
        self, records: list[dict], si_base_time: Optional[str]
    ) -> tuple[int, list[str], list[str]]:
        """Match *records* (from SIManagerCSVReader) against competitors.

        Returns (matched_count, unmatched_si_numbers, warnings).
        """
        si_map = self.get_si_number_map()
        matched = 0
        unmatched: list[str] = []
        warnings: list[str] = []

        for rec in records:
            si = rec["si_number"]
            competitor_id = si_map.get(si)
            if competitor_id is None:
                unmatched.append(si)
                continue

            elapsed: Optional[int] = None
            finish_time: Optional[str] = rec.get("finish_time")
            if finish_time and si_base_time:
                try:
                    elapsed = _hms_to_seconds(finish_time) - _hms_to_seconds(si_base_time)
                    if elapsed < 0:
                        elapsed += 86400  # past midnight
                except ValueError as exc:
                    warnings.append(
                        f"SI {si}: 時刻変換エラー — {exc}"
                    )

            try:
                self.upsert(
                    competitor_id=competitor_id,
                    finish_time=finish_time,
                    elapsed_seconds=elapsed,
                    punched_tx_count=rec.get("punched_tx_count", 0),
                    overtime=rec.get("overtime", False),
                    raw_status=rec.get("raw_status"),
                    tx_punches=rec.get("tx_punches", {}),
                )
                matched += 1
            except sqlite3.Error as exc:
                warnings.append(f"SI {si}: DB エラー — {exc}")

        return matched, unmatched, warnings
