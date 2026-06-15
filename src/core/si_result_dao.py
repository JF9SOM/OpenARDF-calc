from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Optional


def _hms_to_seconds(hms: str) -> int:
    """Convert 'H:MM:SS' or 'HH:MM:SS' to total seconds."""
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

    def get_start_order_map(self) -> dict[int, int]:
        """Return {competitor_id: start_order} for every competitor that has one."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, start_order FROM competitor "
                "WHERE start_order IS NOT NULL"
            ).fetchall()
        return {r["id"]: r["start_order"] for r in rows}

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
        self, records: list[dict], si_base_time: Optional[str] = None
    ) -> tuple[int, list[str], list[str]]:
        """Match *records* against competitors and compute elapsed times.

        Returns (matched_count, unmatched_si_numbers, warnings).

        For records with time_format="si_relative" (raw ARDF-SI CSV):
            elapsed = si_zero_seconds + finish_seconds - group_start_seconds
        For standard header-based CSV:
            elapsed = finish_seconds - si_base_time_seconds
        """
        comp = self.get_competition()
        si_map = self.get_si_number_map()
        start_order_map = self.get_start_order_map()

        # Competition-level timing parameters
        si_zero_sec: Optional[int] = None
        first_start_sec: Optional[int] = None
        group_interval_sec: int = 300  # default 5 min
        time_limit_sec: int = 7200    # default 120 min

        if comp:
            if comp.get("si_base_time"):
                try:
                    si_zero_sec = _hms_to_seconds(comp["si_base_time"])
                except ValueError:
                    pass
            if comp.get("start_time_g1"):
                try:
                    first_start_sec = _hms_to_seconds(comp["start_time_g1"])
                except ValueError:
                    pass
            group_interval_sec = (comp.get("group_interval_min") or 5) * 60
            time_limit_sec = (comp.get("time_limit_min") or 120) * 60

        # Fall back to caller-supplied si_base_time for standard CSV
        caller_base_sec: Optional[int] = None
        if si_base_time:
            try:
                caller_base_sec = _hms_to_seconds(si_base_time)
            except ValueError:
                pass

        matched = 0
        unmatched: list[str] = []
        warnings: list[str] = []

        for rec in records:
            si = rec["si_number"]
            competitor_id = si_map.get(si)
            if competitor_id is None:
                unmatched.append(si)
                continue

            finish_time: Optional[str] = rec.get("finish_time")
            elapsed: Optional[int] = None
            overtime = False

            if rec.get("time_format") == "si_relative":
                # Raw ARDF-SI CSV: finish_time is relative to SI zero
                if finish_time and si_zero_sec is not None and first_start_sec is not None:
                    try:
                        finish_sec = _hms_to_seconds(finish_time)
                        start_order = start_order_map.get(competitor_id, 1)
                        group_start_sec = first_start_sec + (start_order - 1) * group_interval_sec
                        elapsed = si_zero_sec + finish_sec - group_start_sec
                        if elapsed < 0:
                            elapsed = None
                        else:
                            overtime = elapsed > time_limit_sec
                    except ValueError as exc:
                        warnings.append(f"SI {si}: 時刻変換エラー — {exc}")
            else:
                # Standard header CSV: finish_time is absolute clock time
                base = caller_base_sec if caller_base_sec is not None else si_zero_sec
                if finish_time and base is not None:
                    try:
                        elapsed = _hms_to_seconds(finish_time) - base
                        if elapsed < 0:
                            elapsed += 86400
                        overtime = elapsed > time_limit_sec
                    except ValueError as exc:
                        warnings.append(f"SI {si}: 時刻変換エラー — {exc}")

            try:
                self.upsert(
                    competitor_id=competitor_id,
                    finish_time=finish_time,
                    elapsed_seconds=elapsed,
                    punched_tx_count=rec.get("punched_tx_count", 0),
                    overtime=overtime,
                    raw_status=rec.get("raw_status"),
                    tx_punches=rec.get("tx_punches", {}),
                )
                matched += 1
            except sqlite3.Error as exc:
                warnings.append(f"SI {si}: DB エラー — {exc}")

        return matched, unmatched, warnings
