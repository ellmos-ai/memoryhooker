"""Claude-Code-Provider: erzeugt die Hook-KONFIGURATION als Text/JSON.

Wichtig (Auftrag + README): Dieses Modul schreibt NIEMALS automatisch in
eine echte ``settings.json``. Installation ist ein dokumentierter manueller
Schritt -- ``hook_snippet()`` liefert nur den Baustein, den ein Mensch (oder
ein anderer, dafuer freigegebener Agent) selbst eintraegt.

Ereignisse ausschliesslich ``SessionStart`` und ``UserPromptSubmit`` --
niemals ``PreToolUse``.
"""

from __future__ import annotations

from typing import Any

from hook_master.providers.claude import ClaudeProvider as BaseClaudeProvider

FORBIDDEN_EVENT = "PreToolUse"


class ClaudeProvider(BaseClaudeProvider):
    name = "claude"
    events = ("SessionStart", "UserPromptSubmit")

    def hook_snippet(
        self, python_executable: str = "python", module: str = "memoryhooker"
    ) -> dict[str, Any]:
        """Baut den Hook-Konfigurationsblock fuer ``settings.json`` ueber super()."""
        snippet = super().hook_snippet(
            python_executable=python_executable,
            module=module,
            events=self.events,
            provider_arg=False,
        )
        assert FORBIDDEN_EVENT not in snippet["hooks"], (
            "ClaudeProvider darf niemals PreToolUse-Hooks erzeugen (README-Kernregel)."
        )
        return snippet


__all__ = ["FORBIDDEN_EVENT", "ClaudeProvider"]
