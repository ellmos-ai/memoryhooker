from __future__ import annotations

from typing import Any

from .invariants import validate_interpreter, validate_timeout

try:
    from hook_master.providers.codex import CodexProvider as BaseCodexProvider
except ImportError:
    from .base import BaseProvider as BaseCodexProvider

FORBIDDEN_EVENT = "PreToolUse"


class CodexProvider(BaseCodexProvider):
    """Codex-CLI-Provider für ``~/.codex/hooks.json``.

    MemoryHooker hängt nur an ``SessionStart`` und ``UserPromptSubmit``;
    ``PreToolUse`` bleibt wegen der Aufrufhäufigkeit ausdrücklich
    ausgeschlossen.
    """

    name = "codex"
    events = ("SessionStart", "UserPromptSubmit")
    default_timeout = 10

    def is_available(self) -> bool:
        return True

    def hook_snippet(
        self, python_executable: str = "python", module: str = "memoryhooker"
    ) -> dict[str, Any]:
        validate_interpreter(python_executable)

        def command(event: str) -> dict[str, Any]:
            value = f"{python_executable} -m {module} hook-run {event}"
            timeout = validate_timeout(getattr(self, "default_timeout", 10))
            return {
                "hooks": [
                    {
                        "type": "command",
                        "command": value,
                        "commandWindows": value,
                        "timeout": timeout,
                        "statusMessage": f"MemoryHooker: {event}",
                    }
                ]
            }

        snippet = {
            "hooks": {
                "SessionStart": [command("SessionStart")],
                "UserPromptSubmit": [command("UserPromptSubmit")],
            }
        }
        assert FORBIDDEN_EVENT not in snippet["hooks"]
        return snippet
