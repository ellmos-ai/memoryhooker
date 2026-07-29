from pathlib import Path

import pytest

from memoryhooker.config import Config, default_config, load_config


def test_default_config_matches_readme_defaults():
    config = default_config()
    assert config.mode.active == "remember"
    assert config.mode.search_after_n_searches == 3
    assert config.mode.max_hits == 3
    assert config.mode.min_rank == 0.5
    assert config.mode.max_injections_per_session == 5
    assert config.providers.order == [
        "claude",
        "codex",
        "kimi",
        "agy",
        "git",
        "manual",
    ]
    assert config.providers.claude_events == ["SessionStart", "UserPromptSubmit"]
    assert config.controlcenter.enabled == "auto"
    assert config.backend.kind == "files"


def test_load_config_missing_path_returns_defaults(tmp_path: Path):
    config = load_config(tmp_path / "does-not-exist.toml")
    assert config == default_config()


def test_load_config_none_returns_defaults():
    assert load_config(None) == default_config()


def test_load_config_reads_custom_toml(tmp_path: Path):
    toml_path = tmp_path / "memoryhooker.toml"
    toml_path.write_text(
        """
[mode]
active = "remember+search"
max_hits = 7
min_rank = 0.2
max_injections_per_session = 2

[clue]
triggers = ["MemoryHooker"]

[backend]
kind = "gardener"
path = "C:/tmp/gardener-data"
""",
        encoding="utf-8",
    )
    config = load_config(toml_path)
    assert config.mode.active == "remember+search"
    assert config.mode.max_hits == 7
    assert config.mode.min_rank == 0.2
    assert config.mode.max_injections_per_session == 2
    assert config.clue.triggers == ["MemoryHooker"]
    assert config.backend.kind == "gardener"
    assert config.backend.path == "C:/tmp/gardener-data"


def test_load_config_rejects_invalid_mode(tmp_path: Path):
    toml_path = tmp_path / "memoryhooker.toml"
    toml_path.write_text('[mode]\nactive = "invalid-mode"\n', encoding="utf-8")
    with pytest.raises(ValueError):
        load_config(toml_path)


def test_load_config_rejects_invalid_backend(tmp_path: Path):
    toml_path = tmp_path / "memoryhooker.toml"
    toml_path.write_text('[backend]\nkind = "made-up"\n', encoding="utf-8")
    with pytest.raises(ValueError):
        load_config(toml_path)


def test_config_validate_rejects_out_of_range_min_rank():
    config = Config()
    config.mode.min_rank = 1.5
    with pytest.raises(ValueError):
        config.validate()
