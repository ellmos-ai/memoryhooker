from __future__ import annotations

FORBIDDEN_EVENT = "PreToolUse"


class CodexProvider:
    """Codex-CLI-Provider für ``~/.codex/hooks.json``.

    MemoryHooker hängt nur an ``SessionStart`` und ``UserPromptSubmit``;
    ``PreToolUse`` bleibt wegen der Aufrufhäufigkeit ausdrücklich
    ausgeschlossen.
    """

    name = "codex"
    events = ("SessionStart", "UserPromptSubmit")

    def is_available(self) -> bool:
        return True

    def hook_snippet(
        self, python_executable: str = "python", module: str = "memoryhooker"
    ) -> dict:
        def command(event: str) -> dict:
            value = f"{python_executable} -m {module} hook-run {event}"
            return {
                "hooks": [
                    {
                        "type": "command",
                        "command": value,
                        "commandWindows": value,
                        "timeout": 10,
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
