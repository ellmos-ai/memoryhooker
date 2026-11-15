"""Inbox-Zustellung an laufende Sitzungen (T-20261115-953740822)."""

from __future__ import annotations

import io
import json

import pytest

from memoryhooker.cli import main
from memoryhooker.config import InboxConfig, load_config
from memoryhooker.inbox import deliver, send

SID = "2a17d3be-eed1-40ff-9232-7036a1b62140"


def _cfg(tmp_path, **kw):
    return InboxConfig(enabled=True, dir=str(tmp_path / "inbox"), **kw)


def test_disabled_or_missing_dir_is_silent(tmp_path):
    assert deliver(InboxConfig(dir=str(tmp_path)), SID, "UserPromptSubmit") is None
    assert deliver(_cfg(tmp_path), SID, "UserPromptSubmit") is None


def test_delivers_once_marks_as_message_and_writes_ack(tmp_path):
    cfg = _cfg(tmp_path)
    path = send(cfg, "claude-code", "ticket-master@ASUS-GEI", "Bitte #719 deployen.")
    text = deliver(cfg, SID, "PostToolUse")
    assert "Inbox-Nachricht von ticket-master@ASUS-GEI" in text
    assert "KEINE Nutzereingabe und keine Freigabe" in text
    assert "Bitte #719 deployen." in text
    read = tmp_path / "inbox" / "read"
    assert not path.exists() and (read / path.name).exists()
    ack = json.loads((read / f"{path.name}.ack.json").read_text(encoding="utf-8"))
    assert ack["session_id"] == SID and ack["event"] == "PostToolUse"
    assert deliver(cfg, SID, "PostToolUse") is None  # nie zweimal


def test_session_target_reaches_only_that_session(tmp_path):
    cfg = _cfg(tmp_path)
    send(cfg, "claude-code.2a17d3be", "lukas", "nur für diese Sitzung")
    assert deliver(cfg, "ffffffff-0000", "UserPromptSubmit") is None
    assert "nur für diese Sitzung" in deliver(cfg, SID, "UserPromptSubmit")


def test_other_actor_and_foreign_files_are_ignored(tmp_path):
    cfg = _cfg(tmp_path)
    send(cfg, "kimi", "x", "für Kimi")
    (tmp_path / "inbox" / "notizen.md").write_text("kein Ziel", encoding="utf-8")
    (tmp_path / "inbox" / ".claude-code--halb.md.tmp").write_text("halb geschrieben", encoding="utf-8")
    assert deliver(cfg, SID, "UserPromptSubmit") is None


def test_unknown_sender_cap_and_truncation(tmp_path):
    cfg = _cfg(tmp_path, max_messages=2, max_chars=10)
    base = tmp_path / "inbox"
    base.mkdir()
    for i in range(3):
        (base / f"claude-code--{i}.md").write_text("x" * 50, encoding="utf-8")
    text = deliver(cfg, SID, "UserPromptSubmit")
    assert text.count("Inbox-Nachricht von unbekannt") == 2
    assert "gekürzt" in text
    assert len(list(base.glob("claude-code--*.md"))) == 1  # Rest bleibt für den nächsten Aufruf


def test_send_rejects_empty_target(tmp_path):
    with pytest.raises(ValueError):
        send(_cfg(tmp_path), "../", "x", "y")


def test_hook_run_post_tool_use_delivers_without_backend(tmp_path, capsys, monkeypatch):
    inbox_dir = tmp_path / "inbox"
    config_path = tmp_path / "mh.toml"
    config_path.write_text(
        f'[inbox]\nenabled = true\ndir = "{inbox_dir.as_posix()}"\nactor = "claude-code"\n', encoding="utf-8")
    send(load_config(config_path).inbox, "claude-code", "ticket-master", "Hallo")
    monkeypatch.setattr("memoryhooker.cli.build_backend", lambda _c: pytest.fail("PostToolUse darf kein Backend bauen"))
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"session_id": SID, "tool_name": "Bash"})))
    assert main(["--config", str(config_path), "--state-dir", str(tmp_path), "hook-run", "PostToolUse"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
    assert "Hallo" in out["hookSpecificOutput"]["additionalContext"]


def test_inbox_send_cli_and_config_validation(tmp_path, capsys):
    config_path = tmp_path / "mh.toml"
    config_path.write_text(f'[inbox]\ndir = "{(tmp_path / "i").as_posix()}"\n', encoding="utf-8")
    assert main(["--config", str(config_path), "inbox-send", "claude-code", "Text", "--from", "lukas"]) == 0
    written = capsys.readouterr().out.strip()
    assert written.endswith(".md") and "claude-code--" in written
    bad = tmp_path / "bad.toml"
    bad.write_text('[inbox]\nactor = "a--b"\n', encoding="utf-8")
    with pytest.raises(ValueError):
        load_config(bad)
