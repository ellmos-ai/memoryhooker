from __future__ import annotations

from typing import Any

from hook_master.providers.codex import CodexProvider as BaseCodexProvider

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

    def hook_snippet(
        self, python_executable: str = "python", module: str = "memoryhooker"
    ) -> dict[str, Any]:
        snippet = super().hook_snippet(
            python_executable=python_executable,
            module=module,
            events=self.events,
            timeout=getattr(self, "default_timeout", 10),
            status_prefix="MemoryHooker",
            provider_arg=False,
        )
        assert FORBIDDEN_EVENT not in snippet["hooks"]
        return snippet


__all__ = ["FORBIDDEN_EVENT", "CodexProvider"]
