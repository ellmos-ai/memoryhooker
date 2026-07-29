"""Reserved ``usmc`` backend.

The adapter intentionally remains unavailable until a documented read-only
contract exists. Backend chains therefore fail open to another source.
"""

from __future__ import annotations

import os
from pathlib import Path

from ..protocol import Hit


class UsmcBackend:
    def __init__(self, db_path: Path | str | None = None):
        self.db_path = Path(db_path) if db_path else Path(
            os.path.expanduser("~/.usmc/usmc_memory.db")
        )

    def available(self) -> bool:
        # Enable only after a documented read-only API and contract tests exist.
        return False

    def search(self, query: str, limit: int = 5) -> list[Hit]:
        return []
