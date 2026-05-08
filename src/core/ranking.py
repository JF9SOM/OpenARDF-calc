from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from itertools import groupby
from pathlib import Path
from typing import Optional


@dataclass
class RankedCompetitor:
    rank: Optional[int]
    competitor_id: int
    bib_number: str
    call_sign: str
    name: str
    class_name: str
    punched_tx_count: int
    finish_time: Optional[str]
    elapsed_seconds: Optional[int]
    overtime: bool
    absent: bool
    disqualified: bool
    disqualification_reason: Optional[str]
    tx_punches: dict[int, str] = field(default_factory=dict)
    region: Optional[str] = None
    prefecture: Optional[str] = None
    division: Optional[str] = None

    @property
    def is_ranked(self) -> bool:
        return not (self.absent or self.disqualified)

    @property
    def remark(self) -> str:
        if self.absent:
            return "欠席"
        if self.disqualified:
            return self.disqualification_reason or "失格"
        if self.overtime:
            return "OT"
        return ""

    @property
    def elapsed_str(self) -> str:
        """Elapsed time as H:MM:SS or MM:SS."""
        if self.elapsed_seconds is None:
            return self.finish_time or ""
        total = abs(self.elapsed_seconds)
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        if h:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"


class RankingEngine:
    """Compute per-class ARDF rankings from the SQLite database.

    Ranking rules:
      1. More punched TXs rank higher.
      2. Ties broken by elapsed_seconds ascending (faster = better).
      3. Absent / disqualified competitors appear last with no rank number.
    """

    def __init__(self, db_path: Path):
        self._db_path = db_path

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def compute(self) -> list[RankedCompetitor]:
        """Return all competitors with rank assigned within each class."""
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT
                    c.id, c.bib_number, c.call_sign, c.name,
                    COALESCE(c.class_name, '') AS class_name,
                    COALESCE(c.absent, 0)       AS absent,
                    COALESCE(c.disqualified, 0) AS disqualified,
                    c.disqualification_reason,
                    c.region, c.prefecture, c.division,
                    COALESCE(r.punched_tx_count, 0) AS punched_tx_count,
                    r.finish_time, r.elapsed_seconds,
                    COALESCE(r.overtime, 0) AS overtime
                FROM competitor c
                LEFT JOIN results r ON c.id = r.competitor_id
            """).fetchall()
            punch_rows = conn.execute(
                "SELECT competitor_id, tx_number, punch_time FROM tx_punches"
            ).fetchall()

        tx_map: dict[int, dict[int, str]] = {}
        for p in punch_rows:
            tx_map.setdefault(p["competitor_id"], {})[p["tx_number"]] = p["punch_time"]

        competitors = [
            RankedCompetitor(
                rank=None,
                competitor_id=row["id"],
                bib_number=row["bib_number"] or "",
                call_sign=row["call_sign"] or "",
                name=row["name"] or "",
                class_name=row["class_name"],
                punched_tx_count=row["punched_tx_count"],
                finish_time=row["finish_time"],
                elapsed_seconds=row["elapsed_seconds"],
                overtime=bool(row["overtime"]),
                absent=bool(row["absent"]),
                disqualified=bool(row["disqualified"]),
                disqualification_reason=row["disqualification_reason"],
                tx_punches=tx_map.get(row["id"], {}),
                region=row["region"],
                prefecture=row["prefecture"],
                division=row["division"],
            )
            for row in rows
        ]
        return self._assign_ranks(competitors)

    def compute_by_class(self) -> dict[str, list[RankedCompetitor]]:
        """Return {class_name: [RankedCompetitor, ...]} sorted by class name."""
        result: dict[str, list[RankedCompetitor]] = {}
        for rc in self.compute():
            result.setdefault(rc.class_name, []).append(rc)
        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _assign_ranks(self, competitors: list[RankedCompetitor]) -> list[RankedCompetitor]:
        competitors.sort(key=lambda c: c.class_name)
        result: list[RankedCompetitor] = []
        for _, group in groupby(competitors, key=lambda c: c.class_name):
            result.extend(self._rank_class(list(group)))
        return result

    def _rank_class(self, competitors: list[RankedCompetitor]) -> list[RankedCompetitor]:
        ranked = [c for c in competitors if c.is_ranked]
        unranked = [c for c in competitors if not c.is_ranked]
        ranked.sort(key=lambda c: (
            -c.punched_tx_count,
            c.elapsed_seconds if c.elapsed_seconds is not None else 999_999,
        ))
        for i, rc in enumerate(ranked, start=1):
            rc.rank = i
        return ranked + unranked
