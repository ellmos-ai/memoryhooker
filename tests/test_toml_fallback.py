from memoryhooker._toml import loads, loads_fallback


SAMPLE = """
# Kommentar
[mode]
active = "clue"
max_hits = 3
min_rank = 0.5
max_injections_per_session = 5

[clue]
triggers = ["foo", "bar baz"]

[providers]
order = ["claude", "manual"]

[providers.claude]
events = ["SessionStart", "UserPromptSubmit"]

[controlcenter]
enabled = "auto"
suggest_skills = true
suggest_tools = false
"""


def test_loads_uses_stdlib_or_fallback_consistently():
    data = loads(SAMPLE)
    assert data["mode"]["active"] == "clue"
    assert data["mode"]["max_hits"] == 3
    assert data["mode"]["min_rank"] == 0.5
    assert data["clue"]["triggers"] == ["foo", "bar baz"]
    assert data["providers"]["order"] == ["claude", "manual"]
    assert data["providers"]["claude"]["events"] == ["SessionStart", "UserPromptSubmit"]
    assert data["controlcenter"]["suggest_skills"] is True
    assert data["controlcenter"]["suggest_tools"] is False


def test_fallback_parser_directly_regardless_of_python_version():
    # Der Fallback-Pfad soll unabhaengig vom aktiven Interpreter getestet
    # sein (siehe Docstring in _toml.py).
    data = loads_fallback(SAMPLE)
    assert data["mode"]["active"] == "clue"
    assert data["clue"]["triggers"] == ["foo", "bar baz"]
    assert data["providers"]["claude"]["events"] == ["SessionStart", "UserPromptSubmit"]


def test_fallback_parser_empty_array():
    data = loads_fallback("[mode]\nchecks = []\n")
    assert data["mode"]["checks"] == []


def test_fallback_parser_inline_comment():
    data = loads_fallback('[mode]\nactive = "remember"  # Default\n')
    assert data["mode"]["active"] == "remember"


def test_fallback_parser_rejects_garbage_line():
    import pytest

    with pytest.raises(ValueError):
        loads_fallback("not a valid toml line at all ===")
