"""Trigger-Injektor: feste Hinweise zu Stichwoertern aus ``context_triggers``.

Das ist das Gegenstueck zu BACHs Strategy-/Context-Injektoren (Programm
"Gemeinsames Gedaechtnis BACH = OCEAN", Stufe S3). Anders als die drei Modi
sucht dieser Pfad nicht im Gedaechtnis, sondern liest kuratierte Regeln
"Stichwort -> Hinweis" aus der gemeinsamen Tabelle ``context_triggers``
(Vertrag ``memory_union`` v2, in USMC und BACH identisch).

Er laeuft unabhaengig vom aktiven Modus und vom Session-Cap der Modi: jede
Quelle (``source``-Spalte, z. B. ``strategy``) hat ihren eigenen Cooldown und
liefert pro Prompt hoechstens einen Hinweis -- die erste passende Regel in
``id``-Reihenfolge. Ohne ``[triggers].sources`` in der Config bleibt der Pfad
aus.

``trigger_phrase`` darf Alternativen mit ``|`` tragen (``fehler|error|bug``).
So passt eine Regelgruppe in eine Zeile, ohne mit gleichlautenden Phrasen
anderer Quellen am ``UNIQUE(agent_id, trigger_phrase)`` zu kollidieren.
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime

from .config import Config
from .output_policy import sanitize_message
from .protocol import MemoryBackend
from .state import SessionState

DEFAULT_TRIGGER_COOLDOWN_SECONDS = 60


@dataclass(frozen=True)
class TriggerRule:
    phrases: tuple[str, ...]
    hint: str
    source: str
    rule_id: int | None = None

    @property
    def key(self) -> str:
        return f"{self.source}:{'|'.join(self.phrases)}"

    def matches(self, lowered_prompt: str) -> bool:
        return any(phrase in lowered_prompt for phrase in self.phrases)


def read_context_triggers(
    conn: sqlite3.Connection,
    sources: list[str],
    agent_id: str = "default",
    now: datetime | None = None,
) -> list[TriggerRule]:
    """Liest aktive Regeln der genannten Quellen, geordnet nach ``id``.

    Leseregel: ``is_active = 1``, ``status <> 'blocked'``, nicht abgelaufen,
    ``agent_id`` gleich dem eigenen oder ``'default'``. Fehlt die Tabelle,
    ist das Ergebnis leer -- nie ein Fehler.
    """
    if not sources:
        return []
    stamp = (now or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
    marks = ",".join("?" * len(sources))
    try:
        rows = conn.execute(
            f"""
            SELECT id, source, trigger_phrase, hint_text FROM context_triggers
            WHERE source IN ({marks})
              AND is_active = 1
              AND COALESCE(status, 'unknown') <> 'blocked'
              AND (expires_at IS NULL OR expires_at > ?)
              AND agent_id IN (?, 'default')
            ORDER BY id
            """,
            [*sources, stamp, agent_id],
        ).fetchall()
    except sqlite3.Error:
        return []
    rules = []
    for rule_id, source, phrase, hint in rows:
        phrases = tuple(p.strip().lower() for p in str(phrase or "").split("|") if p.strip())
        if phrases and hint:
            rules.append(TriggerRule(phrases=phrases, hint=str(hint), source=str(source),
                                     rule_id=rule_id))
    return rules


def backend_triggers(backend: MemoryBackend, sources: list[str], agent_id: str) -> list[TriggerRule]:
    """Regeln eines Backends; Backends ohne ``triggers()`` liefern keine.

    Bewusst ohne ``available()``: das meint "die Suche hat Daten" -- Regeln
    koennen auch in einem sonst leeren Gedaechtnis stehen. ``triggers()``
    selbst liefert bei fehlender Datei oder Tabelle eine leere Liste.
    """
    reader = getattr(backend, "triggers", None)
    if reader is None:
        return []
    try:
        return list(reader(sources, agent_id=agent_id))
    except Exception:
        return []


def evaluate_triggers(
    prompt: str,
    config: Config,
    backend: MemoryBackend,
    state: SessionState,
    *,
    now: float | None = None,
    fired: list[TriggerRule] | None = None,
) -> list[str]:
    """Hoechstens ein Hinweis je Injektor-Schluessel, mit Cooldown je Schluessel.

    Je Schluessel gewinnt die erste passende Regel in ``id``-Reihenfolge ueber
    alle seine Tabellenquellen. ``fired`` sammelt auf Wunsch die Regeln, die
    einen Hinweis geliefert haben (z. B. fuer Nutzungszaehler des Aufrufers).
    """
    cfg = config.triggers
    if not cfg.sources or not prompt:
        return []
    now = time.time() if now is None else now
    lowered = prompt.lower()
    hints = []
    for key in cfg.sources:
        cooldown = cfg.cooldowns.get(key, DEFAULT_TRIGGER_COOLDOWN_SECONDS)
        if now - state.trigger_last_ts.get(key, float("-inf")) < cooldown:
            continue
        for rule in backend_triggers(backend, cfg.table_sources(key), cfg.agent_id):
            once = rule.source in cfg.once_per_session
            if not rule.matches(lowered) or (once and rule.key in state.trigger_once):
                continue
            hint = sanitize_message(cfg.prefixes.get(key, "") + rule.hint, config.output)
            if not hint:
                continue
            if once:
                state.trigger_once.append(rule.key)
            state.trigger_last_ts[key] = now
            hints.append(hint)
            if fired is not None:
                fired.append(rule)
            break
    return hints
