from pathlib import Path

from memoryhooker.state import SessionState, state_path_for_session


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
