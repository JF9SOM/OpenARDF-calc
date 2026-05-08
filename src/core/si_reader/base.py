from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class SIReaderBase(ABC):
    """Abstract base class for SI punch-data readers.

    Subclass this to add new data sources (e.g. direct hardware reading).
    The rest of the application depends only on this interface.
    """

    @abstractmethod
    def read(self, source: Path | str) -> list[dict[str, Any]]:
        """Read SI punch records from *source* and return a list of dicts.

        Each dict represents one competitor's punch record.  The exact keys
        depend on the source format, but callers should normalise them after
        reading.
        """
