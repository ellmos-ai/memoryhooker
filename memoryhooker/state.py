"""Session-Zustand: Zaehler + Cooldown fuer die 4-Augen-Hook-Regel.

Aus ``~/CLAUDE.md``, Abschnitt "Arbeitsweise": *"Hooks (atexit, signal,
startup, cron, etc.) immer doppelt pruefen: (1) Wird der Hook bei
wiederholtem Aufruf mehrfach registriert? Guard/Flag nutzen. (2) Ist die
Hook-Aktion idempotent oder frequenz-begrenzt?"*

Dieses Modul liefert genau diesen Guard: eine harte Obergrenze
(``max_injections_per_session``) plus einen Cooldown zwischen zwei
Injektionen, persistiert als kleine JSON-Datei -- damit ein Hook, der bei
jedem Prompt neu als Subprozess startet, trotzdem "weiss", wie oft er in
dieser Sitzung schon gesprochen hat.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path


def default_state_dir() -> Path:
    return Path(os.environ.get("MEMORYHOOKER_STATE_DIR", Path.home() / ".memoryhooker"))


def state_path_for_session(session_id: str | None, state_dir: Path | None = None) -> Path:
    directory = state_dir or default_state_dir()
    name = f"session-{session_id}.json" if session_id else "session-default.json"
    return directory / name


def _today() -> str:
    """Lokaler Kalendertag, ISO-Format (YYYY-MM-DD) -- die TTL-Einheit fuer
    :meth:`SessionState.load`."""
    return time.strftime("%Y-%m-%d")


@dataclass
class SessionState:
    injections_count: int = 0
    search_count: int = 0
    # None = "noch keine Injektion in dieser Sitzung" -- bewusst kein 0.0 als
    # Sentinel, weil 0.0 ein gueltiger (falsy!) Zeitstempel ist und damit den
    # Cooldown-Check in modes.py stillschweigend uebersprungen haette
    # (empirisch gefangener Bug, siehe tests/test_modes.py).
    last_injection_ts: float | None = None
    session_start_shown: bool = False
    # TTL fuer den Cap-Guard (Ticket T-20260816-132994550, Befund 1): ohne
    # das blieb z. B. ``session-default.json`` -- der Zustand fuer JEDEN
    # manuellen Aufruf ohne ``session_id`` im Hook-Payload und ohne
    # ``--session-id``, etwa bei manuellem Testen/Debuggen -- dauerhaft am
    # Cap haengen, weil es dafuer keinen Reset gab (gemessen auf ASUS-GEI
    # 2026-08-16: injections_count=5=max, search_count=65). state_date haelt
    # den Kalendertag der letzten Schreibung fest; load() erkennt sowohl
    # einen neuen Tag als auch eine Alt-Datei aus der Zeit vor diesem Feld.
    state_date: str = field(default_factory=_today)

    @classmethod
    def load(cls, path: Path) -> "SessionState":
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return cls()
        today = _today()
        if "state_date" not in data or data.get("state_date") != today:
            # Neuer Kalendertag ODER Alt-Datei ohne state_date-Feld (aus der
            # Zeit vor diesem Fix) -- beides heisst: frisch anfangen statt
            # den Cap-Guard auf ewig blockiert zu lassen.
            return cls(state_date=today)
        known = {f: data[f] for f in cls.__dataclass_fields__ if f in data}
        return cls(**known)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self)), encoding="utf-8")

    def record_search(self) -> None:
        self.search_count += 1
