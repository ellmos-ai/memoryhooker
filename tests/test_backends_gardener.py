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
