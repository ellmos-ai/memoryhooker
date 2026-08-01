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

# Gardener trennt Gedaechtnis von Material: recall() dort schoepft nur aus
# memory/lesson/session, find() aus allem. Wer wie hier direkt an die DB geht,
# muss diese Trennung selbst ziehen -- sonst konkurriert Rohmaterial mit dem
# kuratierten Gedaechtnis um die wenigen Injektionsplaetze.
#
# Ausgeschlossen wird NICHT der Typ `observed` als Ganzes: dort liegen auch
# Skills, Regeldateien und die Lesson-Tabellen anderer Werkzeuge, und die sind
# als Hinweis wertvoll. Ausgeschlossen werden gezielt Gespraechstranskripte --
# auf ASUS-GEI am 2026-08-01 gemessen 11.835 von 14.251 observed-Eintraegen
# (83%). Ein Transkript ist ein abgeschnittener Gespraechsfetzen aus einer
# Altsitzung; als eingeblendeter Hinweis ist er fast immer Rauschen.
DEFAULT_INCLUDE_TYPES = ("memory", "lesson", "session", "knowledge", "observed")
DEFAULT_EXCLUDE_TAGS = ("agent_transcript",)


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
        include_types: tuple[str, ...] | list[str] | None = None,
        exclude_tags: tuple[str, ...] | list[str] | None = None,
    ):
        # Beide Filter sind bewusst ueberschreibbar: Wer die Transkripte doch
        # durchsuchen will, setzt `exclude_tags = []` in der Konfiguration.
        self.include_types = tuple(include_types) if include_types is not None else DEFAULT_INCLUDE_TYPES
        self.exclude_tags = tuple(exclude_tags) if exclude_tags is not None else DEFAULT_EXCLUDE_TAGS

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

    @staticmethod
    def _oder_query(query: str) -> str | None:
        """Mehrwort-Query als FTS5-ODER-Verknuepfung, sonst ``None``.

        FTS5 verknuepft die Woerter einer MATCH-Query mit UND. Ein echter
        Nutzer-Prompt ist aber ein ganzer Satz -- "wie setze ich einen lock
        richtig?" verlangt dann ein Dokument, das ALLE diese Woerter enthaelt,
        Fragezeichen und Fuellwoerter eingeschlossen. Praktisch findet das nie
        etwas: Gemessen am 2026-08-01 lieferte genau dieser Prompt aus dem
        Gardener-Backend null Treffer, waehrend das schwaechere files-Backend
        die Injektion allein bestritt.

        Gardener selbst loest das seit 2026-07-30 mit demselben Verfahren
        (``_build_fts_or_query``); dieses Backend geht an Gardeners Suche
        vorbei direkt an die DB und muss es deshalb selbst mitbringen.
        Explizite Operatoren und Phrasen bleiben unangetastet -- wer sie
        schreibt, meint sie.
        """
        if '"' in query or any(
            op in query.upper().split() for op in ("OR", "AND", "NOT", "NEAR")
        ):
            return None
        worte = [w.strip() for w in query.split() if w.strip()]
        if len(worte) <= 1:
            return None
        return " OR ".join(f'"{w}"' for w in worte)

    def search(self, query: str, limit: int = 5) -> list[Hit]:
        hits = self._sammeln(query, limit)
        if not hits:
            # Erst die strenge UND-Suche, dann die ODER-Variante: Ein Treffer,
            # der alle Begriffe enthaelt, ist der bessere -- die Lockerung
            # greift nur, wenn es ihn nicht gibt.
            oder = self._oder_query(query)
            if oder:
                hits = self._sammeln(oder, limit)
        hits.sort(key=lambda h: h.rank, reverse=True)
        return self._entdoppeln(hits)[:limit]

    def _sammeln(self, match_query: str, limit: int) -> list[Hit]:
        hits: list[Hit] = []
        for db_path, source_label in (
            (self.user_db, "gardener:user"),
            (self.system_db, "gardener:system"),
        ):
            hits.extend(self._search_db(db_path, source_label, match_query, limit))
        return hits

    @staticmethod
    def _sprachneutraler_name(source: str) -> str:
        """Quellname ohne Sprachkennung, als Dedup-Schluessel.

        ``SKILL.md``, ``SKILL.fr.md`` und ``README_de.md`` sind Fassungen
        DESSELBEN Inhalts. Ihre Texte unterscheiden sich, der Text-Vergleich
        greift also nicht -- als Hinweis sind sie dennoch austauschbar, und
        wer sie alle einblendet, verschenkt Plaetze. Gemessen 2026-08-01:
        drei von neun Treffern einer Stichprobe waren Uebersetzungen bereits
        gelisteter Eintraege.
        """
        teile = source.rsplit("/", 2)
        name = teile[-1]
        stamm = name[: -len(".md")] if name.endswith(".md") else name
        # Sprachkennung als Endung (SKILL.fr) oder mit Unterstrich (README_de)
        for trenner in (".", "_"):
            kopf, sep, schwanz = stamm.rpartition(trenner)
            if sep and 2 <= len(schwanz) <= 3 and schwanz.isalpha() and schwanz.islower():
                stamm = kopf
                break
        # Nur der UNMITTELBARE Elternordner zaehlt, nicht der ganze Pfad:
        # Dieselbe Einheit liegt oft an zwei Stellen -- ein Skill sowohl in
        # der Bibliothek als auch deployt, oder derselbe Skill unter zwei
        # Kategorien (gemessen 2026-08-01: `surface-after-care` liegt unter
        # `dev/` UND unter `infrastructure/`). Der Elternordner ist bei
        # solchen Ablagen die tragende Identitaet, der Pfad davor nicht.
        elternordner = teile[-2] if len(teile) > 1 else ""
        return f"{elternordner}/{stamm}".lower()

    @classmethod
    def _entdoppeln(cls, hits: list[Hit]) -> list[Hit]:
        """Denselben Inhalt nur einmal -- der bestplatzierte gewinnt.

        Zwei Wege, wie derselbe Hinweis mehrfach auftaucht:
        - **Gleicher Text:** dieselbe Datei ueber zwei observe-Quellen
          indexiert, oder eine Datei, die an zwei Orten liegt.
        - **Gleicher Inhalt, andere Sprache:** ``SKILL.md`` neben
          ``SKILL.fr.md`` (siehe ``_sprachneutraler_name``).

        Ohne diesen Schritt belegen die wenigen Injektionsplaetze mehrfach
        denselben Hinweis.
        """
        gesehen_text: set[str] = set()
        gesehen_quelle: set[str] = set()
        eindeutig: list[Hit] = []
        for hit in hits:
            text_schluessel = " ".join((hit.text or "").split()).lower()
            quell_schluessel = cls._sprachneutraler_name(hit.source or "")
            if text_schluessel and text_schluessel in gesehen_text:
                continue
            if quell_schluessel and quell_schluessel in gesehen_quelle:
                continue
            gesehen_text.add(text_schluessel)
            gesehen_quelle.add(quell_schluessel)
            eindeutig.append(hit)
        return eindeutig

    def _search_db(
        self, db_path: Path, source_label: str, query: str, limit: int
    ) -> list[Hit]:
        if not db_path.exists():
            return []

        bedingungen = ["everything_fts MATCH ?"]
        parameter: list[object] = [query]
        if self.include_types:
            platzhalter = ", ".join("?" for _ in self.include_types)
            bedingungen.append(f"e.type IN ({platzhalter})")
            parameter.extend(self.include_types)
        for tag in self.exclude_tags:
            bedingungen.append("COALESCE(e.tags, '') NOT LIKE ?")
            parameter.append(f"%{tag}%")

        # Mehr Zeilen holen als gebraucht: Nach dem Entdoppeln in search()
        # sollen noch `limit` Treffer uebrig bleiben. Der Faktor ist eine
        # Reserve, keine Garantie -- bei sehr vielen Doubletten kommen
        # entsprechend weniger Treffer zurueck, und das ist richtig so.
        parameter.append(max(limit * 4, limit))

        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(
                    f"""
                    SELECT e.name AS name, e.content AS content, e.type AS type,
                           bm25(everything_fts) AS score
                    FROM everything_fts
                    JOIN everything e ON e.id = everything_fts.rowid
                    WHERE {' AND '.join(bedingungen)}
                    ORDER BY score
                    LIMIT ?
                    """,
                    parameter,
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
