import io
import json
import sqlite3

from memoryhooker.backends import ChainBackend, UsmcBackend
from memoryhooker.cli import main
from memoryhooker.config import Config, TriggersConfig, load_config
from memoryhooker.state import SessionState
from memoryhooker.triggers import evaluate_triggers, read_context_triggers

_DDL = """
CREATE TABLE context_triggers (
    id INTEGER PRIMARY KEY AUTOINCREMENT, trigger_phrase TEXT NOT NULL,
    hint_text TEXT NOT NULL, source TEXT DEFAULT 'manual', is_active INTEGER DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'unknown', agent_id TEXT NOT NULL DEFAULT 'default',
    expires_at TEXT, UNIQUE(agent_id, trigger_phrase));
"""


def _db(tmp_path, rows):
    path = tmp_path / "mem.db"
    conn = sqlite3.connect(path)
    conn.executescript(_DDL)
    defaults = (1, "unknown", "default", None)  # is_active, status, agent_id, expires_at
    for row in rows:
        conn.execute(
            "INSERT INTO context_triggers (trigger_phrase, hint_text, source, is_active, status,"
            " agent_id, expires_at) VALUES (?,?,?,?,?,?,?)",
            (*row, *defaults[len(row) - 3:]),
        )
    conn.commit()
    return path, conn


class _Backend:
    def __init__(self, conn):
        self.conn = conn

    def available(self):
        return True

    def search(self, query, limit=5):
        return []

    def triggers(self, sources, agent_id="default"):
        return read_context_triggers(self.conn, sources, agent_id)


def _config(**cooldowns):
    return Config(triggers=TriggersConfig(sources=["strategy", "context"], cooldowns=cooldowns))


def test_read_rule_filters_inactive_blocked_expired_and_foreign_agents(tmp_path):
    _, conn = _db(tmp_path, [
        ("aktiv|active", "A", "strategy"),
        ("inaktiv", "B", "strategy", 0),
        ("gesperrt", "C", "strategy", 1, "blocked"),
        ("fremd", "D", "strategy", 1, "unknown", "other-agent"),
        ("abgelaufen", "E", "strategy", 1, "unknown", "default", "2000-01-01 00:00:00"),
        ("andere-quelle", "F", "manual"),
    ])
    rules = read_context_triggers(conn, ["strategy"])
    assert [(r.phrases, r.hint) for r in rules] == [(("aktiv", "active"), "A")]
    assert [r.hint for r in read_context_triggers(conn, ["strategy"], "other-agent")] == ["A", "D"]


def test_first_matching_rule_per_source_in_id_order(tmp_path):
    _, conn = _db(tmp_path, [
        ("fehler|bug", "[STRATEGIE] erst verstehen", "strategy"),
        ("komplex", "[STRATEGIE] zerlegen", "strategy"),
        ("bug", "[KONTEXT] bugfix-workflow", "context"),
    ])
    hints = evaluate_triggers("Komplexer BUG hier", _config(), _Backend(conn), SessionState(), now=0)
    assert hints == ["[STRATEGIE] erst verstehen", "[KONTEXT] bugfix-workflow"]


def test_cooldown_is_per_source(tmp_path):
    _, conn = _db(tmp_path, [("fehler", "S", "strategy"), ("fehler|error", "K", "context")])
    config, state, backend = _config(strategy=120, context=0), SessionState(), _Backend(conn)
    assert evaluate_triggers("fehler", config, backend, state, now=1000) == ["S", "K"]
    assert evaluate_triggers("fehler", config, backend, state, now=1100) == ["K"]
    assert evaluate_triggers("fehler", config, backend, state, now=1120) == ["S", "K"]


def test_off_without_sources_and_backend_without_triggers(tmp_path):
    _, conn = _db(tmp_path, [("fehler", "S", "strategy")])
    assert evaluate_triggers("fehler", Config(), _Backend(conn), SessionState()) == []

    class _Plain:
        def available(self):
            return True

        def search(self, query, limit=5):
            return []

    assert evaluate_triggers("fehler", _config(), _Plain(), SessionState()) == []


def test_usmc_and_chain_backends_read_triggers(tmp_path):
    path, conn = _db(tmp_path, [("fehler", "S", "strategy")])
    conn.close()
    usmc = UsmcBackend(path)
    assert [r.hint for r in usmc.triggers(["strategy"])] == ["S"]
    assert [r.hint for r in ChainBackend([usmc]).triggers(["strategy"])] == ["S"]
    assert UsmcBackend(tmp_path / "missing.db").triggers(["strategy"]) == []


def test_config_and_state_roundtrip(tmp_path):
    config_path = tmp_path / "memoryhooker.toml"
    config_path.write_text(
        '[triggers]\nsources = ["strategy"]\nagent_id = "bach"\n[triggers.cooldowns]\nstrategy = 120\n',
        encoding="utf-8",
    )
    config = load_config(config_path)
    assert config.triggers == TriggersConfig(["strategy"], {"strategy": 120}, "bach")

    state_path = tmp_path / "s.json"
    SessionState().save(state_path)
    assert "trigger_last_ts" not in json.loads(state_path.read_text(encoding="utf-8"))
    state = SessionState(trigger_last_ts={"strategy": 5.0})
    state.save(state_path)
    assert SessionState.load(state_path).trigger_last_ts == {"strategy": 5.0}


def test_hook_run_emits_trigger_hint(tmp_path, capsys, monkeypatch):
    path, conn = _db(tmp_path, [("blockiert", "[STRATEGIE] ueberspringen", "strategy")])
    conn.close()
    config_path = tmp_path / "memoryhooker.toml"
    config_path.write_text(
        f'[mode]\nactive = "clue"\n[backend]\nkind = "usmc"\npath = "{path.as_posix()}"\n'
        '[triggers]\nsources = ["strategy"]\n',
        encoding="utf-8",
    )
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"prompt": "ich bin blockiert"})))
    assert main(["--config", str(config_path), "--state-dir", str(tmp_path / "st"),
                 "hook-run", "UserPromptSubmit"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["hookSpecificOutput"]["additionalContext"] == "[STRATEGIE] ueberspringen"
