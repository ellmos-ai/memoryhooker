"""Claude-Code-Provider: erzeugt die Hook-KONFIGURATION als Text/JSON.

Wichtig (Auftrag + README): Dieses Modul schreibt NIEMALS automatisch in
eine echte ``settings.json``. Installation ist ein dokumentierter manueller
Schritt -- ``hook_snippet()`` liefert nur den Baustein, den ein Mensch (oder
ein anderer, dafuer freigegebener Agent) selbst eintraegt.

Ereignisse ausschliesslich ``SessionStart`` und ``UserPromptSubmit`` --
niemals ``PreToolUse``.
"""

from __future__ import annotations

FORBIDDEN_EVENT = "PreToolUse"


class ClaudeProvider:
    name = "claude"
    events = ("SessionStart", "UserPromptSubmit")

    def is_available(self) -> bool:
        # Kein Laufzeit-Check moeglich (keine settings.json-Introspektion aus
        # dem Modul heraus vorgesehen) -- claude ist der Default-Provider,
        # fuer den dieses Modul in erster Linie gebaut ist.
        return True

    def hook_snippet(self, python_executable: str = "python", module: str = "memoryhooker") -> dict:
        """Baut den Hook-Konfigurationsblock fuer ``settings.json``.

        Der Aufrufer entscheidet, ob/wie er das in eine echte Config
        einmischt -- dieses Modul tut das nicht selbst.
        """
        session_start_cmd = f"{python_executable} -m {module} hook-run SessionStart"
        user_prompt_cmd = f"{python_executable} -m {module} hook-run UserPromptSubmit"

        snippet = {
            "hooks": {
                "SessionStart": [
                    {"hooks": [{"type": "command", "command": session_start_cmd}]}
                ],
                "UserPromptSubmit": [
                    {"hooks": [{"type": "command", "command": user_prompt_cmd}]}
                ],
            }
        }
        assert FORBIDDEN_EVENT not in snippet["hooks"], (
            "ClaudeProvider darf niemals PreToolUse-Hooks erzeugen (README-Kernregel)."
        )
        return snippet
