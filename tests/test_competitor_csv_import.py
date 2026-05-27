"""Tests for CompetitorDAO CSV import with ARDF SI format files."""

from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ui.dialogs.competition_settings import _create_tables
from core.competitor_dao import CompetitorDAO

CSV_2026_ISHIKAWA = Path(__file__).parent / "data" / "2026石川.CSV"


def _make_dao() -> tuple[CompetitorDAO, Path]:
    tmp = Path(tempfile.mktemp(suffix=".ardf"))
    conn = sqlite3.connect(str(tmp))
    conn.row_factory = sqlite3.Row
    _create_tables(conn)
    conn.close()
    return CompetitorDAO(tmp), tmp


class TestArdfSiCsvImport:
    """Import of ARDF SI software CSV (Shift-JIS, half-width katakana headers)."""

    def test_import_count(self):
        dao, tmp = _make_dao()
        try:
            count, errors = dao.import_csv(CSV_2026_ISHIKAWA)
            assert errors == [], f"Unexpected errors: {errors}"
            assert count == 46
        finally:
            tmp.unlink(missing_ok=True)

    def test_bib_and_si_number(self):
        dao, tmp = _make_dao()
        try:
            dao.import_csv(CSV_2026_ISHIKAWA)
            rows = dao.get_all()
            assert rows[0]["bib_number"] == "1"
            assert rows[0]["si_number"] == "1"
        finally:
            tmp.unlink(missing_ok=True)

    def test_callsign_and_name(self):
        dao, tmp = _make_dao()
        try:
            dao.import_csv(CSV_2026_ISHIKAWA)
            rows = dao.get_all()
            assert rows[0]["call_sign"] == "JA9-3192"
            assert rows[0]["name"] == "川井　麻矢"
        finally:
            tmp.unlink(missing_ok=True)

    def test_yomigana(self):
        dao, tmp = _make_dao()
        try:
            dao.import_csv(CSV_2026_ISHIKAWA)
            rows = dao.get_all()
            assert rows[0]["yomigana"] == "かわい　まや"
            assert rows[1]["yomigana"] == "くさかべ　あさみ"
        finally:
            tmp.unlink(missing_ok=True)

    def test_class_and_start_order(self):
        dao, tmp = _make_dao()
        try:
            dao.import_csv(CSV_2026_ISHIKAWA)
            rows = dao.get_all()
            assert rows[0]["class_name"] == "W21"
            assert rows[0]["start_order"] == 6
        finally:
            tmp.unlink(missing_ok=True)

    def test_absent_defaults_to_zero(self):
        dao, tmp = _make_dao()
        try:
            dao.import_csv(CSV_2026_ISHIKAWA)
            rows = dao.get_all()
            assert all(r["absent"] == 0 for r in rows)
        finally:
            tmp.unlink(missing_ok=True)

    def test_all_rows_imported(self):
        dao, tmp = _make_dao()
        try:
            dao.import_csv(CSV_2026_ISHIKAWA)
            rows = dao.get_all()
            bibs = {r["bib_number"] for r in rows}
            assert "1" in bibs
            assert "186" in bibs
            assert len(bibs) == 46
        finally:
            tmp.unlink(missing_ok=True)
