"""Tests fuer die Backend-Kette (``[backend].order``) und ``ChainBackend``.

Hintergrund: Bis 0.1.0 kannte die Fabrik nur ein einzelnes Backend
(``[backend].kind``). Eine Live-Konfiguration mit ``order = ["gardener",
"files"]`` fiel dadurch still auf den Default ``files`` zurueck -- der Hook
lief monatelang gegen das falsche Gedaechtnis, ohne zu scheitern.
Diese Tests halten beide Schreibweisen fest.
"""

from pathlib import Path

import pytest

from memoryhooker.backends import ChainBackend, FilesBackend, GardenerBackend, build_backend
from memoryhooker.config import BackendConfig, Config, load_config
from memoryhooker.protocol import Hit


class _Stub:
    """Minimales Backend zum Pruefen von Reihenfolge und Fehlertoleranz."""

    def __init__(self, name, hits=(), available=True, raises=False):
        self.name = name
        self._hits = list(hits)
        self._available = available
        self._raises = raises
        self.searched = False

    def available(self) -> bool:
        if self._raises == "available":
            raise RuntimeError("kaputt")
        return self._available

    def search(self, query: str, limit: int = 5):
        self.searched = True
        if self._raises == "search":
            raise RuntimeError("kaputt")
        return self._hits[:limit]


def _hit(text, rank, source="stub"):
    return Hit(text=text, source=source, rank=rank)


# --- Config-Ebene ---------------------------------------------------------

def test_chain_falls_back_to_kind_when_order_absent():
    assert BackendConfig(kind="gardener").chain() == ["gardener"]


def test_order_wins_over_kind():
    cfg = BackendConfig(kind="files", order=["gardener", "usmc"])
    assert cfg.chain() == ["gardener", "usmc"]


def test_options_for_reads_subtable():
    cfg = BackendConfig(order=["gardener"], options={"gardener": {"db_path": "/tmp/g.db"}})
    assert cfg.options_for("gardener") == {"db_path": "/tmp/g.db"}


def test_options_for_falls_back_to_main_path():
    cfg = BackendConfig(kind="files", path="/tmp/mem")
    assert cfg.options_for("files")["path"] == "/tmp/mem"


def test_subtable_path_beats_main_path():
    cfg = BackendConfig(path="/tmp/main", options={"files": {"path": "/tmp/sub"}})
    assert cfg.options_for("files")["path"] == "/tmp/sub"


def test_files_backend_searches_multiple_roots_and_deduplicates(tmp_path: Path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (first / "a.md").write_text("Codex gemeinsames Gedächtnis", encoding="utf-8")
    (second / "b.md").write_text("Codex zweites Gedächtnis", encoding="utf-8")

    backend = FilesBackend(roots=[first, second, first])
    hits = backend.search("Codex", limit=10)

    assert backend.available() is True
    assert {hit.meta["root"] for hit in hits} == {str(first), str(second)}
    assert len(hits) == 2


def test_load_config_parses_order_and_options(tmp_path: Path):
    toml = tmp_path / "mh.toml"
    toml.write_text(
        '[backend]\n'
        'order = ["gardener", "files"]\n\n'
        '[backend.gardener]\n'
        'db_path = "~/.gardener/gardener.db"\n'
        'user_db_path = "~/.gardener/user.db"\n\n'
        '[backend.files]\n'
        'path = "~/memories"\n',
        encoding="utf-8",
    )
    config = load_config(toml)
    assert config.backend.chain() == ["gardener", "files"]
    assert config.backend.options_for("gardener")["user_db_path"] == "~/.gardener/user.db"
    assert config.backend.options_for("files")["path"] == "~/memories"


def test_load_config_parses_multiple_file_paths(tmp_path: Path):
    toml = tmp_path / "mh.toml"
    toml.write_text(
        '[backend]\norder = ["files"]\n\n'
        '[backend.files]\npaths = ["~/claude-memory", "~/.codex/memories"]\n',
        encoding="utf-8",
    )
    config = load_config(toml)
    backend = build_backend(config)
    assert [path.name for path in backend.roots] == ["claude-memory", "memories"]


def test_validate_rejects_unknown_backend_in_order():
    config = Config(backend=BackendConfig(order=["gardener", "nonsense"]))
    with pytest.raises(ValueError, match="order"):
        config.validate()


# --- Fabrik ---------------------------------------------------------------

def test_single_entry_order_builds_plain_backend():
    """Ein Glied bleibt ein nacktes Backend -- keine unnoetige Kette."""
    config = Config(backend=BackendConfig(order=["files"], options={"files": {"path": "/tmp"}}))
    assert isinstance(build_backend(config), FilesBackend)


def test_multi_entry_order_builds_chain():
    config = Config(backend=BackendConfig(order=["gardener", "files"]))
    backend = build_backend(config)
    assert isinstance(backend, ChainBackend)
    assert [type(b).__name__ for b in backend.backends] == [
        "GardenerBackend",
        "FilesBackend",
    ]


def test_gardener_options_reach_the_backend(tmp_path: Path):
    config = Config(
        backend=BackendConfig(
            order=["gardener", "files"],
            options={"gardener": {
                "db_path": str(tmp_path / "sys.db"),
                "user_db_path": str(tmp_path / "usr.db"),
            }},
        )
    )
    gardener = build_backend(config).backends[0]
    assert gardener.system_db == tmp_path / "sys.db"
    assert gardener.user_db == tmp_path / "usr.db"


def test_gardener_expands_tilde():
    backend = GardenerBackend(db_path="~/.gardener/gardener.db")
    assert "~" not in str(backend.system_db)


# --- ChainBackend-Verhalten ----------------------------------------------

def test_chain_merges_and_sorts_by_rank():
    chain = ChainBackend([
        _Stub("a", [_hit("low", 0.2)]),
        _Stub("b", [_hit("high", 0.9)]),
    ])
    ranks = [h.rank for h in chain.search("x", 5)]
    assert ranks == [0.9, 0.2]


def test_chain_is_stable_on_tie_first_link_wins():
    first = _hit("erste Quelle", 0.5, source="first")
    second = _hit("zweite Quelle", 0.5, source="second")
    chain = ChainBackend([_Stub("a", [first]), _Stub("b", [second])])
    assert [h.source for h in chain.search("x", 5)] == ["first", "second"]


def test_chain_respects_limit():
    chain = ChainBackend([
        _Stub("a", [_hit("1", 0.9), _hit("2", 0.8)]),
        _Stub("b", [_hit("3", 0.7)]),
    ])
    assert len(chain.search("x", 2)) == 2


def test_chain_skips_unavailable_link():
    absent = _Stub("a", [_hit("nicht sichtbar", 0.9)], available=False)
    present = _Stub("b", [_hit("sichtbar", 0.1)])
    hits = ChainBackend([absent, present]).search("x", 5)
    assert absent.searched is False
    assert [h.text for h in hits] == ["sichtbar"]


def test_chain_survives_a_broken_link():
    """Eine kaputte Quelle darf die uebrigen nie mitreissen."""
    broken = _Stub("a", raises="search")
    healthy = _Stub("b", [_hit("heil", 0.4)])
    assert [h.text for h in ChainBackend([broken, healthy]).search("x", 5)] == ["heil"]


def test_chain_survives_broken_available():
    broken = _Stub("a", [_hit("x", 0.9)], raises="available")
    healthy = _Stub("b", [_hit("heil", 0.4)])
    assert [h.text for h in ChainBackend([broken, healthy]).search("x", 5)] == ["heil"]


def test_chain_available_is_true_if_any_link_is():
    assert ChainBackend([_Stub("a", available=False), _Stub("b")]).available() is True


def test_chain_available_is_false_if_none_is():
    chain = ChainBackend([_Stub("a", available=False), _Stub("b", available=False)])
    assert chain.available() is False
