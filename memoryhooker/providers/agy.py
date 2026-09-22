"""Antigravity (agy) Provider: erzeugt Hook-Konfiguration als Text/JSON.

Dieses Modul schreibt NIEMALS automatisch in eine echte hooks.json --
Installation ist ein dokumentierter manueller Schritt.

Antigravity nutzt hooks.json.
Für MemoryHooker verwenden wir PreInvocation (als Ersatz für SessionStart/UserPromptSubmit)
und PostToolUse (für record-search Zähler).
"""

from __future__ import annotations

from typing import Any

from hook_master.providers.agy import AgyProvider as BaseAgyProvider

FORBIDDEN_EVENT = "PreToolUse"


class AgyProvider(BaseAgyProvider):
    name = "agy"
    events = ("PreInvocation", "PostToolUse")

    def hook_snippet(
        self, python_executable: str = "python", module: str = "memoryhooker"
    ) -> dict[str, Any]:
        self.validate_command(python_executable)
        session_start_cmd = f"{python_executable} -m {module} hook-run SessionStart"
        user_prompt_cmd = f"{python_executable} -m {module} hook-run UserPromptSubmit"
        record_search_cmd = f"{python_executable} -m {module} record-search"

        snippet = {
            "hooks": {
                "PreInvocation": [
                    self.format_hook(session_start_cmd),
                    self.format_hook(user_prompt_cmd),
                ],
                "PostToolUse": [
                    self.format_hook(
                        record_search_cmd,
                        matcher="grep_search|view_file|list_dir|search_web",
                    )
                ],
            }
        }

        assert FORBIDDEN_EVENT not in snippet["hooks"], (
            "AgyProvider darf niemals PreToolUse-Hooks erzeugen (README-Kernregel)."
        )
        return snippet


__all__ = ["FORBIDDEN_EVENT", "AgyProvider"]
