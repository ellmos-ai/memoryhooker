import json
from pathlib import Path

from memoryhooker.state import SessionState, _today, state_path_for_session


def test_load_missing_file_returns_defaults(tmp_path: Path):
    state = SessionState.load(tmp_path / "nope.json")
    assert state.injections_count == 0
    assert state.search_count == 0
    assert state.session_start_shown is False


def test_save_and_load_roundtrip(tmp_path: Path):
    path = tmp_path / "state.json"
    state = SessionState(injections_count=2, search_count=4, last_injection_ts=123.0, session_start_shown=True)
    state.save(path)

    loaded = SessionState.load(path)
    assert loaded == state


def test_record_search_increments():
    state = SessionState()
    state.record_search()
    state.record_search()
    assert state.search_count == 2


def test_load_ignores_corrupt_json(tmp_path: Path):
    path = tmp_path / "corrupt.json"
    path.write_text("{not valid json", encoding="utf-8")
    state = SessionState.load(path)
    assert state == SessionState()


def test_state_path_for_session_differs_by_session_id(tmp_path: Path):
    a = state_path_for_session("session-a", tmp_path)
    b = state_path_for_session("session-b", tmp_path)
    default = state_path_for_session(None, tmp_path)
    assert a != b != default


# ---------------------------------------------------------------------------
# TTL (Ticket T-20260816-132994550, Befund 1): ein Kalendertag-Wechsel oder
# eine Alt-Datei ohne state_date setzt den Cap-Guard zurueck.
# ---------------------------------------------------------------------------

def test_load_resets_state_from_a_previous_day(tmp_path: Path):
    path = tmp_path / "state.json"
    path.write_text(
        json.dumps(
            {
                "injections_count": 5,
                "search_count": 65,
                "last_injection_ts": 100.0,
                "session_start_shown": True,
                "state_date": "2000-01-01",  # garantiert nicht heute
            }
        ),
        encoding="utf-8",
    )

    state = SessionState.load(path)

    assert state == SessionState(state_date=_today())
    assert state.injections_count == 0


def test_load_resets_legacy_file_without_state_date_field(tmp_path: Path):
    """Der real gemessene Fall: eine Datei aus der Zeit vor diesem Feld haengt
    ohne diesen Fix fuer immer am Cap, weil ``state_date`` fehlt statt
    veraltet zu sein -- ein reiner "neuer Tag"-Vergleich haette das NICHT
    geheilt, weil der fehlende Wert sonst per Default-Factory sofort mit
    "heute" aufgefuellt worden waere."""
    path = tmp_path / "session-default.json"
    path.write_text(
        json.dumps(
            {
                "injections_count": 5,
                "search_count": 65,
                "last_injection_ts": 100.0,
                "session_start_shown": True,
            }
        ),
        encoding="utf-8",
    )

    state = SessionState.load(path)

    assert state.injections_count == 0
    assert state.state_date == _today()


def test_load_keeps_state_from_the_same_day(tmp_path: Path):
    path = tmp_path / "state.json"
    state = SessionState(injections_count=3, search_count=10, state_date=_today())
    state.save(path)

    loaded = SessionState.load(path)

    assert loaded == state
    assert loaded.injections_count == 3


def test_state_date_defaults_to_today():
    assert SessionState().state_date == _today()
