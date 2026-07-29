from memoryhooker.backends.bach import BachBackend
from memoryhooker.backends.usmc import UsmcBackend


def test_usmc_backend_always_unavailable(tmp_path):
    backend = UsmcBackend(tmp_path / "usmc_memory.db")
    assert backend.available() is False
    assert backend.search("x") == []


def test_bach_backend_always_unavailable():
    backend = BachBackend()
    assert backend.available() is False
    assert backend.search("x") == []
