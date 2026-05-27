from __future__ import annotations

import csv
import sqlite3
from pathlib import Path
from typing import Any, Optional

from core.database import _migrate

# All writable columns in the competitor table (id and created_at excluded)
COMPETITOR_COLS: tuple[str, ...] = (
    "bib_number", "si_number", "call_sign", "name", "yomigana", "class_name",
    "birthday", "division", "start_order", "group_name",
    "address1", "address2", "tel", "email", "region", "prefecture",
    "absent", "disqualified", "disqualification_reason",
)

# CSV header → DB column (ARDF SI compatible; includes half-width katakana variants)
_CSV_TO_DB: dict[str, str] = {
    # Full-width (OpenARDF-calc native export)
    "ゼッケン":        "bib_number",
    "SINo":           "si_number",
    "SI No":          "si_number",
    "コールサイン":     "call_sign",
    "氏名":            "name",
    "よみがな":         "yomigana",
    "クラス":           "class_name",
    "生年月日":         "birthday",
    "区分":            "division",
    "スタート":         "start_order",
    "グループ":         "group_name",
    "住所1":           "address1",
    "住所2":           "address2",
    "TEL":            "tel",
    "E-mail":         "email",
    "地方":            "region",
    "県":             "prefecture",
    "失格有無":         "disqualified",
    "失格理由":         "disqualification_reason",
    "出欠":            "absent",
    # Half-width katakana (ARDF SI software export)
    "ｾﾞｯｹﾝ":          "bib_number",
    "ｺｰﾙｻｲﾝ":         "call_sign",
    "ｸﾗｽ":            "class_name",
    "ｽﾀｰﾄ":           "start_order",
    "ｽﾀｰﾄ組":          "start_order",
    "ｸﾞﾙｰﾌﾟ":         "group_name",
}

# DB column → CSV header for export
_DB_TO_CSV: dict[str, str] = {
    "bib_number":              "ゼッケン",
    "si_number":               "SINo",
    "call_sign":               "コールサイン",
    "name":                    "氏名",
    "yomigana":                "よみがな",
    "class_name":              "クラス",
    "birthday":                "生年月日",
    "division":                "区分",
    "start_order":             "スタート",
    "group_name":              "グループ",
    "address1":                "住所1",
    "address2":                "住所2",
    "tel":                     "TEL",
    "email":                   "E-mail",
    "region":                  "地方",
    "prefecture":              "県",
    "disqualified":            "失格有無",
    "disqualification_reason": "失格理由",
}

# Columns written to export CSV (absent is internal-only)
_EXPORT_COLS: tuple[str, ...] = tuple(c for c in COMPETITOR_COLS if c != "absent")

_ENCODINGS = ("utf-8-sig", "utf-8", "cp932", "latin-1")


class CompetitorDAO:
    """SQLite CRUD + CSV import/export for the competitor table."""

    def __init__(self, db_path: Path):
        self._db_path = db_path

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        _migrate(conn)
        return conn

    def _read_text(self, path: Path) -> str:
        for enc in _ENCODINGS:
            try:
                return path.read_text(encoding=enc)
            except UnicodeDecodeError:
                continue
        raise ValueError(f"Cannot decode '{path}'")

    def _insert_sql(self, cols: list[str]) -> str:
        ph = ", ".join("?" * len(cols))
        return f"INSERT INTO competitor ({', '.join(cols)}) VALUES ({ph})"

    def _update_sql(self, cols: list[str]) -> str:
        sets = ", ".join(f"{c}=?" for c in cols)
        return f"UPDATE competitor SET {sets} WHERE id=?"

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_all(self) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM competitor "
                "ORDER BY CAST(bib_number AS INTEGER), bib_number"
            ).fetchall()
        return [dict(r) for r in rows]

    def get_by_id(self, competitor_id: int) -> Optional[dict[str, Any]]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM competitor WHERE id=?", (competitor_id,)
            ).fetchone()
        return dict(row) if row else None

    def count(self) -> int:
        with self._conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM competitor").fetchone()[0]

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def insert(self, data: dict[str, Any]) -> int:
        cols = [c for c in COMPETITOR_COLS if c in data]
        with self._conn() as conn:
            cur = conn.execute(self._insert_sql(cols), [data[c] for c in cols])
        return cur.lastrowid

    def update(self, competitor_id: int, data: dict[str, Any]) -> None:
        cols = [c for c in COMPETITOR_COLS if c in data]
        vals = [data[c] for c in cols] + [competitor_id]
        with self._conn() as conn:
            conn.execute(self._update_sql(cols), vals)

    def delete(self, competitor_id: int) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM competitor WHERE id=?", (competitor_id,))

    # ------------------------------------------------------------------
    # Duplicate checks
    # ------------------------------------------------------------------

    def _exists(self, col: str, val: str, exclude_id: Optional[int]) -> bool:
        if not val:
            return False
        sql = f"SELECT 1 FROM competitor WHERE {col}=?"
        args: list[Any] = [val]
        if exclude_id is not None:
            sql += " AND id!=?"
            args.append(exclude_id)
        with self._conn() as conn:
            return conn.execute(sql, args).fetchone() is not None

    def is_duplicate_bib(self, bib: str, exclude_id: Optional[int] = None) -> bool:
        return self._exists("bib_number", bib, exclude_id)

    def is_duplicate_callsign(self, cs: str, exclude_id: Optional[int] = None) -> bool:
        return self._exists("call_sign", cs, exclude_id)

    def is_duplicate_si(self, si: str, exclude_id: Optional[int] = None) -> bool:
        return self._exists("si_number", si, exclude_id)

    # ------------------------------------------------------------------
    # CSV import
    # ------------------------------------------------------------------

    def import_csv(self, path: Path) -> tuple[int, list[str]]:
        """Import CSV. Returns (imported_count, error_messages)."""
        text = self._read_text(path)
        reader = csv.DictReader(text.splitlines())
        imported = 0
        errors: list[str] = []
        seen_bibs: set[str] = set()

        with self._conn() as conn:
            for row_num, row in enumerate(reader, start=2):
                data: dict[str, Any] = {}
                for csv_col, db_col in _CSV_TO_DB.items():
                    raw = row.get(csv_col)
                    if raw is None:
                        continue
                    val = str(raw).strip()
                    if db_col == "start_order":
                        data[db_col] = int(val) if val.isdigit() else None
                    elif db_col in ("absent", "disqualified"):
                        data[db_col] = 1 if val else 0
                    else:
                        data[db_col] = val or None

                bib = data.get("bib_number") or ""
                if not bib:
                    errors.append(f"行{row_num}: ゼッケン番号が空です（スキップ）")
                    continue
                if bib in seen_bibs:
                    errors.append(
                        f"行{row_num}: ゼッケン {bib} がCSV内で重複しています（スキップ）"
                    )
                    continue
                seen_bibs.add(bib)

                cols = [c for c in COMPETITOR_COLS if c in data]
                vals = [data[c] for c in cols]

                try:
                    existing = conn.execute(
                        "SELECT id FROM competitor WHERE bib_number=?", (bib,)
                    ).fetchone()
                    if existing:
                        conn.execute(self._update_sql(cols), vals + [existing["id"]])
                    else:
                        conn.execute(self._insert_sql(cols), vals)
                    imported += 1
                except sqlite3.Error as exc:
                    errors.append(f"行{row_num}: DB エラー — {exc}")

        return imported, errors

    # ------------------------------------------------------------------
    # CSV export
    # ------------------------------------------------------------------

    def export_csv(self, path: Path) -> int:
        """Export all competitors as ARDF-SI-compatible CSV. Returns row count."""
        competitors = self.get_all()
        headers = [_DB_TO_CSV[c] for c in _EXPORT_COLS]

        with path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for c in competitors:
                writer.writerow([c.get(col) or "" for col in _EXPORT_COLS])

        return len(competitors)
