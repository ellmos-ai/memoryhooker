"""Tests gegen eine synthetische DB mit Gardeners echtem Schema.

Schema 1:1 aus gardener.py uebernommen (SCHEMA_SYSTEM), damit der Adapter
gegen dieselbe Tabellenstruktur getestet wird, die Gardener real anlegt --
nicht gegen eine erfundene Vereinfachung.
"""

import sqlite3
from pathlib import Path

from memoryhooker.backends.gardener import GardenerBackend

_SCHEMA = """
CREATE TABLE IF NOT EXISTS everything (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL DEFAULT 'knowledge',
    name TEXT NOT NULL UNIQUE,
    content TEXT DEFAULT '',
    tags TEXT DEFAULT '',
    meta TEXT DEFAULT '{}',
    pinned INTEGER DEFAULT 0,
    created TEXT NOT NULL,
    updated TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS everything_fts
    USING fts5(name, content, tags, content=everything, content_rowid=id);

CREATE TRIGGER IF NOT EXISTS everything_ai AFTER INSERT ON everything BEGIN
    INSERT INTO everything_fts(rowid, name, content, tags)
    VALUES (new.id, new.name, new.content, new.tags);
END;
"""


def _make_db(path: Path, entries: list[tuple[str, str, str]]) -> None:
    conn = sqlite3.connect(str(path))
    conn.executescript(_SCHEMA)
    for name, content, type_ in entries:
        conn.execute(
            "INSERT INTO everything (type, name, content, created, updated) VALUES (?, ?, ?, '2026-07-23', '2026-07-23')",
            (type_, name, content),
        )
    conn.commit()
    conn.close()


def test_unavailable_when_no_db_files(tmp_path: Path):
    backend = GardenerBackend(tmp_path)
    assert backend.available() is False
    assert backend.search("anything") == []


def test_available_when_user_db_exists(tmp_path: Path):
    _make_db(tmp_path / "user.db", [("lesson/x", "MemoryHooker ist ein Hook-Modul", "lesson")])
    backend = GardenerBackend(tmp_path)
    assert backend.available() is True


def test_search_finds_fts_match(tmp_path: Path):
    _make_db(
        tmp_path / "user.db",
        [
            ("lesson/memoryhooker", "MemoryHooker sitzt im Harness, nicht im Speicher.", "lesson"),
            ("lesson/unrelated", "Voellig unrelated Inhalt.", "lesson"),
        ],
    )
    backend = GardenerBackend(tmp_path)
    hits = backend.search("Harness")
    assert len(hits) == 1
    assert "Harness" in hits[0].text
    assert hits[0].source == "gardener:user:lesson/memoryhooker"
    assert 0 < hits[0].rank <= 1.0


def test_search_merges_user_and_system_db(tmp_path: Path):
    _make_db(tmp_path / "user.db", [("u/1", "gardener treffer im user-db", "lesson")])
    _make_db(tmp_path / "gardener.db", [("s/1", "gardener treffer im system-db", "knowledge")])

    backend = GardenerBackend(tmp_path)
    hits = backend.search("gardener")
    sources = {h.source for h in hits}
    assert "gardener:user:u/1" in sources
    assert "gardener:system:s/1" in sources


def test_search_on_db_without_table_returns_empty(tmp_path: Path):
    # Datei existiert, aber ohne Schema (z. B. leere/kaputte DB)
    (tmp_path / "user.db").write_bytes(b"")
    sqlite3.connect(str(tmp_path / "user.db")).close()

    backend = GardenerBackend(tmp_path)
    assert backend.available() is True
    assert backend.search("irrelevant") == []


def test_search_respects_limit(tmp_path: Path):
    entries = [(f"e/{i}", f"gardener treffer nummer {i}", "lesson") for i in range(5)]
    _make_db(tmp_path / "user.db", entries)
    backend = GardenerBackend(tmp_path)
    hits = backend.search("gardener", limit=2)
    assert len(hits) <= 2


# --- Rang-Normalisierung (Regressionsschutz) ------------------------------
#
# Bis 2026-07-25 stand hier ``1 / (1 + |bm25|)``. Da bm25() negativ ist und
# kleinere Werte bessere Treffer bedeuten, war das invertiert: der beste
# Treffer bekam den niedrigsten Rang. Folge im Betrieb: die Sortierung stellte
# die schlechtesten Treffer nach oben, und ``min_rank`` filterte bevorzugt die
# besten weg -- der Hook lieferte deshalb nie etwas. Kein Test hatte die
# Monotonie geprueft; diese holen das nach.
#
# Wichtig fuer die Fixture: bm25 braucht Dokumente OHNE den Suchbegriff,
# sonst ist die IDF null und alle Scores sind 0.0 (dann misst der Test nichts).
# Und ``data_dir`` setzen, nicht nur ``db_path`` -- sonst zeigt die User-DB
# weiterhin auf das echte ``~/.gardener``.

def _make_ranking_db(tmp_path: Path) -> Path:
    """System-DB mit einem starken, einem schwachen und Fuelltreffern."""
    _make_db(tmp_path / "gardener.db", [
        ("stark", "lock lock lock lock lock", "knowledge"),
        ("schwach", "lock " + "fuellwort " * 200, "knowledge"),
        *[(f"fuell{i}", "voellig anderes thema ohne den begriff", "knowledge")
          for i in range(8)],
    ])
    _make_db(tmp_path / "user.db", [])
    return tmp_path


def test_rank_is_higher_for_the_better_match(tmp_path: Path):
    """Ein Dokument, in dem der Suchbegriff dominiert, muss hoeher ranken."""
    backend = GardenerBackend(_make_ranking_db(tmp_path))
    ranks = {h.source.split(":")[-1]: h.rank for h in backend.search("lock", 5)}
    assert ranks["stark"] > ranks["schwach"]


def test_hits_are_sorted_best_first(tmp_path: Path):
    backend = GardenerBackend(_make_ranking_db(tmp_path))
    hits = backend.search("lock", 5)
    assert [h.rank for h in hits] == sorted((h.rank for h in hits), reverse=True)
    assert hits[0].source.endswith("stark")


def test_rank_stays_inside_the_documented_interval(tmp_path: Path):
    """protocol.Hit sagt zu: rank liegt in (0, 1]."""
    backend = GardenerBackend(_make_ranking_db(tmp_path))
    for hit in backend.search("lock", 5):
        assert 0.0 < hit.rank <= 1.0


def test_db_path_alone_does_not_leak_the_default_user_db(tmp_path: Path):
    """Wer nur die System-DB setzt, darf nicht ungewollt ~/.gardener/user.db lesen."""
    backend = GardenerBackend(db_path=tmp_path / "sys.db")
    assert backend.user_db.parent == tmp_path


# ---------------------------------------------------------------------------
# Relevanzfilter (2026-08-01): Gedaechtnis statt Rohmaterial
# ---------------------------------------------------------------------------


def _make_db_mit_tags(path: Path, entries: list[tuple[str, str, str, str]]) -> None:
    """Wie ``_make_db``, aber mit ``tags`` -- der Transkriptfilter braucht sie."""
    conn = sqlite3.connect(str(path))
    conn.executescript(_SCHEMA)
    for name, content, type_, tags in entries:
        conn.execute(
            "INSERT INTO everything (type, name, content, tags, created, updated)"
            " VALUES (?, ?, ?, ?, '2026-08-01', '2026-08-01')",
            (type_, name, content, tags),
        )
    conn.commit()
    conn.close()


def test_gespraechstranskripte_sind_ausgeschlossen(tmp_path: Path):
    """Regression: Transkriptfetzen verdraengten das kuratierte Gedaechtnis.

    Gemessen auf ASUS-GEI am 2026-08-01: 11.835 der 14.251 observed-Eintraege
    (83%) waren Transkripte, und drei typische Prompts lieferten neun von neun
    Treffern aus Rohmaterial -- darunter abgeschnittene Gespraechsfetzen aus
    Altsitzungen. Genau das meldete der Nutzer als "waehlt oft Irrelevantes".
    """
    _make_db_mit_tags(tmp_path / "user.db", [
        ("observed/claude-transcripts/x1", "git push Fetzen aus einer Altsitzung",
         "observed", "agent_transcript,claude-transcripts,assistant"),
        ("memory/git-regeln", "git push nur nach Ruecksprache", "memory", "regeln"),
    ])
    hits = GardenerBackend(tmp_path).search("git", 5)

    quellen = [h.source for h in hits]
    assert any("git-regeln" in q for q in quellen), quellen
    assert not any("transcripts" in q for q in quellen), quellen


def test_wertvolles_material_bleibt_drin(tmp_path: Path):
    """Der Filter zielt auf Transkripte, NICHT auf `observed` als Ganzes.

    Skills, Regeldateien und die Lesson-Tabellen anderer Werkzeuge liegen
    ebenfalls als `observed` -- als Hinweis sind sie wertvoll und muessen
    weiterhin gefunden werden.
    """
    _make_db_mit_tags(tmp_path / "user.db", [
        ("observed/skills-library/encoding-fix/SKILL.md", "encoding reparieren",
         "observed", "markdown_dir,skills-library"),
        ("observed/bach-lessons/7", "encoding kippt auf cp1252",
         "observed", "sqlite_table,bach-lessons"),
    ])
    hits = GardenerBackend(tmp_path).search("encoding", 5)
    assert len(hits) == 2, [h.source for h in hits]


def test_filter_sind_ueberschreibbar(tmp_path: Path):
    """Wer die Transkripte doch durchsuchen will, schaltet den Filter ab."""
    _make_db_mit_tags(tmp_path / "user.db", [
        ("observed/claude-transcripts/x1", "git push Fetzen",
         "observed", "agent_transcript,claude-transcripts"),
    ])
    assert GardenerBackend(tmp_path).search("git", 5) == []
    offen = GardenerBackend(tmp_path, exclude_tags=[])
    assert len(offen.search("git", 5)) == 1


def test_gleicher_text_nur_einmal(tmp_path: Path):
    """Dieselbe Datei ueber zwei observe-Quellen indexiert."""
    _make_db_mit_tags(tmp_path / "user.db", [
        ("observed/quelle-a/notiz.md", "Lock vor Arbeitsbeginn setzen", "observed", "markdown_dir,a"),
        ("observed/quelle-b/notiz.md", "Lock vor Arbeitsbeginn setzen", "observed", "markdown_dir,b"),
    ])
    hits = GardenerBackend(tmp_path).search("Lock", 5)
    assert len(hits) == 1, [h.source for h in hits]


def test_sprachfassungen_belegen_nur_einen_platz(tmp_path: Path):
    """SKILL.md und SKILL.fr.md sind derselbe Hinweis in zwei Sprachen.

    Ihre Texte unterscheiden sich, der Textvergleich greift also nicht --
    als Hinweis sind sie dennoch austauschbar. Gemessen 2026-08-01: drei von
    neun Treffern einer Stichprobe waren Uebersetzungen bereits gelisteter
    Eintraege.
    """
    _make_db_mit_tags(tmp_path / "user.db", [
        ("observed/skills/encoding-fix/SKILL.md", "encoding repair for mojibake",
         "observed", "markdown_dir,skills"),
        ("observed/skills/encoding-fix/SKILL.fr.md", "encoding reparation des mojibakes",
         "observed", "markdown_dir,skills"),
        ("observed/skills/encoding-fix/SKILL.zh.md", "encoding mojibake xiufu",
         "observed", "markdown_dir,skills"),
    ])
    hits = GardenerBackend(tmp_path).search("encoding", 5)
    assert len(hits) == 1, [h.source for h in hits]


def test_unterstrich_sprachkennung_zaehlt_ebenfalls_einmal(tmp_path: Path):
    """Zweite verbreitete Schreibweise: ``README.md`` neben ``README_de.md``.

    Gegenprobe zugleich: ``SKILL.md`` im selben Ordner ist eine ANDERE Datei
    und muss als eigener Treffer erhalten bleiben.
    """
    _make_db_mit_tags(tmp_path / "user.db", [
        ("observed/modul/x/README.md", "lock verfahren englisch", "observed", "markdown_dir"),
        ("observed/modul/x/README_de.md", "lock verfahren deutsch", "observed", "markdown_dir"),
        ("observed/modul/x/SKILL.md", "lock als skill beschrieben", "observed", "markdown_dir"),
    ])
    hits = GardenerBackend(tmp_path).search("lock", 5)
    namen = sorted(h.source.rsplit("/", 1)[-1] for h in hits)
    assert namen == ["README.md", "SKILL.md"], namen


def test_gleicher_name_unter_zwei_kategorien_zaehlt_einmal(tmp_path: Path):
    """Derselbe Skill unter zwei Kategorien abgelegt (real vorgefunden:
    `surface-after-care` liegt unter `dev/` UND unter `infrastructure/`)."""
    _make_db_mit_tags(tmp_path / "user.db", [
        ("observed/skills-library/dev/after-care/SKILL.md", "pflege lauf alpha",
         "observed", "markdown_dir,skills-library"),
        ("observed/skills-library/infrastructure/after-care/SKILL.md", "pflege lauf beta",
         "observed", "markdown_dir,skills-library"),
    ])
    hits = GardenerBackend(tmp_path).search("pflege", 5)
    assert len(hits) == 1, [h.source for h in hits]


def test_verschiedene_dateien_werden_nicht_verwechselt(tmp_path: Path):
    """Gegenprobe: Der Entdoppler darf nicht zu gierig sein."""
    _make_db_mit_tags(tmp_path / "user.db", [
        ("observed/skills/lock-a/SKILL.md", "Lock setzen vor Arbeitsbeginn", "observed", "markdown_dir"),
        ("observed/skills/lock-b/SKILL.md", "Lock nach Abschluss freigeben", "observed", "markdown_dir"),
    ])
    hits = GardenerBackend(tmp_path).search("Lock", 5)
    assert len(hits) == 2, [h.source for h in hits]


def test_ganzer_satz_findet_trotz_fts_und_verknuepfung(tmp_path: Path):
    """Regression: Ein echter Nutzer-Prompt ist ein Satz, keine Stichwortliste.

    FTS5 verknuepft die Woerter einer MATCH-Query mit UND -- ein ganzer Satz
    verlangt damit ein Dokument, das ALLE Woerter enthaelt, Fuellwoerter und
    Fragezeichen eingeschlossen. Gemessen am 2026-08-01: der Prompt "wie setze
    ich einen lock richtig?" lieferte aus diesem Backend null Treffer, sodass
    allein das schwaechere files-Backend die Injektion bestritt -- mit einem
    mathematischen Beweistext als drittem Treffer.
    """
    _make_db_mit_tags(tmp_path / "user.db", [
        ("memory/lock-regel", "Lock vor Arbeitsbeginn setzen", "memory", "regeln"),
    ])
    backend = GardenerBackend(tmp_path)

    assert backend.search("Lock setzen", 3), "Stichwort-Query fand schon vorher"
    treffer = backend.search("wie setze ich einen Lock richtig?", 3)
    assert treffer, "ganzer Satz muss ebenfalls finden"
    assert "lock-regel" in treffer[0].source


def test_explizite_operatoren_bleiben_unangetastet(tmp_path: Path):
    """Wer FTS-Operatoren oder Phrasen schreibt, meint sie -- keine Lockerung."""
    _make_db_mit_tags(tmp_path / "user.db", [
        ("memory/a", "Lock setzen vor Arbeitsbeginn", "memory", "regeln"),
        ("memory/b", "Backup nachts einspielen", "memory", "regeln"),
    ])
    backend = GardenerBackend(tmp_path)

    # Phrase, die so nicht vorkommt: darf NICHT auf ODER gelockert werden.
    assert backend.search('"Lock Backup"', 3) == []
    # Explizites UND ebenfalls nicht.
    assert backend.search("Lock AND Backup", 3) == []
