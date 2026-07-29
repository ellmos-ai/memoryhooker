import pytest

from memoryhooker.backends import BachBackend, FilesBackend, GardenerBackend, UsmcBackend, build_backend
from memoryhooker.config import BackendConfig, Config


def test_build_backend_files():
    config = Config(backend=BackendConfig(kind="files", path="."))
    backend = build_backend(config)
    assert isinstance(backend, FilesBackend)


def test_build_backend_gardener(tmp_path):
    config = Config(backend=BackendConfig(kind="gardener", path=str(tmp_path)))
    backend = build_backend(config)
    assert isinstance(backend, GardenerBackend)


def test_build_backend_usmc():
    config = Config(backend=BackendConfig(kind="usmc"))
    assert isinstance(build_backend(config), UsmcBackend)


def test_build_backend_bach():
    config = Config(backend=BackendConfig(kind="bach"))
    assert isinstance(build_backend(config), BachBackend)


def test_build_backend_unknown_kind_raises():
    config = Config(backend=BackendConfig(kind="files"))
    config.backend.kind = "made-up"  # Config.validate() wuerde das fangen, hier direkt testen
    with pytest.raises(ValueError):
        build_backend(config)
