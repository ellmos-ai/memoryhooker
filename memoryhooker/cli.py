"""CLI -- manueller Aufruf und Wiring-Schicht für Hook-Provider.

Befehle:

  python -m memoryhooker check "<prompt>"     manueller Aufruf (Auftrag)
  python -m memoryhooker hook-run <event>      liest stdin-JSON, gibt
                                                 Hook-Output aus
  python -m memoryhooker record-search         zaehlt eine Suche (fuer den
                                                 PostToolUse-Zaehler aus der
                                                 ROADMAP, manuell aufgerufen)
  python -m memoryhooker session-start          SessionStart-Reminder
  python -m memoryhooker providers              zeigt Provider-Fallback-Kette
  python -m memoryhooker install-snippet        druckt/schreibt einen
                                                 Provider-Hook-Snippet

Jeder Befehl gibt bei "nichts zu sagen" einfach keine Ausgabe UND Exit-Code 0
-- ein Hook, der nichts einzuspielen hat, darf niemals wie ein Fehler wirken.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .backends import build_backend
from .config import Config, load_config
from .modes import evaluate_prompt, session_start_message
from .providers import PROVIDER_REGISTRY, resolve_provider
from .providers.claude import ClaudeProvider
from .state import SessionState, default_state_dir, state_path_for_session

# Kandidaten-Feldnamen fuer den Prompt-Text im UserPromptSubmit-stdin-JSON.
# ACHTUNG (siehe ROADMAP.md, "Zu verifizieren, bevor gebaut wird"): der
# exakte Feldname ist zum Zeitpunkt dieses MVP NICHT gegen die Claude-Code-
# Doku verifiziert. Es wird defensiv durch mehrere plausible Kandidaten
# probiert -- findet sich keiner, bleibt der Hook stumm statt zu raten.
_PROMPT_FIELD_CANDIDATES = ("prompt", "user_prompt", "text", "message")


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="memoryhooker")
    parser.add_argument("--config", type=Path, default=None, help="Pfad zu memoryhooker.toml")
    parser.add_argument("--state-dir", type=Path, default=None, help="Override fuer den State-Ordner")
    parser.add_argument("--session-id", default=None, help="Session-ID zur State-Trennung")

    sub = parser.add_subparsers(required=True)

    p_check = sub.add_parser("check", help="Prompt gegen den aktiven Modus auswerten")
    p_check.add_argument("prompt")
    p_check.set_defaults(func=_cmd_check)

    p_hook = sub.add_parser("hook-run", help="stdin-JSON lesen und Hook-Output schreiben")
    p_hook.add_argument("event", choices=["SessionStart", "UserPromptSubmit"])
    p_hook.add_argument(
        "--format",
        dest="output_format",
        choices=["json", "plain"],
        default="json",
        help="Ausgabeformat: json (Claude/Codex, hookSpecificOutput) oder plain (Kimi: Klartext)",
    )
    p_hook.set_defaults(func=_cmd_hook_run)

    p_search = sub.add_parser("record-search", help="Suchzaehler dieser Sitzung erhoehen")
    p_search.set_defaults(func=_cmd_record_search)

    p_start = sub.add_parser("session-start", help="SessionStart-Reminder ausgeben")
    p_start.set_defaults(func=_cmd_session_start)

    p_providers = sub.add_parser("providers", help="Provider-Fallback-Kette anzeigen")
    p_providers.set_defaults(func=_cmd_providers)

    p_install = sub.add_parser("install-snippet", help="Hook-Snippet ausgeben")
    p_install.add_argument(
        "--provider",
        default="claude",
        choices=list(PROVIDER_REGISTRY.keys()),
        help="Provider (claude, agy, ...)",
    )
    p_install.add_argument("--out", type=Path, default=None)
    p_install.set_defaults(func=_cmd_install_snippet)

    return parser


def _load(args) -> tuple[Config, "object"]:
    config = load_config(args.config)
    backend = build_backend(config)
    return config, backend


def _state_path(args) -> Path:
    return state_path_for_session(args.session_id, args.state_dir)


def _cmd_check(args) -> int:
    config, backend = _load(args)
    state_path = _state_path(args)
    state = SessionState.load(state_path)

    message = evaluate_prompt(args.prompt, config, backend, state)

    state.save(state_path)
    if message:
        print(message)
    return 0


def _cmd_session_start(args) -> int:
    config, backend = _load(args)
    state_path = _state_path(args)
    state = SessionState.load(state_path)

    message = session_start_message(backend, state)

    state.save(state_path)
    if message:
        print(message)
    return 0


def _cmd_record_search(args) -> int:
    state_path = _state_path(args)
    state = SessionState.load(state_path)
    state.record_search()
    state.save(state_path)
    return 0


def _cmd_providers(args) -> int:
    config = load_config(args.config)
    for name in config.providers.order:
        provider = PROVIDER_REGISTRY.get(name)
        available = provider.is_available() if provider else False
        marker = "verfuegbar" if available else "nicht verfuegbar"
        print(f"{name}: {marker}")
    chosen = resolve_provider(config.providers)
    print(f"gewaehlt: {chosen.name}")
    return 0


def _cmd_install_snippet(args) -> int:
    provider_name = getattr(args, "provider", "claude")
    provider = PROVIDER_REGISTRY.get(provider_name, ClaudeProvider())
    snippet = provider.hook_snippet()
    text = json.dumps(snippet, indent=2, ensure_ascii=False)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
        print(f"geschrieben nach {args.out} -- manuell in Config einmischen", file=sys.stderr)
    else:
        print(text)
    return 0


def _cmd_hook_run(args) -> int:
    config, backend = _load(args)

    # stdin MUSS vor dem State gelesen werden: Die Sitzungskennung steht nur dort.
    payload = _read_stdin_json()

    # Ohne diese Zeile landen ALLE Sitzungen in session-default.json. Der
    # Session-Guard verliert damit seinen Sinn: `session_start_shown` bleibt fuer
    # immer true (der SessionStart-Reminder feuert genau EINMAL im Leben) und aus
    # `max_injections_per_session` wird faktisch "max_injections_ueberhaupt".
    # `--session-id` allein reicht nicht: Ein Hook-Kommando in settings.json kann
    # sie nicht fuellen, weil Claude Code dort keine Variablen ersetzt. Die
    # Kennung kommt ausschliesslich im stdin-JSON. Die CLI-Option behaelt Vorrang,
    # damit manuelle Aufrufe und Tests weiterhin steuern koennen.
    state_path = state_path_for_session(
        args.session_id or _extract_session_id(payload), args.state_dir
    )
    state = SessionState.load(state_path)

    if args.event == "SessionStart":
        message = session_start_message(backend, state)
    else:
        prompt = _extract_prompt(payload)
        message = evaluate_prompt(prompt, config, backend, state) if prompt is not None else None

    state.save(state_path)

    if message:
        output = {
            "hookSpecificOutput": {
                "hookEventName": args.event,
                "additionalContext": message,
            }
        }
        if args.output_format == "plain":
            # Kimi Code speist Klartext auf stdout als Kontext ein; eine
            # Auswertung von hookSpecificOutput-JSON ist dort nicht dokumentiert.
            print(message)
        else:
            print(json.dumps(output, ensure_ascii=False))
    return 0


def _read_stdin_json() -> dict:
    if sys.stdin.isatty():
        return {}
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def _extract_session_id(payload: dict) -> str | None:
    """Sitzungskennung aus dem Hook-stdin-JSON, dateinamentauglich gemacht.

    Der Wert wandert in einen Dateinamen (``session-<id>.json``), deshalb bleiben
    nur unbedenkliche Zeichen stehen. Claude Code liefert UUIDs, aber der Wert
    kommt von aussen -- ein ``..`` oder ein Pfadtrenner darf nicht durchschlagen.
    Bleibt nichts uebrig, wird ``None`` zurueckgegeben: dann greift wie bisher
    ``session-default.json``, statt einen kaputten Namen zu bauen.
    """
    raw = payload.get("session_id")
    if not isinstance(raw, str):
        return None
    sicher = "".join(z for z in raw if z.isalnum() or z in "-_")[:64]
    return sicher or None


def _extract_prompt(payload: dict) -> str | None:
    for field in _PROMPT_FIELD_CANDIDATES:
        value = payload.get(field)
        if isinstance(value, str) and value.strip():
            return value
        # Kimi Code liefert den Prompt NICHT als String, sondern als
        # Content-Block-Liste: "prompt": [{"type": "text", "text": "..."}]
        # Ohne diesen Zweig bliebe der Hook unter Hosts mit strukturiertem
        # Prompt-Payload stumm.
        if isinstance(value, list):
            parts = [
                block["text"]
                for block in value
                if isinstance(block, dict)
                and block.get("type") == "text"
                and isinstance(block.get("text"), str)
            ]
            joined = "\n".join(part for part in parts if part.strip())
            if joined.strip():
                return joined
    return None


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
