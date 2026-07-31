"""``files``-Backend: durchsucht Markdown-Memories im Dateisystem.

Zero-Dependency-Fallback -- funktioniert ohne DB, ohne Gardener, ohne USMC.
Naive Termfrequenz-Suche, keine echte FTS. Fuer das MVP bewusst so simpel
gehalten: der Sinn ist ein Backend, das *immer* funktioniert, wenn ein
Verzeichnis mit ``.md``-Dateien existiert.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..protocol import Hit

_SNIPPET_RADIUS = 120

# Mindestlaenge fuer Suchterme; kuerzere Tokens sind fast immer Rauschen.
_MIN_TERM_LENGTH = 3

# Wortzeichen (inkl. Umlaute) und Bindestrich -- Satzzeichen fallen so
# beim Tokenisieren automatisch weg (".TOPICS," -> "TOPICS").
_TOKEN_PATTERN = re.compile(r"[\w-]+", re.UNICODE)

# Stopwoerter Deutsch + Englisch: Fuellwoerter ohne Eigeninfo. Als Suchterm
# treffen sie per Substr-Match fast jeden Text ("fuer" in "Verfuegung")
# und dominieren das Ranking. Wartbar als Modul-Konstante.
_STOPWORDS = frozenset(
    {
        # Deutsch
        "aber", "alle", "als", "am", "an", "auch", "auf", "aus", "bei",
        "beim", "bin", "bis", "da", "dann", "das", "dass", "dem", "den",
        "der", "des", "die", "dies", "diese", "dieser", "du", "durch",
        "ein", "eine", "einem", "einen", "einer", "er", "es", "für",
        "fuer", "habe", "haben", "hat", "ich", "ihm", "ihn", "ihr",
        "ihre", "im", "in", "ins", "ist", "kein", "keine", "man", "mein",
        "meine", "mit", "nach", "nicht", "noch", "nur", "ob", "oder",
        "ohne", "sein", "seine", "sich", "sie", "sind", "so", "über",
        "ueber", "um", "und", "uns", "vom", "von", "vor", "war", "was",
        "weil", "wenn", "wie", "wir", "wird", "wo", "zu", "zum", "zur",
        # Englisch
        "the", "and", "for", "with", "this", "that", "from", "have",
        "has", "are", "was", "were", "not", "but", "all", "can", "you",
        "your", "its", "our", "their", "them", "they", "what", "which",
        "when", "where", "how", "then", "there", "here", "into", "only",
        "very", "just",
    }
)


class FilesBackend:
    """Sucht in ``*.md``-Dateien unterhalb eines oder mehrerer Wurzeln."""

    def __init__(
        self,
        root: Path | str | None = None,
        *,
        roots: list[Path | str] | tuple[Path | str, ...] | None = None,
    ):
        values = list(roots or ())
        if root:
            values.insert(0, root)
        self.roots = tuple(Path(value).expanduser() for value in values if value)
        # Kompatibilität für bisherige Aufrufer und Diagnosecode.
        self.root = self.roots[0] if self.roots else None

    def available(self) -> bool:
        return any(root.is_dir() for root in self.roots)

    def search(self, query: str, limit: int = 5) -> list[Hit]:
        if not self.available():
            return []

        terms = _terms_from_query(query)
        if not terms:
            return []

        hits: list[Hit] = []
        seen: set[Path] = set()
        for root in self.roots:
            if not root.is_dir():
                continue
            for path in sorted(root.rglob("*.md")):
                try:
                    resolved = path.resolve()
                except OSError:
                    resolved = path.absolute()
                if resolved in seen:
                    continue
                seen.add(resolved)
                try:
                    text = path.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue

                lowered = text.lower()
                score = sum(lowered.count(term) for term in terms)
                if score == 0:
                    continue

                # Sanftes Sättigungsmaß statt reinem Zählwert.
                rank = score / (score + 3)
                snippet = _snippet(text, lowered, terms)
                hits.append(
                    Hit(
                        text=snippet,
                        source=str(path.relative_to(root)),
                        rank=rank,
                        meta={"path": str(path), "root": str(root)},
                    )
                )

        hits.sort(key=lambda h: h.rank, reverse=True)
        return hits[:limit]


def _terms_from_query(query: str) -> list[str]:
    """Normalisiert eine Query zu Suchtermen.

    Kleinschreibung, Satzzeichen gestrippt, Mindestlaenge 3, Stopwoerter
    raus. Bleibt kein Term uebrig (leere oder reine Fuellwort-Query),
    liefert ``search()`` keine Treffer statt Vollrauschen.
    """
    return [
        term
        for term in _TOKEN_PATTERN.findall(query.lower())
        if len(term) >= _MIN_TERM_LENGTH and term not in _STOPWORDS
    ]


def _snippet(text: str, lowered: str, terms: list[str]) -> str:
    for term in terms:
        idx = lowered.find(term)
        if idx == -1:
            continue
        start = max(0, idx - _SNIPPET_RADIUS)
        end = min(len(text), idx + len(term) + _SNIPPET_RADIUS)
        prefix = "…" if start > 0 else ""
        suffix = "…" if end < len(text) else ""
        return (prefix + text[start:end].strip() + suffix).replace("\n", " ")
    return text[: 2 * _SNIPPET_RADIUS].strip().replace("\n", " ")
