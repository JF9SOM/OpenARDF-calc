"""Reader for the headerless SI Manager CSV format used by ARDF SI software.

Format (no header row, CRLF line endings):
  col 0 : SI card number, 5 digits (may be empty)
  col 1 : SI card number with prefix, 6-7 digits
  col 2 : readout datetime  "YYYY/MM/DD HH:MM:SS"
  col 3 : absolute start time  "HH:MM:SS" (often empty)
  col 4 : elapsed start time   "H:MM:SS"  (often empty)
  col 5 : unknown / empty
  col 6 : elapsed finish time  "H:MM:SS"  (empty if not finished)
  col 7-9 : name fields (ignored)
  col 10+ : pairs (control_number, elapsed_time) repeating

Competitor matching: SI card last-2-digits (stripped of leading zero)
== SI No in the participant CSV.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any

from .base import SIReaderBase

_TIME_RE = re.compile(r"^\d{1,2}:\d{2}:\d{2}$")
_DATETIME_RE = re.compile(r"^\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}$")


def _is_raw_format(path: Path) -> bool:
    """Return True when the file looks like the headerless ARDF-SI raw format."""
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            with path.open(newline="", encoding=enc) as fh:
                first = next(csv.reader(fh), None)
            if first is None:
                return False
            # Header rows contain text labels; raw rows start with digits or empty
            col0 = first[0].strip() if first else ""
            col1 = first[1].strip() if len(first) > 1 else ""
            return col0.isdigit() or (col0 == "" and col1.isdigit())
        except (UnicodeDecodeError, StopIteration):
            continue
    return False


def _si_number_key(si_card: str) -> str:
    """Convert a raw SI card number to the 'SI No' key used in the competitor table.

    Rule: last two characters stripped of a leading zero.
    Examples: '38503' → '3', '38510' → '10', '38501' → '1'
    """
    last2 = si_card[-2:].lstrip("0")
    return last2 if last2 else "0"


def _hms_to_seconds(hms: str) -> int:
    h, m, s = hms.split(":")
    return int(h) * 3600 + int(m) * 60 + int(s)


class ARDFSIRawCSVReader(SIReaderBase):
    """Reads the headerless ARDF-SI Manager CSV export format."""

    _ENCODINGS = ("utf-8-sig", "utf-8", "cp932")

    def read(self, source: Path | str) -> list[dict[str, Any]]:
        path = Path(source)
        for enc in self._ENCODINGS:
            try:
                return self._parse(path, enc)
            except UnicodeDecodeError:
                continue
        raise ValueError(f"Could not decode '{path}'")

    def _parse(self, path: Path, encoding: str) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        with path.open(newline="", encoding=encoding) as fh:
            for row in csv.reader(fh):
                rec = _parse_row(row)
                if rec is not None:
                    results.append(rec)
        return results


def _parse_row(row: list[str]) -> dict[str, Any] | None:
    if len(row) < 2:
        return None

    # Determine SI card number
    col0 = row[0].strip()
    col1 = row[1].strip() if len(row) > 1 else ""

    si_card = col0 if col0.isdigit() else (col1 if col1.isdigit() else "")
    if not si_card:
        return None

    si_number = _si_number_key(si_card)

    # col 6: finish time relative to SI zero (SI基準時刻からの経過)
    col6_time: str | None = None
    if len(row) > 6:
        ft = row[6].strip()
        if _TIME_RE.match(ft):
            col6_time = ft

    # col 10+: pairs of (control_number, elapsed_time)
    all_punches: dict[int, str] = {}
    idx = 10
    while idx + 1 < len(row):
        ctrl = row[idx].strip()
        time = row[idx + 1].strip()
        if ctrl.isdigit() and _TIME_RE.match(time):
            all_punches[int(ctrl)] = time
        idx += 2

    # The finish control is the punch whose time is closest to col6 (readout time).
    # Identify it and remove it from tx_punches so it isn't counted as a TX.
    # col6 itself is the official finish time used for elapsed calculation.
    tx_punches = dict(all_punches)
    if col6_time and all_punches:
        col6_sec = _hms_to_seconds(col6_time)
        finish_ctrl = min(
            all_punches,
            key=lambda c: abs(col6_sec - _hms_to_seconds(all_punches[c])),
        )
        del tx_punches[finish_ctrl]

    return {
        "si_number": si_number,
        "si_card_full": si_card,
        "finish_time": col6_time,        # col6 = SI基準時刻からの経過時間（公式タイムの基準）
        "time_format": "si_relative",    # DAOに si_zero + finish - group_start で計算させる
        "punched_tx_count": len(tx_punches),
        "overtime": False,               # DAOで制限時間と比較して上書き
        "raw_status": None,
        "tx_punches": tx_punches,
    }
