"""``gardener``-Backend: FTS5-Suche read-only gegen Gardeners SQLite-DBs.

Schema (verifiziert gegen ``gardener.py`` im Gardener-Repo, Stand 2026-07,
Tabelle ``everything`` + virtuelle FTS5-Tabelle ``everything_fts``):

    everything(id, type, name, content, tags, meta, pinned, created, updated)
    everything_fts(name, content, tags)  -- content=everything, content_rowid=id

Gardener fuehrt zwei Datenbanken im selben Datenverzeichnis:
``gardener.db`` (system) und ``user.db`` (user). Default-Datenverzeichnis wie
in Gardener selbst: ``$GARDENER_DATA`` oder ``~/.gardener``.

Read-only geoeffnet (``mode=ro``) -- dieses Modul schreibt niemals in Gardeners
Datenbanken. Fehlt eine DB-Datei oder existiert die Tabelle noch nicht (leere,
ungeseedete DB), liefert ``search()`` schlicht keine Treffer statt zu
crashen -- siehe README "Abhaengigkeit, die man kennen muss".
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from ..protocol import Hit

_SNIPPET_LIMIT = 240


def _expand(value: Path | str) -> Path:
    """``~`` und ``$VARS`` aufloesen -- Konfigdateien schreiben Pfade so."""
    return Path(os.path.expandvars(os.path.expanduser(str(value))))


class GardenerBackend:
    """Liest Gardeners beide Datenbanken.

    Ueblich reicht ``data_dir`` (beide DBs liegen im selben Verzeichnis).
    ``db_path``/``user_db_path`` setzen die Rollen einzeln -- noetig, wenn die
    System-DB (kuratiertes Wissen, bei Updates ersetzt) und die User-DB
    (Memory/Beobachtungen, nie geteilt) getrennt liegen.
    """

    def __init__(
        self,
        data_dir: Path | str | None = None,
        db_path: Path | str | None = None,
        user_db_path: Path | str | None = None,
    ):
        system = _expand(db_path) if db_path else None
        user = _expand(user_db_path) if user_db_path else None

        if data_dir:
            base = _expand(data_dir)
        elif system is not None:
            # Nur eine der beiden DBs gesetzt: die andere liegt daneben, NICHT
            # im globalen Default. Sonst zoege eine isolierte Instanz (Test,
            # zweite Gardener-Ablage) ungewollt die echte ~/.gardener/user.db
            # mit den privaten Beobachtungen herein.
            base = system.parent
        elif user is not None:
            base = user.parent
        else:
            base = _expand(os.environ.get("GARDENER_DATA", "~/.gardener"))

        self.system_db = system or base / "gardener.db"
        self.user_db = user or base / "user.db"

    def available(self) -> bool:
        return self.system_db.exists() or self.user_db.exists()

    def search(self, query: str, limit: int = 5) -> list[Hit]:
        hits: list[Hit] = []
        for db_path, source_label in (
            (self.user_db, "gardener:user"),
            (self.system_db, "gardener:system"),
        ):
            hits.extend(self._search_db(db_path, source_label, query, limit))

        hits.sort(key=lambda h: h.rank, reverse=True)
        return hits[:limit]

    def _search_db(
        self, db_path: Path, source_label: str, query: str, limit: int
    ) -> list[Hit]:
        if not db_path.exists():
            return []

        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(
                    """
                    SELECT e.name AS name, e.content AS content, e.type AS type,
                           bm25(everything_fts) AS score
                    FROM everything_fts
                    JOIN everything e ON e.id = everything_fts.rowid
                    WHERE everything_fts MATCH ?
                    ORDER BY score
                    LIMIT ?
                    """,
                    (query, limit),
                ).fetchall()
            finally:
                conn.close()
        except sqlite3.Error:
            # Datei existiert, aber Tabelle fehlt/ist kaputt/query ist kein
            # gueltiger FTS5-Ausdruck -- still zurueckfallen, nicht crashen.
            return []

        results = []
        for row in rows:
            # bm25() ist ein negativer Real-Wert, kleiner = relevanter --
            # ein Treffer mit -3.9 ist besser als einer mit -0.5. Auf (0,1)
            # normalisieren, MONOTON STEIGEND mit der Trefferguete, damit
            # min_rank backend-uebergreifend dieselbe Bedeutung hat wie beim
            # files-Backend (dort ``score / (score + 3)``, gleiche Bauart).
            #
            # Frueher stand hier ``1 / (1 + |score|)`` -- das war invertiert:
            # der beste Treffer bekam den niedrigsten Rang, die nachfolgende
            # Sortierung stellte damit die schlechtesten nach oben, und
            # min_rank filterte bevorzugt die besten Treffer weg.
            strength = abs(row["score"])
            rank = strength / (1.0 + strength)
            content = (row["content"] or row["name"] or "").strip()
            results.append(
                Hit(
                    text=content[:_SNIPPET_LIMIT],
                    source=f"{source_label}:{row['name']}",
                    rank=rank,
                    meta={"type": row["type"]},
                )
            )
        return results
