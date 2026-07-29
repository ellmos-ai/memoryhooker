"""Backend-Adapter fuer MemoryHooker.

``build_backend()`` ist die Fabrik, die anhand von ``Config.backend`` den
passenden Adapter erzeugt. Sie wirft nie wegen eines fehlenden Speicherorts
(z. B. Gardener-DB nicht vorhanden) -- das ist Sache von ``available()`` auf
dem jeweiligen Adapter, nicht der Fabrik.

Steht in der Config eine ``order``-Kette, liefert die Fabrik einen
:class:`ChainBackend`, der alle verfuegbaren Glieder befragt und die Treffer
nach ``rank`` zusammenfuehrt. Das ist zulaessig, weil ``rank`` laut
``protocol.Hit`` backend-uebergreifend auf ``(0, 1]`` normalisiert ist.
"""

from __future__ import annotations

from ..config import Config
from ..protocol import Hit, MemoryBackend
from .bach import BachBackend
from .files import FilesBackend
from .gardener import GardenerBackend
from .usmc import UsmcBackend

__all__ = [
    "Hit",
    "MemoryBackend",
    "FilesBackend",
    "GardenerBackend",
    "UsmcBackend",
    "BachBackend",
    "ChainBackend",
    "build_backend",
]


class ChainBackend:
    """Mehrere Backends als eines.

    ``search()`` fragt jedes **verfuegbare** Glied und fuehrt die Treffer
    zusammen, absteigend nach ``rank``. Die Sortierung ist stabil: bei
    gleichem Rang gewinnt das Glied, das in der Kette weiter vorn steht.

    Ein Glied, das nicht verfuegbar ist oder beim Suchen scheitert, wird
    uebersprungen -- eine kaputte Quelle darf die uebrigen nie mitreissen.
    """

    def __init__(self, backends: list[MemoryBackend]):
        self._backends = list(backends)

    @property
    def backends(self) -> tuple[MemoryBackend, ...]:
        return tuple(self._backends)

    def available(self) -> bool:
        return any(self._safe_available(b) for b in self._backends)

    def search(self, query: str, limit: int = 5) -> list[Hit]:
        merged: list[Hit] = []
        for backend in self._backends:
            if not self._safe_available(backend):
                continue
            try:
                merged.extend(backend.search(query, limit))
            except Exception:
                continue
        merged.sort(key=lambda hit: hit.rank, reverse=True)
        return merged[:limit]

    @staticmethod
    def _safe_available(backend: MemoryBackend) -> bool:
        try:
            return bool(backend.available())
        except Exception:
            return False

    def __repr__(self) -> str:  # pragma: no cover - Diagnosehilfe
        names = ", ".join(type(b).__name__ for b in self._backends)
        return f"ChainBackend({names})"


def _build_one(kind: str, options: dict) -> MemoryBackend:
    """Ein einzelnes Backend aus seinem Namen und seinen Optionen."""
    path = options.get("path")

    if kind == "files":
        return FilesBackend(path, roots=options.get("paths"))
    if kind == "gardener":
        return GardenerBackend(
            options.get("data_dir") or path,
            db_path=options.get("db_path"),
            user_db_path=options.get("user_db_path"),
        )
    if kind == "usmc":
        return UsmcBackend(options.get("db_path") or path)
    if kind == "bach":
        return BachBackend(options.get("api_path") or path)

    raise ValueError(f"unbekanntes Backend: {kind!r}")


def build_backend(config: Config) -> MemoryBackend:
    chain = config.backend.chain()

    if len(chain) == 1:
        return _build_one(chain[0], config.backend.options_for(chain[0]))

    return ChainBackend(
        [_build_one(kind, config.backend.options_for(kind)) for kind in chain]
    )
