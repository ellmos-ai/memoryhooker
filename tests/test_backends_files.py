from pathlib import Path

from memoryhooker.backends.files import FilesBackend


def test_unavailable_when_root_missing(tmp_path: Path):
    backend = FilesBackend(tmp_path / "does-not-exist")
    assert backend.available() is False
    assert backend.search("anything") == []


def test_unavailable_when_root_is_none():
    backend = FilesBackend(None)
    assert backend.available() is False
    assert backend.search("anything") == []


def test_search_finds_matching_markdown_file(tmp_path: Path):
    (tmp_path / "a.md").write_text("Dies ist ein Eintrag über MemoryHooker und Gardener.", encoding="utf-8")
    (tmp_path / "b.md").write_text("Voellig unrelated Text.", encoding="utf-8")

    backend = FilesBackend(tmp_path)
    assert backend.available() is True

    hits = backend.search("MemoryHooker")
    assert len(hits) == 1
    assert hits[0].source == "a.md"
    assert 0 < hits[0].rank <= 1.0
    assert "MemoryHooker" in hits[0].text


def test_search_orders_by_score_desc(tmp_path: Path):
    (tmp_path / "weak.md").write_text("gardener einmal erwaehnt", encoding="utf-8")
    (tmp_path / "strong.md").write_text("gardener gardener gardener gardener gardener", encoding="utf-8")

    backend = FilesBackend(tmp_path)
    hits = backend.search("gardener")
    assert [h.source for h in hits] == ["strong.md", "weak.md"]
    assert hits[0].rank > hits[1].rank


def test_search_respects_limit(tmp_path: Path):
    for i in range(5):
        (tmp_path / f"f{i}.md").write_text("gardener " * (i + 1), encoding="utf-8")

    backend = FilesBackend(tmp_path)
    hits = backend.search("gardener", limit=2)
    assert len(hits) == 2


def test_search_empty_query_returns_nothing(tmp_path: Path):
    (tmp_path / "a.md").write_text("Inhalt", encoding="utf-8")
    backend = FilesBackend(tmp_path)
    assert backend.search("   ") == []


def test_search_recurses_into_subdirectories(tmp_path: Path):
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "nested.md").write_text("gardener im Unterordner", encoding="utf-8")

    backend = FilesBackend(tmp_path)
    hits = backend.search("gardener")
    assert hits and hits[0].source == str(Path("sub") / "nested.md")


def test_search_ignores_stopwords(tmp_path: Path):
    # "für" steckt als Substr in "Verfügung"/"dafür": ohne Stopwortfilter
    # wuerde die Fuellwort-Query hier faelschlich treffen.
    (tmp_path / "a.md").write_text(
        "Hinweis zur Verfügung: dafür ist der Maintainer zuständig.", encoding="utf-8"
    )

    backend = FilesBackend(tmp_path)
    assert backend.search("Rezept für Tomatensuppe") == []


def test_search_with_keywords_still_hits(tmp_path: Path):
    (tmp_path / "a.md").write_text(
        "Tomatensuppe: Zwiebeln anschwitzen, Tomaten dazu.", encoding="utf-8"
    )
    (tmp_path / "b.md").write_text("Anderes Thema.", encoding="utf-8")

    backend = FilesBackend(tmp_path)
    hits = backend.search("Rezept für Tomatensuppe")
    assert len(hits) == 1
    assert hits[0].source == "a.md"


def test_search_stopword_only_query_returns_nothing(tmp_path: Path):
    (tmp_path / "a.md").write_text("Für das und mit dem ist alles getan.", encoding="utf-8")

    backend = FilesBackend(tmp_path)
    assert backend.search("für das und mit") == []


def test_search_ignores_terms_shorter_than_three_chars(tmp_path: Path):
    (tmp_path / "a.md").write_text("py py py everywhere", encoding="utf-8")

    backend = FilesBackend(tmp_path)
    assert backend.search("py") == []


def test_search_strips_punctuation_from_terms(tmp_path: Path):
    (tmp_path / "a.md").write_text("Die Datei heisst memoryhooker.toml", encoding="utf-8")

    backend = FilesBackend(tmp_path)
    # "?" und "." duerfen den Term nicht veraendern: "memoryhooker.toml?"
    # als Ganzes kaeme im Text nie vor, die Tokens schon.
    hits = backend.search("Was ist memoryhooker.toml?")
    assert hits and hits[0].source == "a.md"


def test_search_single_file_as_root(tmp_path: Path):
    single_file = tmp_path / "single_memo.md"
    single_file.write_text("Dies ist eine einzelne Notiz ueber Architektur.", encoding="utf-8")

    backend = FilesBackend(single_file)
    assert backend.available() is True

    hits = backend.search("Architektur")
    assert len(hits) == 1
    assert hits[0].source == "single_memo.md"
    assert hits[0].meta["path"] == str(single_file)
    assert hits[0].meta["root"] == str(tmp_path)
    assert 0 < hits[0].rank <= 1.0


def test_search_mixed_roots_and_deduplication(tmp_path: Path):
    dir_path = tmp_path / "notes"
    dir_path.mkdir()
    shared_file = dir_path / "shared.md"
    shared_file.write_text("Wichtiger Eintrag fuer Projekt-Planung.", encoding="utf-8")

    other_file = tmp_path / "standalone.md"
    other_file.write_text("Planung fuer naechstes Quartal.", encoding="utf-8")

    missing_path = tmp_path / "does_not_exist.md"

    backend = FilesBackend(roots=[dir_path, shared_file, other_file, missing_path])
    assert backend.available() is True

    hits = backend.search("Planung")
    # shared_file ist im Verzeichnis und explizit als Einzeldatei angegeben -> genau 1 Treffer da dedupliziert
    assert len(hits) == 2
    sources = {h.source for h in hits}
    assert "shared.md" in sources
    assert "standalone.md" in sources


def test_normalized_ranking_favors_multi_term_coverage(tmp_path: Path):
    # doc_full enthält beide Suchbegriffe je 1x
    # doc_single enthält nur einen Begriff, aber 10x
    (tmp_path / "full.md").write_text("authentifizierung und autorisierung im system", encoding="utf-8")
    (tmp_path / "single.md").write_text("authentifizierung " * 10, encoding="utf-8")

    backend = FilesBackend(tmp_path)
    hits = backend.search("authentifizierung autorisierung")
    assert len(hits) == 2
    assert hits[0].source == "full.md"
    assert hits[1].source == "single.md"
    assert hits[0].rank > hits[1].rank
    assert 0 < hits[0].rank <= 1.0
    assert 0 < hits[1].rank <= 1.0

