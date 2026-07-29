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
