from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any

from .base import SIReaderBase

# Column header variants (lowercased, stripped) that identify each field
_SI_CARD_VARIANTS: frozenset[str] = frozenset([
    "sino", "si no", "siカードno", "siカードno.", "si card", "si-card",
    "card", "card no.", "カード番号", "sicard", "si_card",
])
_FINISH_VARIANTS: frozenset[str] = frozenset([
    "フィニッシュ", "finish", "fin", "f", "finish time", "finish_time",
])
_STATUS_VARIANTS: frozenset[str] = frozenset([
    "状態", "status", "classifier", "nc",
])
_TX_COUNT_VARIANTS: frozenset[str] = frozenset([
    "探索tx数", "探索tx", "tx count", "txcount", "punched tx", "punched",
])
_TX_RE = re.compile(r"^tx(\d+)$", re.IGNORECASE)


class SIManagerCSVReader(SIReaderBase):
    """Reads SI punch data from SI Manager ARDF CSV export.

    Handles UTF-8-BOM and CP932 automatically.  Returns a list of normalised
    dicts; each dict has the following keys:
        si_number        str
        finish_time      str | None   (HH:MM:SS)
        punched_tx_count int
        overtime         bool
        raw_status       str | None
        tx_punches       dict[int, str]   {tx_number: "HH:MM:SS"}
    """

    _ENCODINGS = ("utf-8-sig", "cp932", "utf-8")

    def read(self, source: Path | str) -> list[dict[str, Any]]:
        path = Path(source)
        for encoding in self._ENCODINGS:
            try:
                return self._parse(path, encoding)
            except UnicodeDecodeError:
                continue
        raise ValueError(
            f"Could not decode '{path}' with any of {self._ENCODINGS}."
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _parse(self, path: Path, encoding: str) -> list[dict[str, Any]]:
        with path.open(newline="", encoding=encoding) as fh:
            reader = csv.DictReader(fh)
            if reader.fieldnames is None:
                return []
            col_map = _map_columns(list(reader.fieldnames))
            return [
                rec
                for row in reader
                if (rec := _normalise_row(row, col_map)) is not None
            ]


# ---------------------------------------------------------------------------
# Column mapping helpers (module-level so they are easy to unit-test)
# ---------------------------------------------------------------------------

def _map_columns(fieldnames: list[str]) -> dict[str, Any]:
    """Map actual CSV column names to canonical roles.

    Returns a dict with keys:
        "si_number"  → original column name (str) or None
        "finish_time" → original column name (str) or None
        "status"     → original column name (str) or None
        "tx_count"   → original column name (str) or None
        "tx_cols"    → {tx_number (int): original column name (str)}
    """
    result: dict[str, Any] = {
        "si_number": None,
        "finish_time": None,
        "status": None,
        "tx_count": None,
        "tx_cols": {},
    }

    for col in fieldnames:
        norm = col.strip().lower()
        m = _TX_RE.match(norm)
        if m:
            result["tx_cols"][int(m.group(1))] = col
        elif result["si_number"] is None and (
            norm in _SI_CARD_VARIANTS
            or "sino" in norm
            or "siカード" in col.lower()
        ):
            result["si_number"] = col
        elif result["finish_time"] is None and norm in _FINISH_VARIANTS:
            result["finish_time"] = col
        elif result["status"] is None and norm in _STATUS_VARIANTS:
            result["status"] = col
        elif result["tx_count"] is None and norm in _TX_COUNT_VARIANTS:
            result["tx_count"] = col

    return result


def _normalise_row(
    row: dict[str, str],
    col_map: dict[str, Any],
) -> dict[str, Any] | None:
    si_col = col_map["si_number"]
    if si_col is None:
        return None
    si_number = row.get(si_col, "").strip()
    if not si_number:
        return None

    finish_col = col_map["finish_time"]
    finish_time = row.get(finish_col, "").strip() if finish_col else None
    if not finish_time:
        finish_time = None

    status_col = col_map["status"]
    raw_status = row.get(status_col, "").strip() if status_col else None
    if not raw_status:
        raw_status = None

    tx_count_col = col_map["tx_count"]
    tx_count_str = row.get(tx_count_col, "").strip() if tx_count_col else ""
    try:
        punched_tx_count: int = int(tx_count_str)
    except (ValueError, TypeError):
        punched_tx_count = -1  # will be computed from tx_punches below

    tx_punches: dict[int, str] = {}
    for tx_num, col in col_map["tx_cols"].items():
        val = row.get(col, "").strip()
        if val:
            tx_punches[tx_num] = val

    if punched_tx_count < 0:
        punched_tx_count = len(tx_punches)

    overtime = raw_status is not None and (
        "ot" in raw_status.lower()
        or "タイムオーバー" in raw_status
        or "overtime" in raw_status.lower()
    )

    return {
        "si_number": si_number,
        "finish_time": finish_time,
        "punched_tx_count": punched_tx_count,
        "overtime": overtime,
        "raw_status": raw_status,
        "tx_punches": tx_punches,
    }
