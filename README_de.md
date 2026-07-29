# MemoryHooker

MemoryHooker verbindet lokale Wissensquellen mit Lebenszyklus-Hooks von
Coding-Agenten. Das Modul kann an eine Suche erinnern, einen kurzen Hinweis
geben oder lokale Quellen durchsuchen und ausgewählte Treffer zurückgeben. Es
nutzt kein Netzwerk und verändert keine Host-Konfiguration.

## Funktionen

- `files`-Backend für ein oder mehrere Markdown-Verzeichnisse.
- Read-only-Backend für kompatible Gardener-SQLite-FTS5-Datenbanken.
- Geordnete Backend-Ketten, die nicht verfügbare Quellen überspringen.
- Modi `remember`, `clue` und `remember+search`.
- Begrenzung und Cooldown je Sitzung.
- Provider für Claude Code, Codex CLI, Kimi Code CLI, Antigravity, Git und
  manuelle Ausführung.

Die Backend-Namen `usmc` und `bach` sind reservierte Adapter. Sie liefern
derzeit keine Treffer und greifen nicht direkt auf Datenbanken zu.

## Installation und Konfiguration

MemoryHooker benötigt Python 3.10 oder neuer.

```shell
python -m pip install .
```

Beispiel für `memoryhooker.toml`:

```toml
[mode]
active = "remember+search"
max_hits = 3
max_injections_per_session = 5
cooldown_seconds = 60

[backend]
order = ["gardener", "files"]

[backend.files]
path = "./memory"
```

`install-snippet` gibt nur einen Konfigurationsbaustein aus. Prüfe und
übernimm ihn manuell.

## Datenschutz und Lizenz

Das Datei-Backend liest nur ausdrücklich konfigurierte Markdown-Wurzeln. Der
Gardener-Adapter öffnet konfigurierte Datenbanken read-only. Treffer und Pfade
können sensibel sein und dürfen nicht ungeprüft veröffentlicht werden.
Sicherheitsmeldungen beschreibt [SECURITY.md](SECURITY.md), die Herkunft
[PROVENANCE.md](PROVENANCE.md). Lizenz: MIT, siehe [LICENSE](LICENSE).
