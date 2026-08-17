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
from dataclasses import dataclass, replace

from .config import Config
from .protocol import Hit, MemoryBackend
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


# ---------------------------------------------------------------------------
# diagnose -- Ticket T-20260816-132994550, Befund 2.
#
# check/hook-run verschmelzen bewusst drei Gates (Config-Load, Session-Cap/
# Cooldown, Backend-Suche) zu einem opaken Ja/Nein -- ein Hook ohne Aussage
# darf nie wie ein Fehler aussehen. Das ist richtig fuer den Hook-Pfad, macht
# aber gezieltes Debuggen teuer: ein fehlendes --config sieht identisch aus
# wie "kein Treffer" (gemessene Kosten: eine volle Debugging-Runde).
# diagnose_prompt() bricht dieses Opaque nur fuer den EXPLIZIT angeforderten
# Diagnose-Pfad auf -- sie veraendert ``state`` nicht und zaehlt selbst nie
# als Injektion.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GateStatus:
    ok: bool
    detail: str


@dataclass(frozen=True)
class BackendDiagnosis:
    name: str
    available: bool
    hit_count: int
    top_rank: float | None


@dataclass(frozen=True)
class DiagnoseReport:
    mode: str
    session_cap: GateStatus
    cooldown: GateStatus
    backends: list[BackendDiagnosis]
    would_inject: str | None


def _session_cap_status(state: SessionState, config: Config) -> GateStatus:
    limit = config.mode.max_injections_per_session
    ok = state.injections_count < limit
    return GateStatus(ok, f"{state.injections_count}/{limit}")


def _cooldown_status(state: SessionState, config: Config, now: float) -> GateStatus:
    if state.last_injection_ts is None:
        return GateStatus(True, "noch keine Injektion in dieser Sitzung")
    remaining = config.mode.cooldown_seconds - (now - state.last_injection_ts)
    if remaining <= 0:
        return GateStatus(True, "bereit")
    return GateStatus(False, f"noch {remaining:.0f}s")


def _safe_available(backend: MemoryBackend) -> bool:
    try:
        return bool(backend.available())
    except Exception:
        return False


def _safe_search(backend: MemoryBackend, prompt: str, limit: int) -> list[Hit]:
    if not _safe_available(backend):
        return []
    try:
        return backend.search(prompt, limit=limit)
    except Exception:
        return []


def _iter_backend_links(backend: MemoryBackend) -> list[tuple[str, MemoryBackend]]:
    """Zerlegt eine (moegliche) ``ChainBackend`` in ihre einzelnen Glieder.

    Lokaler Import gegen einen Zyklus: ``backends`` importiert nichts aus
    ``modes``, aber ``modes`` sollte nicht global von ``backends`` abhaengen,
    nur um an ``ChainBackend`` heranzukommen.
    """
    from .backends import ChainBackend

    if isinstance(backend, ChainBackend):
        return [(type(link).__name__, link) for link in backend.backends]
    return [(type(backend).__name__, backend)]


_DIAGNOSE_SEARCH_LIMIT = 5


def diagnose_prompt(
    prompt: str,
    config: Config,
    backend: MemoryBackend,
    state: SessionState,
    *,
    now: float | None = None,
) -> DiagnoseReport:
    """Wertet die drei Gates einzeln aus, ohne ``state`` zu veraendern.

    Anders als :func:`evaluate_prompt` mutiert dieser Aufruf den State nicht
    und zaehlt nicht gegen ``max_injections_per_session`` -- ein explizit
    angefordertes Diagnose-Kommando darf das Budget nicht selbst verbrauchen.
    ``would_inject`` simuliert deshalb ``evaluate_prompt`` auf einer Kopie.
    """
    now = time.time() if now is None else now

    session_cap = _session_cap_status(state, config)
    cooldown = _cooldown_status(state, config, now)

    backends = []
    for name, link in _iter_backend_links(backend):
        hits = _safe_search(link, prompt, _DIAGNOSE_SEARCH_LIMIT)
        backends.append(
            BackendDiagnosis(
                name=name,
                available=_safe_available(link),
                hit_count=len(hits),
                top_rank=hits[0].rank if hits else None,
            )
        )

    # ``evaluate_prompt`` selbst faengt eine kaputte Backend-Instanz nicht ab
    # (nur ``ChainBackend`` tut das fuer ihre Glieder) -- das bleibt hier
    # bewusst unveraendert, um den Hook-Pfad nicht anzufassen. diagnose_prompt
    # ist aber genau dafuer da, ein kaputtes Backend sichtbar zu machen, statt
    # selbst daran zu scheitern: die Backend-Liste oben zeigt es bereits als
    # ``available=False``, deshalb faellt "wuerde einspielen" hier defensiv
    # auf ``None`` zurueck statt die Diagnose abzubrechen.
    simulated_state = replace(state)
    try:
        would_inject = evaluate_prompt(prompt, config, backend, simulated_state, now=now)
    except Exception:
        would_inject = None

    return DiagnoseReport(
        mode=config.mode.active,
        session_cap=session_cap,
        cooldown=cooldown,
        backends=backends,
        would_inject=would_inject,
    )
