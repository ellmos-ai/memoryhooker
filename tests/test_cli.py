import json
from pathlib import Path

from memoryhooker.cli import main


def _write_config(tmp_path: Path, memories_dir: Path, *, active="remember", search_after_n_searches=0) -> Path:
    config_path = tmp_path / "memoryhooker.toml"
    config_path.write_text(
        f"""
[mode]
active = "{active}"
search_after_n_searches = {search_after_n_searches}
max_hits = 3
min_rank = 0.1
max_injections_per_session = 5

[backend]
kind = "files"
path = "{memories_dir.as_posix()}"
""",
        encoding="utf-8",
    )
    return config_path


def test_check_prints_message_when_remember_mode_and_threshold_met(tmp_path, capsys):
    memories = tmp_path / "memories"
    memories.mkdir()
    (memories / "note.md").write_text("MemoryHooker Notiz", encoding="utf-8")

    config_path = _write_config(tmp_path, memories, active="remember", search_after_n_searches=0)
    state_dir = tmp_path / "state"

    exit_code = main(
        ["--config", str(config_path), "--state-dir", str(state_dir), "check", "irgendein prompt"]
    )
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "MemoryHooker" in out


def test_check_silent_when_backend_missing(tmp_path, capsys):
    config_path = _write_config(tmp_path, tmp_path / "does-not-exist")
    state_dir = tmp_path / "state"

    exit_code = main(["--config", str(config_path), "--state-dir", str(state_dir), "check", "prompt"])
    assert exit_code == 0
    assert capsys.readouterr().out == ""


def test_record_search_then_check_fires_remember(tmp_path, capsys):
    memories = tmp_path / "memories"
    memories.mkdir()
    (memories / "note.md").write_text("Inhalt", encoding="utf-8")

    config_path = _write_config(tmp_path, memories, active="remember", search_after_n_searches=2)
    state_dir = tmp_path / "state"
    common = ["--config", str(config_path), "--state-dir", str(state_dir)]

    main(common + ["record-search"])
    main(common + ["record-search"])
    exit_code = main(common + ["check", "prompt"])

    assert exit_code == 0
    assert "MemoryHooker" in capsys.readouterr().out


def test_session_start_command(tmp_path, capsys):
    memories = tmp_path / "memories"
    memories.mkdir()
    (memories / "note.md").write_text("Inhalt", encoding="utf-8")
    config_path = _write_config(tmp_path, memories)
    state_dir = tmp_path / "state"

    main(["--config", str(config_path), "--state-dir", str(state_dir), "session-start"])
    out = capsys.readouterr().out
    assert "MemoryHooker" in out


def test_providers_command_lists_all_and_chosen(tmp_path, capsys):
    exit_code = main(["--state-dir", str(tmp_path), "providers"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "claude: verfuegbar" in out
    assert "codex: verfuegbar" in out
    assert "agy: verfuegbar" in out
    assert "git: nicht verfuegbar" in out
    assert "manual: verfuegbar" in out
    assert "gewaehlt: claude" in out


def test_install_snippet_never_touches_real_settings_and_has_no_pretooluse(tmp_path, capsys):
    out_path = tmp_path / "snippet.json"
    exit_code = main(["--state-dir", str(tmp_path), "install-snippet", "--out", str(out_path)])
    assert exit_code == 0
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert "PreToolUse" not in data["hooks"]
    assert set(data["hooks"]) == {"SessionStart", "UserPromptSubmit"}


def test_install_snippet_supports_agy_provider(tmp_path, capsys):
    out_path = tmp_path / "snippet_agy.json"
    exit_code = main(["--state-dir", str(tmp_path), "install-snippet", "--provider", "agy", "--out", str(out_path)])
    assert exit_code == 0
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert "PreToolUse" not in data["hooks"]
    assert set(data["hooks"]) == {"PreInvocation", "PostToolUse"}


def test_hook_run_user_prompt_submit_reads_stdin_json(tmp_path, capsys, monkeypatch):
    memories = tmp_path / "memories"
    memories.mkdir()
    (memories / "note.md").write_text("MemoryHooker Inhalt", encoding="utf-8")
    config_path = _write_config(tmp_path, memories, active="remember", search_after_n_searches=0)
    state_dir = tmp_path / "state"

    import io

    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"prompt": "hallo welt"})))
    exit_code = main(
        ["--config", str(config_path), "--state-dir", str(state_dir), "hook-run", "UserPromptSubmit"]
    )
    assert exit_code == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    assert "MemoryHooker" in payload["hookSpecificOutput"]["additionalContext"]


def test_hook_run_without_prompt_field_is_silent(tmp_path, capsys, monkeypatch):
    memories = tmp_path / "memories"
    memories.mkdir()
    (memories / "note.md").write_text("Inhalt", encoding="utf-8")
    config_path = _write_config(tmp_path, memories, active="remember", search_after_n_searches=0)
    state_dir = tmp_path / "state"

    import io

    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"unrelated_field": "x"})))
    exit_code = main(
        ["--config", str(config_path), "--state-dir", str(state_dir), "hook-run", "UserPromptSubmit"]
    )
    assert exit_code == 0
    assert capsys.readouterr().out == ""


def _hook_run(config_path, state_dir, event, payload, monkeypatch):
    import io

    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    return main(["--config", str(config_path), "--state-dir", str(state_dir), "hook-run", event])


def test_hook_run_trennt_state_nach_session_id_aus_stdin(tmp_path, capsys, monkeypatch):
    """Regression: Sitzungskennung kommt NUR aus dem stdin-JSON.

    Vor dem Fix (2026-07-27) wurde der State-Pfad aus ``args.session_id``
    gebildet, bevor stdin ueberhaupt gelesen war -- also landeten alle Sitzungen
    in ``session-default.json``. Folge: ``session_start_shown`` blieb dauerhaft
    true, der Reminder feuerte genau einmal im Leben, und aus
    ``max_injections_per_session`` wurde faktisch "max_injections_ueberhaupt".
    ``--session-id`` konnte das nicht heilen, weil Claude Code in Hook-Kommandos
    keine Variablen ersetzt.
    """
    memories = tmp_path / "memories"
    memories.mkdir()
    (memories / "note.md").write_text("MemoryHooker Inhalt", encoding="utf-8")
    config_path = _write_config(tmp_path, memories)
    state_dir = tmp_path / "state"

    assert _hook_run(config_path, state_dir, "SessionStart", {"session_id": "A"}, monkeypatch) == 0
    assert capsys.readouterr().out.strip(), "erste Sitzung muss melden"

    # Gleiche Sitzung erneut: Der Guard muss greifen.
    assert _hook_run(config_path, state_dir, "SessionStart", {"session_id": "A"}, monkeypatch) == 0
    assert capsys.readouterr().out == "", "zweiter Aufruf derselben Sitzung muss schweigen"

    # Andere Sitzung: eigener State, muss wieder melden.
    assert _hook_run(config_path, state_dir, "SessionStart", {"session_id": "B"}, monkeypatch) == 0
    assert capsys.readouterr().out.strip(), "neue Sitzung darf nicht vom Guard der alten getroffen werden"

    namen = sorted(p.name for p in state_dir.iterdir())
    assert namen == ["session-A.json", "session-B.json"], namen


def test_session_id_aus_stdin_wird_dateinamentauglich_entschaerft(tmp_path, monkeypatch):
    """Die Kennung wandert in einen Dateinamen und kommt von aussen."""
    memories = tmp_path / "memories"
    memories.mkdir()
    config_path = _write_config(tmp_path, memories)
    state_dir = tmp_path / "state"

    assert _hook_run(
        config_path, state_dir, "SessionStart", {"session_id": "../../boese/x"}, monkeypatch
    ) == 0

    geschrieben = list(state_dir.iterdir())
    assert len(geschrieben) == 1
    assert geschrieben[0].parent == state_dir, "darf den State-Ordner nicht verlassen"
    assert geschrieben[0].name == "session-boesex.json", geschrieben[0].name


def test_cli_session_id_schlaegt_stdin(tmp_path, monkeypatch):
    """Manuelle Aufrufe und Tests muessen weiter steuern koennen."""
    memories = tmp_path / "memories"
    memories.mkdir()
    config_path = _write_config(tmp_path, memories)
    state_dir = tmp_path / "state"

    import io

    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"session_id": "aus-stdin"})))
    assert main([
        "--config", str(config_path), "--state-dir", str(state_dir),
        "--session-id", "explizit", "hook-run", "SessionStart",
    ]) == 0

    assert [p.name for p in state_dir.iterdir()] == ["session-explizit.json"]


def test_hook_run_accepts_kimi_content_block_prompt(tmp_path, capsys, monkeypatch):
    """Kimi Code sendet "prompt" als Content-Block-Liste
    [{"type": "text", "text": ...}] -- empirisch belegt per Capture-Probe
    gegen CLI 0.29.2 am 2026-07-28. Ohne diese Extraktion bliebe der Hook
    unter Kimi stumm (leere Ausgabe, Exit 0)."""
    memories = tmp_path / "memories"
    memories.mkdir()
    (memories / "note.md").write_text("MemoryHooker Inhalt", encoding="utf-8")
    config_path = _write_config(tmp_path, memories, active="remember", search_after_n_searches=0)
    state_dir = tmp_path / "state"

    import io

    payload = {
        "hook_event_name": "UserPromptSubmit",
        "session_id": "kimi-probe",
        "cwd": str(tmp_path),
        "prompt": [{"type": "text", "text": "hallo welt"}],
    }
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    exit_code = main(
        ["--config", str(config_path), "--state-dir", str(state_dir), "hook-run", "UserPromptSubmit"]
    )
    assert exit_code == 0
    out = capsys.readouterr().out
    payload_out = json.loads(out)
    assert "MemoryHooker" in payload_out["hookSpecificOutput"]["additionalContext"]


def test_hook_run_plain_format_prints_bare_message(tmp_path, capsys, monkeypatch):
    """--format plain: kein JSON-Wrapper -- Kimi speist stdout-Klartext ein,
    eine hookSpecificOutput-Auswertung ist dort nicht dokumentiert."""
    memories = tmp_path / "memories"
    memories.mkdir()
    (memories / "note.md").write_text("MemoryHooker Inhalt", encoding="utf-8")
    config_path = _write_config(tmp_path, memories, active="remember", search_after_n_searches=0)
    state_dir = tmp_path / "state"

    import io

    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"prompt": "hallo"})))
    exit_code = main(
        [
            "--config", str(config_path), "--state-dir", str(state_dir),
            "hook-run", "--format", "plain", "UserPromptSubmit",
        ]
    )
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "MemoryHooker" in out
    assert not out.strip().startswith("{")


def test_record_search_zaehlt_in_die_sitzung_aus_stdin(tmp_path, monkeypatch):
    """Regression: Auch ``record-search`` liest die Sitzungskennung aus stdin.

    Der Befehl laeuft als PostToolUse-Hook -- dort steht die Kennung
    ausschliesslich im stdin-JSON, weil Claude Code in Hook-Kommandos keine
    Variablen ersetzt. Ohne das Lesen landet JEDER Suchzaehler in
    ``session-default.json``, waehrend die echte Sitzung bei 0 bleibt.
    Getroffen wird damit genau die Funktion, fuer die der Zaehler existiert:
    ``search_after_n_searches`` wird nie erreicht, das Modul blendet nie
    Treffer ein, sondern hoechstens den generischen SessionStart-Anstoss.

    Gemessen auf ASUS-GEI am 2026-08-01: drei Aufrufe mit Kennung im Payload
    erhoehten session-default.json auf 3, die Sitzungsdatei blieb bei 0.
    """
    import io
    import json as _json

    state_dir = tmp_path / "state"
    for _ in range(3):
        monkeypatch.setattr(
            "sys.stdin", io.StringIO(_json.dumps({"session_id": "S1"}))
        )
        assert main(["--state-dir", str(state_dir), "record-search"]) == 0

    geschrieben = sorted(p.name for p in state_dir.iterdir())
    assert geschrieben == ["session-S1.json"], geschrieben
    zustand = _json.loads((state_dir / "session-S1.json").read_text(encoding="utf-8"))
    assert zustand["search_count"] == 3


def test_record_search_session_id_option_behaelt_vorrang(tmp_path, monkeypatch):
    """Manuelle Aufrufe und Tests muessen weiterhin steuern koennen."""
    import io
    import json as _json

    state_dir = tmp_path / "state"
    monkeypatch.setattr("sys.stdin", io.StringIO(_json.dumps({"session_id": "AUS_STDIN"})))
    assert main([
        "--state-dir", str(state_dir), "--session-id", "EXPLIZIT", "record-search",
    ]) == 0
    assert [p.name for p in state_dir.iterdir()] == ["session-EXPLIZIT.json"]
