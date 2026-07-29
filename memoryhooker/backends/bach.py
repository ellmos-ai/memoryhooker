"""Reserved ``bach`` backend.

The adapter intentionally remains unavailable until a documented read-only API
exists. It never opens a BACH database directly and fails open with no hits.
"""

from __future__ import annotations

from pathlib import Path

from ..protocol import Hit


class BachBackend:
    def __init__(self, api_path: Path | str | None = None):
        self.api_path = Path(api_path) if api_path else None

    def available(self) -> bool:
        # Enable only after a documented read-only API and contract tests exist.
        return False

    def search(self, query: str, limit: int = 5) -> list[Hit]:
        return []
