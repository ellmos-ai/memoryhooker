from memoryhooker.backends import ChainBackend
from memoryhooker.config import ClueConfig, Config, ModeConfig
from memoryhooker.modes import diagnose_prompt, evaluate_prompt, session_start_message
from memoryhooker.protocol import Hit
from memoryhooker.state import SessionState


class _StubBackend:
    def __init__(self, available: bool = True, hits: list[Hit] | None = None):
        self._available = available
        self._hits = hits or []

    def available(self) -> bool:
        return self._available

    def search(self, query: str, limit: int = 5) -> list[Hit]:
        return self._hits[:limit]


# ---------------------------------------------------------------------------
# session_start_message
# ---------------------------------------------------------------------------

def test_session_start_fires_once_when_backend_available():
    state = SessionState()
    backend = _StubBackend(available=True)

    first = session_start_message(backend, state)
    second = session_start_message(backend, state)

    assert first is not None
    assert second is None
    assert state.session_start_shown is True


def test_session_start_silent_when_backend_unavailable():
    state = SessionState()
    backend = _StubBackend(available=False)
    assert session_start_message(backend, state) is None


# ---------------------------------------------------------------------------
# remember mode
# ---------------------------------------------------------------------------

def test_remember_mode_silent_before_threshold():
    config = Config(mode=ModeConfig(active="remember", search_after_n_searches=3))
    backend = _StubBackend(available=True)
    state = SessionState(search_count=2)

    assert evaluate_prompt("irgendein prompt", config, backend, state) is None


def test_remember_mode_fires_after_threshold():
    config = Config(mode=ModeConfig(active="remember", search_after_n_searches=3))
    backend = _StubBackend(available=True)
    state = SessionState(search_count=3)

    message = evaluate_prompt("irgendein prompt", config, backend, state)
    assert message is not None
    assert state.injections_count == 1


def test_remember_mode_silent_without_backend():
    config = Config(mode=ModeConfig(active="remember", search_after_n_searches=0))
    backend = _StubBackend(available=False)
    state = SessionState()
    assert evaluate_prompt("x", config, backend, state) is None


# ---------------------------------------------------------------------------
# clue mode
# ---------------------------------------------------------------------------

def test_clue_mode_matches_trigger_case_insensitive():
    config = Config(
        mode=ModeConfig(active="clue", min_rank=0.5),
        clue=ClueConfig(triggers=["MemoryHooker"]),
    )
    backend = _StubBackend(hits=[Hit(text="Notiz zu MemoryHooker", source="a.md", rank=0.9)])
    state = SessionState()

    message = evaluate_prompt("Was ist eigentlich memoryhooker?", config, backend, state)
    assert message is not None
    assert "MemoryHooker" in message
    assert "a.md" in message


def test_clue_mode_no_trigger_match_is_silent():
    config = Config(mode=ModeConfig(active="clue"), clue=ClueConfig(triggers=["Xyzzy"]))
    backend = _StubBackend(hits=[Hit(text="egal", source="a.md", rank=0.9)])
    state = SessionState()

    assert evaluate_prompt("voellig anderer text", config, backend, state) is None


def test_clue_mode_respects_min_rank():
    config = Config(
        mode=ModeConfig(active="clue", min_rank=0.8),
        clue=ClueConfig(triggers=["Trigger"]),
    )
    backend = _StubBackend(hits=[Hit(text="schwacher treffer", source="a.md", rank=0.3)])
    state = SessionState()

    assert evaluate_prompt("Trigger im text", config, backend, state) is None


# ---------------------------------------------------------------------------
# remember+search mode
# ---------------------------------------------------------------------------

def test_search_mode_formats_hits_above_min_rank():
    config = Config(mode=ModeConfig(active="remember+search", max_hits=2, min_rank=0.4))
    backend = _StubBackend(
        hits=[
            Hit(text="starker treffer", source="a.md", rank=0.9),
            Hit(text="schwacher treffer", source="b.md", rank=0.1),
        ]
    )
    state = SessionState()

    message = evaluate_prompt("suche etwas", config, backend, state)
    assert message is not None
    assert "starker treffer" in message
    assert "schwacher treffer" not in message


def test_search_mode_silent_without_hits():
    config = Config(mode=ModeConfig(active="remember+search"))
    backend = _StubBackend(hits=[])
    state = SessionState()
    assert evaluate_prompt("suche etwas", config, backend, state) is None


# ---------------------------------------------------------------------------
# 4-Augen-Hook-Guard: harte Obergrenze + Cooldown
# ---------------------------------------------------------------------------

def test_hard_cap_max_injections_per_session():
    config = Config(mode=ModeConfig(active="remember", search_after_n_searches=0, max_injections_per_session=2, cooldown_seconds=0))
    backend = _StubBackend(available=True)
    state = SessionState()

    results = [evaluate_prompt(f"prompt {i}", config, backend, state, now=float(i)) for i in range(5)]
    fired = [r for r in results if r is not None]
    assert len(fired) == 2
    assert state.injections_count == 2


def test_cooldown_blocks_rapid_repeated_injections():
    config = Config(mode=ModeConfig(active="remember", search_after_n_searches=0, max_injections_per_session=10, cooldown_seconds=60))
    backend = _StubBackend(available=True)
    state = SessionState()

    first = evaluate_prompt("p1", config, backend, state, now=0.0)
    second = evaluate_prompt("p2", config, backend, state, now=10.0)  # innerhalb Cooldown
    third = evaluate_prompt("p3", config, backend, state, now=61.0)  # nach Cooldown

    assert first is not None
    assert second is None
    assert third is not None
    assert state.injections_count == 2


def test_unknown_mode_raises_value_error():
    import pytest

    config = Config(mode=ModeConfig(active="remember"))
    config.mode.active = "made-up-mode"  # Config.validate() wuerde das fangen; hier direkt evaluate() testen
    backend = _StubBackend(available=True)
    state = SessionState()
    with pytest.raises(ValueError):
        evaluate_prompt("x", config, backend, state)


# ---------------------------------------------------------------------------
# diagnose_prompt (Ticket T-20260816-132994550, Befund 2)
# ---------------------------------------------------------------------------


def test_diagnose_never_mutates_the_passed_in_state():
    config = Config(mode=ModeConfig(active="remember+search", cooldown_seconds=0))
    backend = _StubBackend(hits=[Hit(text="treffer", source="a.md", rank=0.9)])
    state = SessionState()

    report = diagnose_prompt("suche", config, backend, state, now=0.0)

    assert report.would_inject is not None
    assert state.injections_count == 0
    assert state.last_injection_ts is None


def test_diagnose_session_cap_status_reflects_config_and_state():
    config = Config(mode=ModeConfig(max_injections_per_session=2))
    state = SessionState(injections_count=2)
    backend = _StubBackend(available=False)

    report = diagnose_prompt("x", config, backend, state, now=0.0)

    assert report.session_cap.ok is False
    assert report.session_cap.detail == "2/2"
    assert report.would_inject is None


def test_diagnose_cooldown_status_reflects_remaining_time():
    config = Config(mode=ModeConfig(cooldown_seconds=60))
    state = SessionState(last_injection_ts=0.0)
    backend = _StubBackend(available=False)

    blocked = diagnose_prompt("x", config, backend, state, now=10.0)
    assert blocked.cooldown.ok is False
    assert "50" in blocked.cooldown.detail

    ready = diagnose_prompt("x", config, backend, state, now=61.0)
    assert ready.cooldown.ok is True
    assert ready.cooldown.detail == "bereit"


def test_diagnose_reports_each_link_of_a_chain_backend():
    unavailable = _StubBackend(available=False)
    available = _StubBackend(hits=[Hit(text="treffer", source="a.md", rank=0.7)])
    chain = ChainBackend([unavailable, available])
    config = Config(mode=ModeConfig(active="remember+search"))
    state = SessionState()

    report = diagnose_prompt("suche", config, chain, state, now=0.0)

    assert len(report.backends) == 2
    assert report.backends[0].available is False
    assert report.backends[0].hit_count == 0
    assert report.backends[0].top_rank is None
    assert report.backends[1].available is True
    assert report.backends[1].hit_count == 1
    assert report.backends[1].top_rank == 0.7


def test_diagnose_survives_a_broken_backend():
    class _Broken:
        def available(self):
            raise RuntimeError("kaputt")

        def search(self, query, limit=5):
            raise RuntimeError("kaputt")

    config = Config(mode=ModeConfig(active="remember+search"))
    state = SessionState()

    report = diagnose_prompt("x", config, _Broken(), state, now=0.0)

    assert report.backends[0].available is False
    assert report.backends[0].hit_count == 0
    assert report.would_inject is None
