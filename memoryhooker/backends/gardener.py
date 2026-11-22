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
import re
import sqlite3
import unicodedata
from pathlib import Path

from ..protocol import Hit

_SNIPPET_LIMIT = 240
_MIN_TERM_LENGTH = 3
_BM25_K_SINGLE = 2.5
_BM25_K_MULTI = 10.0

# Wortzeichen ohne Unterstrich -- entspricht FTS5 ``unicode61``-Tokenisierung,
# sodass ``RH/abc:``, ``Ticket-Auftrag`` und ``codex_companion`` sauber in
# Einzelterme zerlegt werden ohne FTS5-Syntaxfehler auszuloesen.
_TOKEN_PATTERN = re.compile(r"[^\W_]+", re.UNICODE)
_FTS5_OPERATORS = frozenset({"OR", "AND", "NOT", "NEAR"})

# Deutsche und englische Stopp- und Fuellwoerter ohne fachlichen Kern.
# Verhindert, dass die ODER-Lockerung bei umgangssprachlichen Prompts ueber
# Allerweltswoerter wie "wie", "hast", "du", "und", "fuer", "lesen", "ideen"
# fachfremde Treffer anzieht.
_STOPWORDS_DE = frozenset(
    {
        # Deutsch: Artikel, Pronomen, Praepositionen, Konjunktionen, Hilfs-/Modalverben, Fuellwoerter
        "aber", "alle", "allem", "allen", "aller", "alles", "als", "also",
        "am", "an", "andere", "anderem", "anderen", "anderer", "anderes",
        "auch", "auf", "aus", "bei", "beim", "bin", "bis", "bist", "bitte",
        "da", "dabei", "dadurch", "dafuer", "dafür", "dagegen", "daher",
        "damit", "danach", "dann", "daran", "darauf", "daraus", "darin",
        "darum", "das", "dass", "davon", "dazu", "dein", "deine", "deinem",
        "deinen", "deiner", "deines", "dem", "den", "denn", "der", "des",
        "dessen", "dich", "die", "dies", "diese", "diesem", "diesen",
        "dieser", "dieses", "dir", "doch", "dort", "du", "durch", "eben",
        "eigentlich", "ein", "eine", "einem", "einen", "einer", "eines",
        "einige", "einmal", "er", "erst", "es", "etwa", "etwas", "euch",
        "euer", "eure", "fuer", "für", "ganz", "gar", "gegen", "gehabt",
        "gemacht", "genau", "gerade", "gern", "gerne", "gewesen", "gibt",
        "hab", "habe", "haben", "habt", "hast", "hat", "hatte", "hatten",
        "her", "hier", "hin", "hinter", "ich", "idee", "ideen", "ihm",
        "ihn", "ihnen", "ihr", "ihre", "ihrem", "ihren", "ihrer", "ihres",
        "im", "immer", "in", "indem", "ins", "ist", "ja", "je", "jede",
        "jedem", "jeden", "jeder", "jedes", "jedoch", "jetzt", "kann",
        "kannst", "kein", "keine", "keinem", "keinen", "keiner", "keines",
        "koennen", "können", "koennt", "könnt", "konnte", "konnten",
        "lassen", "lesen", "machen", "macht", "mal", "man", "mehr", "mein",
        "meine", "meinem", "meinen", "meiner", "meines", "mich", "mir",
        "mit", "muss", "musst", "muessen", "müssen", "nach", "nachdem",
        "nein", "nicht", "nichts", "nie", "noch", "nun", "nur", "ob",
        "oder", "ohne", "pruefen", "prüfen", "schon", "sehr", "sei",
        "seid", "sein", "seine", "seinem", "seinen", "seiner", "seines",
        "seit", "selbst", "sich", "sie", "sind", "so", "sogar", "solch",
        "solche", "soll", "sollen", "sollst", "sollt", "sollte", "sollten",
        "sondern", "sonst", "sowie", "ueber", "über", "um", "und", "uns",
        "unser", "unsere", "unserem", "unseren", "unserer", "unter",
        "viel", "viele", "vielleicht", "vom", "von", "vor", "wann", "war",
        "waren", "warst", "warum", "was", "weder", "wegen", "weil",
        "weiter", "welche", "welchem", "welchen", "welcher", "welches",
        "wem", "wen", "wenig", "wenn", "wer", "werde", "werden", "werdet",
        "weshalb", "wie", "wieder", "wieso", "will", "willst", "wir",
        "wird", "wirklich", "wirst", "wo", "woher", "wohin", "wollen",
        "wollt", "wollte", "wollten", "worden", "wurde", "wurden",
        "zurechtgefunden", "zusammen", "zwar", "zwischen",
    }
)

_STOPWORDS_EN = frozenset(
    {
        # Englisch
        "about", "above", "actually", "after", "again", "against", "all",
        "already", "also", "always", "am", "an", "and", "any", "are",
        "as", "at", "be", "because", "been", "before", "being", "below",
        "between", "both", "but", "by", "can", "could", "did", "do",
        "does", "doing", "done", "down", "during", "each", "ever", "few",
        "for", "from", "further", "had", "has", "have", "having", "he",
        "hello", "her", "here", "hers", "herself", "him", "himself", "his",
        "how", "however", "if", "in", "into", "is", "it", "its", "itself",
        "just", "many", "may", "me", "might", "more", "most", "much",
        "must", "my", "myself", "never", "no", "nor", "not", "now", "of",
        "off", "often", "on", "once", "only", "or", "other", "our", "ours",
        "ourselves", "out", "over", "own", "please", "really", "same",
        "she", "should", "since", "so", "some", "still", "such", "than",
        "thanks", "that", "the", "their", "theirs", "them", "themselves",
        "then", "there", "these", "they", "this", "those", "through", "to",
        "too", "under", "until", "up", "very", "was", "we", "well", "were",
        "what", "when", "where", "which", "while", "who", "whom", "why",
        "will", "with", "would", "yet", "you", "your", "yours", "yourself",
        "yourselves",
    }
)

_STOPWORDS = _STOPWORDS_DE | _STOPWORDS_EN

# Gardener trennt kuratiertes Gedaechtnis von Rohmaterial (`recall()` schoepft
# nur aus memory/lesson/session, `find()` aus allem inkl. `observed`).
# Automatische Hook-Injektion darf per Default KEINE `observed`-Eintraege
# (private Notizen/wissen-summaries, usmc-working AUTO-STATE, Transkripte)
# in fremde Sitzungen einspielen. Wer `observed` ausdruecklich durchsuchen
# will, setzt `include_types` explizit in der Konfiguration; in diesem Opt-in-
# Fall bleiben Gespraechstranskripte weiterhin durch `DEFAULT_EXCLUDE_TAGS`
# ausgeblendet.
DEFAULT_INCLUDE_TYPES = ("memory", "lesson", "session", "knowledge")
DEFAULT_EXCLUDE_TAGS = ("agent_transcript",)


def _fold_text(text: str) -> str:
    """Normalisiert Gross-/Kleinschreibung und Diakritika wie FTS5 ``unicode61``."""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _is_explicit_fts_query(query: str) -> bool:
    """Erkennt explizite FTS5-Phrasen, Operatoren oder Prefix-Wildcards."""
    if '"' in query:
        return True
    return any(
        token in _FTS5_OPERATORS or token.startswith("NEAR/") or "*" in token
        for token in query.split()
    )


def _extract_terms(query: str) -> list[str]:
    """Extrahiert deduplizierte signifikante Suchterme ohne Stopp-/Fuellwoerter."""
    seen: set[str] = set()
    terms: list[str] = []
    for raw_token in _TOKEN_PATTERN.findall(query):
        token = raw_token.casefold()
        if len(token) < _MIN_TERM_LENGTH or token in _STOPWORDS:
            continue
        folded = _fold_text(token)
        if folded in _STOPWORDS or folded in seen:
            continue
        seen.add(folded)
        terms.append(token)
    return terms


def _extract_explicit_terms(query: str) -> list[str]:
    """Extrahiert Suchwoerter aus expliziten FTS5-Ausdruecken fuer die Abdeckung."""
    seen: set[str] = set()
    terms: list[str] = []
    for raw_token in _TOKEN_PATTERN.findall(query):
        if raw_token in _FTS5_OPERATORS or raw_token == "NEAR":
            continue
        token = raw_token.casefold()
        folded = _fold_text(token)
        if not folded or folded in seen:
            continue
        seen.add(folded)
        terms.append(token)
    return terms


def _matched_term_count(haystack: str, query_terms: list[str]) -> int:
    """Zaehlt, wie viele der signifikanten Suchterme im Treffer vorkommen."""
    if not query_terms:
        return 1
    haystack_tokens = set(_TOKEN_PATTERN.findall(_fold_text(haystack)))
    matched = sum(1 for term in query_terms if _fold_text(term) in haystack_tokens)
    return max(1, matched)


def _calibrate_rank(strength: float, matched_terms: int, total_terms: int) -> float:
    """Kalibriert FTS5-BM25 in ``(0, 1]`` ueber Termabdeckung und BM25-Saettigung.

    Im Gegensatz zu ``|bm25| / (1 + |bm25|)`` (saettigt bei grossen Korpora
    sofort bei 0.83..0.99) kombiniert die Kalibrierung:
    - bei Einzelwort-Queries (``total_terms <= 1``): gedehnte BM25-Saettigung
      (``k = 2.5``) mit Basis ``0.35``;
    - bei Mehrwort-Queries (``total_terms >= 2``): Anteil und Anzahl der
      tatsaechlich getroffenen Suchterme plus gedaempfte BM25-Saettigung
      (``k = 10.0``). Reine Einzelwort-Zufallstreffer (``matched_terms == 1``)
      werden stark abgewertet und bleiben mathematisch unter ``min_rank = 0.5``
      (maximal ~0.34).
    """
    if total_terms <= 1:
        bm25_sat = strength / (_BM25_K_SINGLE + strength)
        raw = 0.35 + 0.65 * bm25_sat
    else:
        coverage = min(1.0, matched_terms / total_terms)
        term_signal = matched_terms / (matched_terms + 1.0)
        multi_cov = 0.4 * coverage + 0.6 * term_signal
        bm25_sat = strength / (_BM25_K_MULTI + strength)
        raw = 0.75 * multi_cov + 0.25 * bm25_sat
        if matched_terms <= 1:
            raw *= 0.55
    return min(1.0, max(1e-6, raw))


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
        """Mehrwort-Query ohne Stopp-/Fuellwoerter als FTS5-ODER-Verknuepfung.

        FTS5 verknuepft die Woerter einer MATCH-Query mit UND. Ein echter
        Nutzer-Prompt ist aber ein ganzer Satz -- "wie setze ich einen lock
        richtig?" verlangt dann ein Dokument, das ALLE diese Woerter enthaelt,
        Fragezeichen und Fuellwoerter eingeschlossen.

        Vor dem Bau der ODER-Query werden Satzzeichen, kurze Tokens (< 3)
        sowie deutsche und englische Stopp-/Fuellwoerter entfernt, damit
        einzelne Allerweltswoerter ("wie", "hast", "du", "und", "fuer",
        "lesen", "ideen") keine fachfremden Treffer anziehen. Explizite
        FTS5-Operatoren und Phrasen bleiben unangetastet.
        """
        if _is_explicit_fts_query(query):
            return None
        worte = _extract_terms(query)
        if len(worte) <= 1:
            return None
        return " OR ".join(f'"{w}"' for w in worte)

    def search(self, query: str, limit: int = 5) -> list[Hit]:
        if limit <= 0 or not self.available():
            return []

        if _is_explicit_fts_query(query):
            terms = _extract_explicit_terms(query)
            hits = self._sammeln(query, limit, query_terms=terms)
        else:
            terms = _extract_terms(query)
            if not terms:
                return []
            and_query = " ".join(f'"{w}"' for w in terms)
            hits = self._sammeln(and_query, limit, query_terms=terms)
            if not hits:
                # Erst die strenge UND-Suche ueber bereinigte Fachtokens, dann
                # die ODER-Variante: Ein Treffer, der alle Begriffe enthaelt,
                # ist der bessere -- die Lockerung greift nur ohne UND-Treffer.
                oder = self._oder_query(query)
                if oder:
                    hits = self._sammeln(oder, limit, query_terms=terms)

        hits.sort(key=lambda h: h.rank, reverse=True)
        return self._entdoppeln(hits)[:limit]

    def _sammeln(
        self,
        match_query: str,
        limit: int,
        query_terms: list[str] | None = None,
    ) -> list[Hit]:
        hits: list[Hit] = []
        for db_path, source_label in (
            (self.user_db, "gardener:user"),
            (self.system_db, "gardener:system"),
        ):
            hits.extend(
                self._search_db(
                    db_path,
                    source_label,
                    match_query,
                    limit,
                    query_terms=query_terms,
                )
            )
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
        self,
        db_path: Path,
        source_label: str,
        query: str,
        limit: int,
        query_terms: list[str] | None = None,
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

        # Mehr Zeilen holen als gebraucht, damit nach Termabdeckungs-Kalibrierung
        # und Entdoppelung weiterhin `limit` beste Treffer uebrig bleiben.
        parameter.append(max(limit * 8, 25))

        try:
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(
                    f"""
                    SELECT e.name AS name, e.content AS content,
                           COALESCE(e.tags, '') AS tags, e.type AS type,
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

        terms = query_terms if query_terms is not None else _extract_terms(query)
        total_terms = len(terms)
        results = []
        for row in rows:
            # bm25() ist ein negativer Real-Wert, kleiner = relevanter;
            # Kalibrierung ueber Termabdeckung und gedaempfte BM25-Saettigung
            # verhindert, dass bei grossen Korpora Zufallstreffer bei 0.9+
            # landen.
            strength = abs(row["score"])
            haystack = f"{row['name'] or ''} {row['content'] or ''} {row['tags'] or ''}"
            matched_terms = _matched_term_count(haystack, terms)
            rank = _calibrate_rank(strength, matched_terms, total_terms)
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
