from __future__ import annotations

import csv
from pathlib import Path

from core.ranking import RankedCompetitor


def export_all(ranked: list[RankedCompetitor], output_dir: Path) -> list[str]:
    """Export four result CSVs to *output_dir*. Returns list of created paths."""
    output_dir.mkdir(parents=True, exist_ok=True)
    return [
        _export_general(ranked, output_dir / "ARDF総合.CSV"),
        _export_region(ranked, output_dir / "ARDF地域.CSV"),
        _export_laps(ranked, output_dir / "総合TX.CSV"),
        _export_award(ranked, output_dir / "賞状.CSV"),
    ]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _write_csv(path: Path, headers: list[str], rows: list[list]) -> str:
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(rows)
    return str(path)


def _export_general(ranked: list[RankedCompetitor], path: Path) -> str:
    """ARDF総合.CSV — all classes, sorted by class then rank."""
    headers = ["順位", "ゼッケン", "コールサイン", "氏名", "クラス",
               "探索TX数", "タイム", "備考"]
    rows = [
        [
            rc.rank or "",
            rc.bib_number,
            rc.call_sign,
            rc.name,
            rc.class_name,
            rc.punched_tx_count if rc.is_ranked else "",
            rc.elapsed_str if rc.is_ranked else "",
            rc.remark,
        ]
        for rc in ranked
    ]
    return _write_csv(path, headers, rows)


def _export_region(ranked: list[RankedCompetitor], path: Path) -> str:
    """ARDF地域.CSV — same columns plus region/prefecture, sorted by region."""
    headers = ["地方", "県", "ゼッケン", "コールサイン", "氏名", "クラス",
               "順位", "探索TX数", "タイム", "備考"]
    rows = sorted(
        [
            [
                rc.region or "",
                rc.prefecture or "",
                rc.bib_number,
                rc.call_sign,
                rc.name,
                rc.class_name,
                rc.rank or "",
                rc.punched_tx_count if rc.is_ranked else "",
                rc.elapsed_str if rc.is_ranked else "",
                rc.remark,
            ]
            for rc in ranked
        ],
        key=lambda r: (r[0], r[1], r[5]),  # region, prefecture, class
    )
    return _write_csv(path, headers, rows)


def _export_laps(ranked: list[RankedCompetitor], path: Path) -> str:
    """総合TX.CSV — per-TX punch times."""
    max_tx = max(
        (max(rc.tx_punches.keys(), default=0) for rc in ranked),
        default=0,
    )
    tx_cols = [f"TX{i}" for i in range(1, max_tx + 1)]
    headers = ["ゼッケン", "コールサイン", "氏名", "クラス"] + tx_cols + ["フィニッシュ"]
    rows = [
        [
            rc.bib_number, rc.call_sign, rc.name, rc.class_name,
            *[rc.tx_punches.get(i, "") for i in range(1, max_tx + 1)],
            rc.finish_time or "",
        ]
        for rc in ranked
    ]
    return _write_csv(path, headers, rows)


def _export_award(ranked: list[RankedCompetitor], path: Path) -> str:
    """賞状.CSV — ranked competitors only, for certificate printing."""
    headers = ["部門", "クラス", "順位", "コールサイン", "氏名", "タイム", "探索TX数"]
    rows = [
        [
            rc.division or "",
            rc.class_name,
            rc.rank,
            rc.call_sign,
            rc.name,
            rc.elapsed_str,
            rc.punched_tx_count,
        ]
        for rc in ranked
        if rc.rank is not None
    ]
    return _write_csv(path, headers, rows)
