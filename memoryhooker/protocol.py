"""Schmales Protokoll fuer Memory-Backends und der gemeinsame Treffer-Typ.

Siehe README.md, Abschnitt "Nutzerneutral: Backend austauschbar". MemoryHooker
schreibt keinem Backend vor, wie es intern sucht -- nur wie es antwortet.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class Hit:
    """Ein einzelner Suchtreffer aus einem :class:`MemoryBackend`.

    ``rank`` ist auf ``(0, 1]`` normalisiert -- ``1.0`` steht fuer den
    bestmoeglichen Treffer. Jeder Backend-Adapter bildet seine eigene
    Scoring-Groesse (z. B. FTS5-bm25, Termfrequenz) auf diesen gemeinsamen
    Massstab ab, damit ``min_rank`` aus der Config backend-uebergreifend
    dieselbe Bedeutung hat.
    """

    text: str
    source: str
    rank: float
    meta: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class MemoryBackend(Protocol):
    """Protokoll, hinter dem jedes Gedaechtnis-Backend steckt.

    ``available()`` ist eine bewusste Ergaenzung zum README-Entwurf
    (``search()`` allein): ein fehlendes Backend (leere DB, kein pip-Install,
    Datei nicht vorhanden) muss sich still zurueckziehen koennen, statt eine
    Exception zu werfen -- "Ein fehlender MCP-Server darf nie ein Fehler
    sein" gilt hier analog fuer Memory-Backends.
    """

    def search(self, query: str, limit: int = 5) -> list[Hit]:
        ...

    def available(self) -> bool:
        ...
