"""Antigravity (agy) Provider: erzeugt Hook-Konfiguration als Text/JSON.

Dieses Modul schreibt NIEMALS automatisch in eine echte hooks.json --
Installation ist ein dokumentierter manueller Schritt.

Antigravity nutzt hooks.json.
Für MemoryHooker verwenden wir PreInvocation (als Ersatz für SessionStart/UserPromptSubmit)
und PostToolUse (für record-search Zähler).
"""

from __future__ import annotations

FORBIDDEN_EVENT = "PreToolUse"


class AgyProvider:
    name = "agy"
    events = ("PreInvocation", "PostToolUse")

    def is_available(self) -> bool:
        return True

    def hook_snippet(self, python_executable: str = "python", module: str = "memoryhooker") -> dict:
        session_start_cmd = f"{python_executable} -m {module} hook-run SessionStart"
        user_prompt_cmd = f"{python_executable} -m {module} hook-run UserPromptSubmit"
        record_search_cmd = f"{python_executable} -m {module} record-search"

        snippet = {
            "hooks": {
                "PreInvocation": [
                    {"type": "command", "command": session_start_cmd},
                    {"type": "command", "command": user_prompt_cmd}
                ],
                "PostToolUse": [
                    {
                        "matcher": "grep_search|view_file|list_dir|search_web",
                        "hooks": [{"type": "command", "command": record_search_cmd}]
                    }
                ]
            }
        }

        assert FORBIDDEN_EVENT not in snippet["hooks"], (
            "AgyProvider darf niemals PreToolUse-Hooks erzeugen (README-Kernregel)."
        )
        return snippet
