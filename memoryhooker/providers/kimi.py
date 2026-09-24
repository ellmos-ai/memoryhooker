from __future__ import annotations

from typing import Any

from hook_master.providers.kimi import KimiProvider as BaseKimiProvider

FORBIDDEN_EVENT = "PreToolUse"


class KimiProvider(BaseKimiProvider):
    """Kimi-Code-CLI-Provider fuer ``~/.kimi-code/config.toml`` (``[[hooks]]``)."""

    name = "kimi"
    events = ("UserPromptSubmit",)
    default_timeout = 15

    def hook_snippet(
        self, python_executable: str = "python", module: str = "memoryhooker"
    ) -> dict[str, Any]:
        self.validate_command(python_executable, self.default_timeout)
        cmd = f"{python_executable} -m {module} hook-run --format plain UserPromptSubmit"
        snippet = {
            "hooks": [
                self.format_hook("UserPromptSubmit", cmd, timeout=self.default_timeout)
            ]
        }
        assert FORBIDDEN_EVENT not in {h["event"] for h in snippet["hooks"]}, (
            "KimiProvider darf niemals PreToolUse-Hooks erzeugen (README-Kernregel)."
        )
        return snippet


__all__ = ["FORBIDDEN_EVENT", "KimiProvider"]
