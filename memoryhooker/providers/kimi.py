from __future__ import annotations

from pathlib import Path

FORBIDDEN_EVENT = "PreToolUse"


class KimiProvider:
    """Kimi-Code-CLI-Provider fuer ``~/.kimi-code/config.toml`` (``[[hooks]]``).

    Der Adapter folgt dem dokumentierten stdin/stdout-Vertrag des Hosts:

    - stdin-JSON: ``hook_event_name``, ``session_id``, ``cwd``; bei
      ``UserPromptSubmit`` ist ``prompt`` KEIN String, sondern eine
      Content-Block-Liste ``[{"type": "text", "text": ...}]`` (wird in
      ``cli._extract_prompt`` beruecksichtigt).
    - stdout-Text speist sich NUR bei ``UserPromptSubmit`` (Kontext) und
      ``Stop`` (Weiterfuehr-Nachricht) in den Fluss ein. ``SessionStart`` und
      ``PreCompact`` sind Beobachtungs-Events -- ihr Output wird verworfen.
      Sie werden deshalb absichtlich NICHT registriert: ein Hook, dessen
      Ausgabe nie ankommt, ist die im Auftrag beschriebene stille Falle.
    - Hooks laufen fail-open; Blockieren (Exit 2) nutzt dieses Modul nicht.
    - Ausgabe als Klartext (``hook-run --format plain``): Eine Auswertung von
      ``hookSpecificOutput.additionalContext``-JSON ist fuer Kimi nicht
      dokumentiert, die Klartext-Weitergabe dagegen schon.
    """

    name = "kimi"
    events = ("UserPromptSubmit",)

    def is_available(self) -> bool:
        # Existenz der CLI-Config ist das belegbare Minimum -- KEIN Nachweis
        # einer registrierten Hook-Verdrahtung (die bleibt ein manueller,
        # dokumentierter Schritt).
        return (Path.home() / ".kimi-code" / "config.toml").exists()

    def hook_snippet(
        self, python_executable: str = "python", module: str = "memoryhooker"
    ) -> dict:
        """Baustein fuer ``[[hooks]]`` in config.toml (TOML-Array-of-Tables).

        Wie bei den anderen Providern schreibt das Modul NIEMALS selbst in
        die echte Config -- Installation ist ein dokumentierter manueller
        Schritt. Config- und State-Pfade (``--config``/``--state-dir``)
        ergaenzt der Installierende.
        """
        snippet = {
            "hooks": [
                {
                    "event": "UserPromptSubmit",
                    "command": f"{python_executable} -m {module} hook-run --format plain UserPromptSubmit",
                    "timeout": 15,
                }
            ]
        }
        assert FORBIDDEN_EVENT not in {h["event"] for h in snippet["hooks"]}, (
            "KimiProvider darf niemals PreToolUse-Hooks erzeugen (README-Kernregel)."
        )
        return snippet
