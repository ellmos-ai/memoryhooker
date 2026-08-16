"""``usmc``-Backend: read-only Zugriff auf USMCs kuratierte Aggregationen.

USMC (``pip install usmc``, CLI ``usmc``) fuehrt eine eigene SQLite-DB unter
``~/.usmc/usmc_memory.db`` mit drei kuratierten Tabellen -- Fakten, Lessons
Learned und Working Memory (offene Punkte/RESUME-Staende). Dieses Backend
fragt genau diese drei Tabellen ab, nicht ein generisches Volltextmaterial:
das ist der Unterschied zu einer blossen "noch eine Quelle im FTS-Index"-
Anbindung (siehe Ticket T-20260816-972236043) -- USMCs eigene Kuratierung
(Kategorie/Konfidenz bei Fakten, Severity bei Lessons, Prioritaet bei Working
Memory) fliesst direkt in die Rang-Berechnung ein.

Warum sqlite3 direkt und nicht das ``usmc``-Paket (``usmc.api``/
``USMCClient``) oder die ``usmc``-CLI:

- ``USMCClient.__init__`` legt bei fehlendem Pfad das Verzeichnis an
  (``db_path.parent.mkdir(parents=True, exist_ok=True)``) und ruft danach
  ``schema.migrate()`` -> ``init_db()`` -> ``conn.commit()`` auf, falls noch
  keine Schema-Version gesetzt ist. Ein simples Instanziieren des Clients hat
  also einen SCHREIB-Pfad eingebaut -- unvereinbar mit der harten Vorgabe
  "nur lesen, niemals in die USMC-DB schreiben".
- Die CLI muesste denselben Konstruktor durchlaufen (gleiches Risiko) und
  bringt zusaetzlich Prozess-Spawn-Overhead pro Abfrage mit; bei bis zu drei
  Tabellen x mehreren Suchtermen waeren das viele Subprozess-Aufrufe fuer
  eine einzelne ``search()``.

Ein reiner ``mode=ro``-Connect wie hier kann nichts anlegen: eine fehlende
Datei fuehrt zu einem Fehler statt zu einer neu erzeugten DB. Dasselbe Muster
verwendet bereits ``gardener.py`` in diesem Paket fuer eine Schwesterquelle.
Empirisch gegen die reale, WAL-modus-aktive Live-DB verifiziert (2026-08-16):
ein ``mode=ro``-Connect liest den aktuellen Stand korrekt, auch ohne eigene
``-wal``/``-shm``-Dateien im Datenverzeichnis.

Schema (verifiziert gegen ``usmc/schema.py``, Paketversion 0.2.1):

    usmc_facts(id, category, key, value, confidence, source, agent_id,
               created_at, updated_at)
    usmc_lessons(id, category, severity, title, problem, solution, agent_id,
                 is_active, confidence, times_shown, created_at, updated_at)
    usmc_working(id, type, content, priority, tags, agent_id, is_active,
                 created_at, updated_at)

Fehlt die DB-Datei, fehlen die drei Tabellen, oder ist die Datei beschaedigt,
meldet ``available()`` ``False`` bzw. ``search()`` still ``[]`` -- niemals
eine Exception nach aussen (gleiche Regel wie bei allen anderen Backends
dieses Pakets).
"""

from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path

from ..protocol import Hit

_SNIPPET_LIMIT = 240
_SNIPPET_RADIUS = 120

# Mindestlaenge fuer Suchterme; kuerzere Tokens sind fast immer Rauschen.
_MIN_TERM_LENGTH = 3
_TOKEN_PATTERN = re.compile(r"[\w-]+", re.UNICODE)

# Eigene, bewusst kleine Stopwortliste -- an files.py angelehnt, aber lokal
# gehalten statt importiert: jedes Backend in diesem Paket bleibt fuer sich
# lesbar und testbar, ohne stille Kopplung zwischen den Adaptern (gleiche
# Haltung wie gardener.py, das seine eigene OR-Tokenisierung mitbringt statt
# files.py's Tokenizer zu importieren).
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
        "weil", "wenn", "wie", "wir", "wird", "werden", "wo", "zu", "zum",
        "zur",
        # Englisch
        "the", "and", "for", "with", "this", "that", "from", "have",
        "has", "are", "was", "were", "not", "but", "all", "can", "you",
        "your", "its", "our", "their", "them", "they", "what", "which",
        "when", "where", "how", "then", "there", "here", "into", "only",
        "very", "just", "does", "already",
    }
)

_REQUIRED_TABLES = ("usmc_facts", "usmc_lessons", "usmc_working")

# Kuratierungsgewicht je Aggregation, in (0, 1]. Lessons/Facts sind explizit
# geprueftes/bestaetigtes Wissen -- Working Memory ist laut eigener
# Konvention ("Prozess-State gehoert in USMC, nicht in Markdown") der
# fluechtige Sitzungsstand, kein kuratiertes Gedaechtnis. Working Memory
# bekommt deshalb bewusst eine niedrigere Obergrenze als Lessons/Facts,
# nicht weil es unwichtig waere, sondern weil die Eintraege im Schnitt sehr
# lang und unstrukturiert sind (RESUME-Bloecke) -- ein zufaelliger
# Mehrfachtreffer in einem langen Blob soll nicht so hoch werten wie ein
# ebenso starker Treffer in einer kurzen, kuratierten Lesson.
_SEVERITY_WEIGHT = {"critical": 1.0, "high": 0.85, "medium": 0.7, "low": 0.55}
_DEFAULT_SEVERITY_WEIGHT = 0.65
_WORKING_WEIGHT_MIN = 0.25
_WORKING_WEIGHT_MAX = 0.60
_WORKING_PRIORITY_CAP = 10.0


def _expand(value: Path | str) -> Path:
    """``~`` und ``$VARS`` aufloesen -- Konfigdateien schreiben Pfade so."""
    return Path(os.path.expandvars(os.path.expanduser(str(value))))


def _terms_from_query(query: str) -> list[str]:
    """Normalisiert eine Query zu Suchtermen (Kleinschreibung, Mindestlaenge,
    ohne Stopwoerter). Bleibt nichts uebrig, liefert ``search()`` keine
    Treffer statt Vollrauschen -- gleiche Regel wie in ``files.py``."""
    return [
        term
        for term in _TOKEN_PATTERN.findall(query.lower())
        if len(term) >= _MIN_TERM_LENGTH and term not in _STOPWORDS
    ]


def _like_escape(value: str) -> str:
    """Maskiert LIKE-Platzhalter, damit ein Suchterm woertlich gilt."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _match_quality(haystack_lower: str, terms: list[str]) -> tuple[float, list[str]]:
    """Wie stark ein Treffer zur Query passt, als (0, 1].

    Saettigendes Mass ueber die ABSOLUTE Zahl gefundener Terme, nicht ueber
    deren Anteil an der Gesamtquery (dieselbe Bauart wie ``files.py``:
    ``score / (score + 3)``, hier mit Faktor 1 statt 3, weil USMC-Eintraege
    kuerzer und praeziser formuliert sind als Markdown-Memories). Ein
    einzelner generischer Treffer soll nicht reichen, um die Injektionsguete
    zu erreichen; zwei bis drei treffsichere Terme sollen es.
    """
    matched = [t for t in terms if t in haystack_lower]
    if not matched:
        return 0.0, matched
    quality = len(matched) / (len(matched) + 1.0)
    return quality, matched


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


class UsmcBackend:
    """Liest USMCs ``usmc_facts``/``usmc_lessons``/``usmc_working`` read-only."""

    def __init__(self, db_path: Path | str | None = None):
        self.db_path = _expand(db_path) if db_path else _expand("~/.usmc/usmc_memory.db")

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        return conn

    def available(self) -> bool:
        # Schnellpfad zuerst (wie gardener.py): eine fehlende Datei niemals
        # per Connect-Versuch anlegen oder auch nur oeffnen wollen.
        if not self.db_path.exists():
            return False
        try:
            conn = self._connect()
            try:
                rows = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name IN (?, ?, ?)",
                    _REQUIRED_TABLES,
                ).fetchall()
            finally:
                conn.close()
        except sqlite3.Error:
            return False
        # ALLE drei Tabellen muessen existieren -- eine Datei, die zufaellig
        # existiert, aber (noch) kein USMC-Schema traegt, ist kein
        # verfuegbares Backend, sondern die stille "sieht aus wie nichts
        # gefunden"-Falle, die dieses Ticket eigentlich beheben soll.
        return {row["name"] for row in rows} == set(_REQUIRED_TABLES)

    def search(self, query: str, limit: int = 5) -> list[Hit]:
        terms = _terms_from_query(query)
        if not terms or not self.db_path.exists():
            return []

        try:
            conn = self._connect()
        except sqlite3.Error:
            return []

        try:
            hits: list[Hit] = []
            hits.extend(self._search_lessons(conn, terms, limit))
            hits.extend(self._search_facts(conn, terms, limit))
            hits.extend(self._search_working(conn, terms, limit))
        finally:
            conn.close()

        hits.sort(key=lambda h: h.rank, reverse=True)
        return hits[:limit]

    @staticmethod
    def _where_any_term(terms: list[str], columns: tuple[str, ...]) -> tuple[str, list[str]]:
        """``(col1 LIKE ? OR col2 LIKE ? OR ...)`` fuer jeden Term, ODER-verknuepft.

        USMCs eigenes ``--grep`` kennt nur EINEN literalen Teilstring (siehe
        Docstring oben) -- ein ganzer Nutzer-Prompt trifft damit fast nie.
        Diese Methode fragt stattdessen nach JEDEM Term einzeln (SQL-seitig
        als grobe Vorauswahl); wie viele der Terme tatsaechlich vorkommen,
        entscheidet danach ``_match_quality`` in Python -- Python-seitig,
        weil SQLites LIKE Umlaute nicht case-faltet (siehe USMCs eigene
        Doku dazu in ``client.py``), Python's ``str.lower()`` aber schon.
        """
        clauses = []
        params: list[str] = []
        for term in terms:
            like = f"%{_like_escape(term)}%"
            clauses.append("(" + " OR ".join(f"{c} LIKE ? ESCAPE '\\'" for c in columns) + ")")
            params.extend([like] * len(columns))
        return "(" + " OR ".join(clauses) + ")", params

    def _search_lessons(self, conn: sqlite3.Connection, terms: list[str], limit: int) -> list[Hit]:
        where, params = self._where_any_term(terms, ("title", "problem", "solution"))
        try:
            rows = conn.execute(
                f"""
                SELECT id, category, severity, title, problem, solution, agent_id, updated_at
                FROM usmc_lessons
                WHERE is_active = 1 AND {where}
                LIMIT ?
                """,
                (*params, max(limit * 20, 50)),
            ).fetchall()
        except sqlite3.Error:
            return []

        results = []
        for row in rows:
            haystack = f"{row['title']}\n{row['problem']}\n{row['solution']}"
            lowered = haystack.lower()
            quality, matched = _match_quality(lowered, terms)
            if quality <= 0:
                continue
            weight = _SEVERITY_WEIGHT.get(row["severity"], _DEFAULT_SEVERITY_WEIGHT)
            body = _snippet(f"{row['problem']} {row['solution']}", lowered, matched)
            text = f"{row['title']} — {body}"
            results.append(
                Hit(
                    text=text[:_SNIPPET_LIMIT],
                    source=f"usmc:lesson:{row['id']}",
                    rank=min(1.0, quality * weight),
                    meta={"type": "lesson", "severity": row["severity"], "agent_id": row["agent_id"]},
                )
            )
        return results

    def _search_facts(self, conn: sqlite3.Connection, terms: list[str], limit: int) -> list[Hit]:
        where, params = self._where_any_term(terms, ("key", "value"))
        try:
            rows = conn.execute(
                f"""
                SELECT id, category, key, value, confidence, agent_id, updated_at
                FROM usmc_facts
                WHERE {where}
                LIMIT ?
                """,
                (*params, max(limit * 20, 50)),
            ).fetchall()
        except sqlite3.Error:
            return []

        results = []
        for row in rows:
            haystack = f"{row['key']}\n{row['value']}"
            lowered = haystack.lower()
            quality, matched = _match_quality(lowered, terms)
            if quality <= 0:
                continue
            confidence = row["confidence"] if row["confidence"] is not None else 0.0
            weight = 0.5 + 0.45 * max(0.0, min(1.0, confidence))
            text = f"{row['key']}: {row['value']}"
            results.append(
                Hit(
                    text=text[:_SNIPPET_LIMIT],
                    source=f"usmc:fact:{row['category']}/{row['key']}",
                    rank=min(1.0, quality * weight),
                    meta={"type": "fact", "category": row["category"], "confidence": confidence},
                )
            )
        return results

    def _search_working(self, conn: sqlite3.Connection, terms: list[str], limit: int) -> list[Hit]:
        where, params = self._where_any_term(terms, ("content",))
        try:
            rows = conn.execute(
                f"""
                SELECT id, type, content, priority, tags, agent_id, updated_at
                FROM usmc_working
                WHERE is_active = 1 AND {where}
                LIMIT ?
                """,
                (*params, max(limit * 20, 50)),
            ).fetchall()
        except sqlite3.Error:
            return []

        results = []
        for row in rows:
            content = row["content"] or ""
            lowered = content.lower()
            quality, matched = _match_quality(lowered, terms)
            if quality <= 0:
                continue
            priority = row["priority"] if row["priority"] is not None else 0
            priority_norm = max(0.0, min(1.0, priority / _WORKING_PRIORITY_CAP))
            weight = _WORKING_WEIGHT_MIN + (_WORKING_WEIGHT_MAX - _WORKING_WEIGHT_MIN) * priority_norm
            text = _snippet(content, lowered, matched)
            results.append(
                Hit(
                    text=text[:_SNIPPET_LIMIT],
                    source=f"usmc:working:{row['id']}",
                    rank=min(1.0, quality * weight),
                    meta={"type": "working", "priority": priority, "agent_id": row["agent_id"]},
                )
            )
        return results
