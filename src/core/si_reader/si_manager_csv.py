import csv
from pathlib import Path
from typing import Any

from .base import SIReaderBase


class SIManagerCSVReader(SIReaderBase):
    """Reads SI punch data exported by SI Manager as CSV.

    SI Manager typically exports UTF-8-BOM or CP932 CSV.  We try UTF-8-BOM
    first and fall back to CP932 so users do not have to pre-convert files.
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

    def _parse(self, path: Path, encoding: str) -> list[dict[str, Any]]:
        with path.open(newline="", encoding=encoding) as fh:
            reader = csv.DictReader(fh)
            return [dict(row) for row in reader]
