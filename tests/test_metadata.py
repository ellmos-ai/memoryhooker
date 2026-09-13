import json
from pathlib import Path

import pytest

# ``tomllib`` ist erst ab Python 3.11 Stdlib, das Projekt bleibt aber bei
# ``requires-python = ">=3.10"``. Ohne diesen Skip bricht schon das Einsammeln
# der Testdatei ab und reisst die ganze 3.10-Zeile der CI-Matrix mit.
# Der paketeigene Fallback aus ``memoryhooker/_toml.py`` hilft hier NICHT: er
# deckt bewusst nur das Teilmengen-Schema der eigenen Config ab und scheitert
# an der Inline-Tabelle in ``authors`` von pyproject.toml. Eine Testabhaengigkeit
# auf ``tomli`` waere die Alternative -- sie brachte aber nichts, weil die
# Versionsparitaet auf 3.11/3.12/3.13 ohnehin geprueft wird.
tomllib = pytest.importorskip("tomllib", reason="stdlib erst ab Python 3.11")

import memoryhooker


def test_version_parity():
    root = Path(__file__).resolve().parent.parent
    pyproject_path = root / "pyproject.toml"
    module_v2_path = root / "ellmos-module.v2.json"

    with pyproject_path.open("rb") as f:
        pyproject_data = tomllib.load(f)
    pyproject_version = pyproject_data["project"]["version"]

    with module_v2_path.open("r", encoding="utf-8") as f:
        module_v2_data = json.load(f)
    module_v2_version = module_v2_data["version"]

    assert memoryhooker.__version__ == pyproject_version
    assert memoryhooker.__version__ == module_v2_version


def test_module_v2_contract():
    root = Path(__file__).resolve().parent.parent
    module_v2_path = root / "ellmos-module.v2.json"

    with module_v2_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["schema"] == "ellmos.module.v2"
    assert data["id"] == "memoryhooker"
    assert "provides" in data
    assert "surfaces" in data
    assert "boundaries" in data


def test_package_exports():
    expected_exports = ["Hit", "MemoryBackend", "Config", "load_config", "__version__"]
    for export_name in expected_exports:
        assert hasattr(memoryhooker, export_name)
        assert export_name in memoryhooker.__all__
