"""Die drei Betriebsmodi aus README.md, Abschnitt "Modi".

``evaluate_prompt()`` ist der Kern: sie wertet einen ``UserPromptSubmit``-
artigen Aufruf gegen den aktiven Modus aus und erzwingt dabei ueberall
dieselbe harte Guard-Logik (max. Injektionen/Sitzung + Cooldown).

``session_start_message()`` ist getrennt, weil ``SessionStart`` semantisch
etwas anderes ist als ein Prompt -- es gibt keinen "Suchzaehler", der hier
etwas ausloest, sondern schlicht: "gibt es ueberhaupt ein Backend?".
"""

from __future__ import annotations

import time

from .config import Config
from .protocol import MemoryBackend
from .state import SessionState

_SESSION_START_TEMPLATE = (
    "[MemoryHooker] Fuer dieses Projekt existiert ein durchsuchbares Gedaechtnis "
    "-- bei Bedarf gezielt danach suchen, statt Wissen neu herzuleiten."
)

_REMEMBER_TEMPLATE = (
    "[MemoryHooker] Du hast in dieser Sitzung bereits mehrfach gesucht -- "
    "es lohnt sich moeglicherweise, gezielt im Gedaechtnis-Backend nachzuschlagen."
)


def session_start_message(backend: MemoryBackend, state: SessionState) -> str | None:
    """Einmaliger Hinweis bei Sitzungsbeginn, unabhaengig vom aktiven Modus.

    Liefert nur einmal pro Sitzung eine Nachricht (``state.session_start_shown``)
    und nur, wenn ueberhaupt ein Backend verfuegbar ist.
    """
    if state.session_start_shown:
        return None
    if not backend.available():
        return None
    state.session_start_shown = True
    return _SESSION_START_TEMPLATE


def evaluate_prompt(
    prompt: str,
    config: Config,
    backend: MemoryBackend,
    state: SessionState,
    *,
    now: float | None = None,
) -> str | None:
    """Wertet einen Prompt gegen den aktiven Modus aus.

    Erzwingt die 4-Augen-Hook-Regel (siehe state.py): harte Obergrenze
    (``max_injections_per_session``) + Cooldown zwischen zwei Injektionen,
    unabhaengig davon, welcher Modus aktiv ist.
    """
    now = time.time() if now is None else now

    if state.injections_count >= config.mode.max_injections_per_session:
        return None
    if (
        state.last_injection_ts is not None
        and (now - state.last_injection_ts) < config.mode.cooldown_seconds
    ):
        return None

    if config.mode.active == "remember":
        message = _evaluate_remember(config, backend, state)
    elif config.mode.active == "clue":
        message = _evaluate_clue(prompt, config, backend)
    elif config.mode.active == "remember+search":
        message = _evaluate_search(prompt, config, backend)
    else:  # pragma: no cover - Config.validate() faengt das vorher ab
        raise ValueError(f"unbekannter Modus: {config.mode.active!r}")

    if message is not None:
        state.injections_count += 1
        state.last_injection_ts = now

    return message


def _evaluate_remember(config: Config, backend: MemoryBackend, state: SessionState) -> str | None:
    if not backend.available():
        return None
    if state.search_count < config.mode.search_after_n_searches:
        return None
    return _REMEMBER_TEMPLATE


def _evaluate_clue(prompt: str, config: Config, backend: MemoryBackend) -> str | None:
    lowered = prompt.lower()
    if not backend.available():
        return None
    for trigger in config.clue.triggers:
        if trigger.lower() not in lowered:
            continue
        hits = backend.search(trigger, limit=1)
        if hits and hits[0].rank >= config.mode.min_rank:
            hit = hits[0]
            return (
                f"[MemoryHooker] Stichwort '{trigger}' erkannt -- {hit.text} "
                f"(Quelle: {hit.source})"
            )
    return None


def _evaluate_search(prompt: str, config: Config, backend: MemoryBackend) -> str | None:
    if not backend.available():
        return None
    hits = [
        h for h in backend.search(prompt, limit=config.mode.max_hits)
        if h.rank >= config.mode.min_rank
    ]
    if not hits:
        return None
    lines = [f"- ({h.rank:.2f}) {h.text} [{h.source}]" for h in hits[: config.mode.max_hits]]
    return "[MemoryHooker] Gefundene Erkenntnisse:\n" + "\n".join(lines)
