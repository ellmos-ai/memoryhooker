"""Config-Schema fuer MemoryHooker (siehe README.md, Abschnitt "Modi").

Alle Werte haben Defaults, die dem README entsprechen -- ein Modul ohne
``memoryhooker.toml`` laeuft also bereits mit dem zurueckhaltendsten Verhalten
(``remember``-Modus).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from . import _toml

VALID_MODES = ("remember", "clue", "remember+search")
VALID_BACKENDS = ("files", "gardener", "usmc", "bach")
VALID_CONTROLCENTER_STATES = ("auto", "on", "off")


@dataclass
class ModeConfig:
    active: str = "remember"
    search_after_n_searches: int = 3
    max_hits: int = 3
    min_rank: float = 0.5
    max_injections_per_session: int = 5
    cooldown_seconds: int = 60


@dataclass
class GateConfig:
    enabled: bool = False
    min_relevance: float = 0.5
    min_change: float = 1.0


@dataclass
class OutputConfig:
    max_text_chars: int = 500
    max_source_chars: int = 160
    max_meta_chars: int = 160
    max_meta_entries: int = 32
    max_meta_total_chars: int = 1000
    max_message_chars: int = 2000
    redaction_marker: str = "[redacted]"
    truncation_marker: str = "…[truncated]"


@dataclass
class ClueConfig:
    triggers: list[str] = field(default_factory=list)


@dataclass
class ProvidersConfig:
    order: list[str] = field(
        default_factory=lambda: ["claude", "codex", "kimi", "agy", "git", "manual"]
    )
    claude_events: list[str] = field(
        default_factory=lambda: ["SessionStart", "UserPromptSubmit"]
    )


@dataclass
class ControlCenterConfig:
    """Wird geparst, aber in v0.1 (noch) nicht ausgewertet -- siehe README
    "Was NICHT umgesetzt ist"."""

    enabled: str = "auto"
    suggest_skills: bool = True
    suggest_tools: bool = True


@dataclass
class BackendConfig:
    """Welches Gedaechtnis befragt wird.

    Zwei Schreibweisen, absichtlich beide gueltig:

    ``kind``/``path`` waehlen genau ein Backend -- die kleinste sinnvolle
    Konfiguration und weiterhin der Default.

    ``order`` waehlt eine **Kette** (z. B. ``["gardener", "files"]``). Jedes
    Glied bekommt seine eigenen Optionen aus einer Untertabelle::

        [backend]
        order = ["gardener", "files"]

        [backend.gardener]
        db_path = "~/.gardener/gardener.db"
        user_db_path = "~/.gardener/user.db"

        [backend.files]
        path = "~/.claude/projects/<projekt>/memory"

    Ist ``order`` gesetzt, gewinnt es gegen ``kind``. Nicht verfuegbare
    Glieder werden still uebersprungen -- ein fehlendes Backend ist nie ein
    Fehler (siehe ``MemoryBackend.available()``).
    """

    kind: str = "files"
    path: str | None = None
    order: list[str] = field(default_factory=list)
    options: dict[str, dict] = field(default_factory=dict)

    def chain(self) -> list[str]:
        """Effektive Backend-Reihenfolge -- ``order`` falls gesetzt, sonst ``[kind]``."""
        return [name for name in self.order] if self.order else [self.kind]

    def options_for(self, name: str) -> dict:
        """Optionen eines Kettenglieds; faellt auf ``path`` der Haupttabelle zurueck."""
        opts = dict(self.options.get(name, {}))
        if "path" not in opts and self.path:
            opts["path"] = self.path
        return opts


@dataclass
class Config:
    mode: ModeConfig = field(default_factory=ModeConfig)
    gate: GateConfig = field(default_factory=GateConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    clue: ClueConfig = field(default_factory=ClueConfig)
    providers: ProvidersConfig = field(default_factory=ProvidersConfig)
    controlcenter: ControlCenterConfig = field(default_factory=ControlCenterConfig)
    backend: BackendConfig = field(default_factory=BackendConfig)

    def validate(self) -> None:
        if self.mode.active not in VALID_MODES:
            raise ValueError(
                f"[mode].active muss einer von {VALID_MODES} sein, nicht {self.mode.active!r}"
            )
        if self.backend.kind not in VALID_BACKENDS:
            raise ValueError(
                f"[backend].kind muss einer von {VALID_BACKENDS} sein, nicht {self.backend.kind!r}"
            )
        for name in self.backend.order:
            if name not in VALID_BACKENDS:
                raise ValueError(
                    f"[backend].order darf nur {VALID_BACKENDS} enthalten, nicht {name!r}"
                )
        if self.controlcenter.enabled not in VALID_CONTROLCENTER_STATES:
            raise ValueError(
                f"[controlcenter].enabled muss einer von {VALID_CONTROLCENTER_STATES} sein, "
                f"nicht {self.controlcenter.enabled!r}"
            )
        if not (0.0 <= self.mode.min_rank <= 1.0):
            raise ValueError(f"[mode].min_rank muss in [0,1] liegen, nicht {self.mode.min_rank!r}")
        for name, value in (
            ("min_relevance", self.gate.min_relevance),
            ("min_change", self.gate.min_change),
        ):
            if not (0.0 <= value <= 1.0):
                raise ValueError(f"[gate].{name} muss in [0,1] liegen, nicht {value!r}")
        for name in (
            "max_text_chars",
            "max_source_chars",
            "max_meta_chars",
            "max_meta_entries",
            "max_meta_total_chars",
            "max_message_chars",
        ):
            value = getattr(self.output, name)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"[output].{name} muss eine positive Ganzzahl sein, nicht {value!r}")
        if not self.output.redaction_marker or not self.output.truncation_marker:
            raise ValueError("[output]-Marker duerfen nicht leer sein")


def default_config() -> Config:
    return Config()


def load_config(path: Path | str | None) -> Config:
    """Laedt eine ``memoryhooker.toml``. Fehlt die Datei, gelten die Defaults.

    Ein fehlender Pfad ist ausdruecklich kein Fehler -- das Modul soll ohne
    jede Konfiguration lauffaehig sein (README: "Default ist die
    zurueckhaltendste").
    """
    if path is None:
        return default_config()

    path = Path(path)
    if not path.exists():
        return default_config()

    data = _toml.loads(path.read_text(encoding="utf-8"))
    config = _config_from_dict(data)
    config.validate()
    return config


def _config_from_dict(data: dict) -> Config:
    mode_data = data.get("mode", {})
    mode = ModeConfig(
        active=mode_data.get("active", ModeConfig.active),
        search_after_n_searches=mode_data.get(
            "search_after_n_searches", ModeConfig.search_after_n_searches
        ),
        max_hits=mode_data.get("max_hits", ModeConfig.max_hits),
        min_rank=float(mode_data.get("min_rank", ModeConfig.min_rank)),
        max_injections_per_session=mode_data.get(
            "max_injections_per_session", ModeConfig.max_injections_per_session
        ),
        cooldown_seconds=mode_data.get("cooldown_seconds", ModeConfig.cooldown_seconds),
    )

    gate_data = data.get("gate", {})
    gate = GateConfig(
        enabled=bool(gate_data.get("enabled", GateConfig.enabled)),
        min_relevance=float(gate_data.get("min_relevance", GateConfig.min_relevance)),
        min_change=float(gate_data.get("min_change", GateConfig.min_change)),
    )

    output_data = data.get("output", {})
    output = OutputConfig(
        max_text_chars=output_data.get("max_text_chars", OutputConfig.max_text_chars),
        max_source_chars=output_data.get("max_source_chars", OutputConfig.max_source_chars),
        max_meta_chars=output_data.get("max_meta_chars", OutputConfig.max_meta_chars),
        max_meta_entries=output_data.get("max_meta_entries", OutputConfig.max_meta_entries),
        max_meta_total_chars=output_data.get(
            "max_meta_total_chars", OutputConfig.max_meta_total_chars
        ),
        max_message_chars=output_data.get("max_message_chars", OutputConfig.max_message_chars),
        redaction_marker=output_data.get("redaction_marker", OutputConfig.redaction_marker),
        truncation_marker=output_data.get("truncation_marker", OutputConfig.truncation_marker),
    )

    clue_data = data.get("clue", {})
    clue = ClueConfig(triggers=list(clue_data.get("triggers", [])))

    providers_data = data.get("providers", {})
    claude_data = providers_data.get("claude", {})
    providers = ProvidersConfig(
        order=list(providers_data.get("order", ProvidersConfig().order)),
        claude_events=list(claude_data.get("events", ProvidersConfig().claude_events)),
    )

    cc_data = data.get("controlcenter", {})
    controlcenter = ControlCenterConfig(
        enabled=cc_data.get("enabled", ControlCenterConfig.enabled),
        suggest_skills=bool(cc_data.get("suggest_skills", ControlCenterConfig.suggest_skills)),
        suggest_tools=bool(cc_data.get("suggest_tools", ControlCenterConfig.suggest_tools)),
    )

    backend_data = data.get("backend", {})
    # Untertabellen ([backend.gardener] usw.) sind die Optionen des jeweiligen
    # Kettenglieds; skalare Schluessel bleiben Haupttabelle (kind/path/order).
    backend_options = {
        name: value for name, value in backend_data.items() if isinstance(value, dict)
    }
    backend_order = [str(name) for name in backend_data.get("order", []) if str(name)]
    backend = BackendConfig(
        kind=backend_data.get("kind", BackendConfig.kind),
        path=backend_data.get("path") or None,
        order=backend_order,
        options=backend_options,
    )

    return Config(
        mode=mode,
        gate=gate,
        output=output,
        clue=clue,
        providers=providers,
        controlcenter=controlcenter,
        backend=backend,
    )
