![MemoryHooker](docs/assets/banner.svg)

# MemoryHooker

[![ellmos-ai](https://img.shields.io/badge/ecosystem-ellmos--ai-blue.svg)](https://github.com/ellmos-ai)
[![open-bricks](https://img.shields.io/badge/umbrella-open--bricks-indigo.svg)](https://github.com/open-bricks)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-177%20bestanden-brightgreen.svg)](tests/)
[![llms.txt](https://img.shields.io/badge/llms.txt-verf%C3%BCgbar-0055ff?logo=markdown)](llms.txt)
[![Language: English](https://img.shields.io/badge/Language-English-gb.svg)](README.md)

> [!NOTE]
> **KI- & Agenten-Indexierung:** Dieses Repository bietet eine maschinenlesbare [`llms.txt`](llms.txt)-Zusammenfassung für KI-Agenten, LLM-Werkzeuge und Lifecycle-Hooks.

MemoryHooker verbindet lokale Wissensquellen mit Lebenszyklus-Hooks von
Coding-Agenten. Das Modul kann an eine Suche erinnern, einen kurzen Hinweis
geben oder lokale Quellen durchsuchen und ausgewählte Treffer zurückgeben. Es
nutzt kein Netzwerk und verändert keine Host-Konfiguration.

## Funktionen

- `files`-Backend für ein oder mehrere Markdown-Verzeichnisse.
- Read-only-Backend für kompatible Gardener-SQLite-FTS5-Datenbanken.
- Read-only-`usmc`-Backend für USMCs kuratierte Fakten, Lessons und Working
  Memory (siehe Abschnitt "USMC-Backend" unten).
- Geordnete Backend-Ketten, die nicht verfügbare Quellen überspringen.
- Modi `remember`, `clue` und `remember+search`.
- Begrenzung und Cooldown je Sitzung, mit taeglicher TTL und manuellem
  `clear`-Kommando zum Zuruecksetzen.
- `diagnose "<prompt>"`: meldet Config-Quelle, Session-Cap/Cooldown und
  Backend-Verfuegbarkeit/Treffer einzeln -- ohne State zu veraendern. Details
  und bekannte Stolpersteine (`--config` vor dem Subcommand, fehlendes
  `--config`) siehe [README.md](README.md), Abschnitt "Command line".
- Provider für Claude Code, Codex CLI, Kimi Code CLI, Antigravity, Git und
  manuelle Ausführung.

Der Backend-Name `bach` ist ein reservierter Adapter. Er liefert derzeit
keine Treffer und greift nicht direkt auf Datenbanken zu.

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

[gate]
# Explizites Opt-in; false bewahrt das bisherige Verhalten.
enabled = false
min_relevance = 0.5
# 1.0 lässt eine identische bereinigte Auswahl stumm.
min_change = 1.0

[output]
max_text_chars = 500
max_source_chars = 160
max_meta_chars = 160
max_meta_entries = 32
max_meta_total_chars = 1000
max_message_chars = 2000
redaction_marker = "[redacted]"
truncation_marker = "…[truncated]"

[backend]
order = ["usmc", "gardener", "files"]

[backend.usmc]
db_path = "~/.usmc/usmc_memory.db"

[backend.files]
path = "./memory"
```

`install-snippet` gibt nur einen Konfigurationsbaustein aus. Prüfe und
übernimm ihn manuell.

Das optionale Gate ist standardmäßig deaktiviert. Ist es aktiviert, werden
Session-Cap und Cooldown vor der Suche geprüft. Danach werden Treffer
bereinigt und total deterministisch sortiert. `min_relevance` ist die
inklusive Rangschwelle. `min_change` vergleicht einen binären Änderungswert:
`1.0` für eine gegenüber der letzten Ausgabe geänderte bereinigte Auswahl,
`0.0` für dieselbe Auswahl. Persistiert wird nur deren SHA-256-Digest, niemals
Prompt oder Rohtreffer. Status- und Versionsmetadaten fließen unverändert in
den Digest ein, werden aber nicht als Wahrheit interpretiert.

### USMC-Backend

Das `usmc`-Backend liest [USMCs](https://pypi.org/project/usmc/) drei
kuratierte Tabellen direkt und read-only: `usmc_facts`, `usmc_lessons` und
`usmc_working` (Fakten, Lessons Learned und Working-Memory-Notizen). Es
importiert oder instanziiert das `usmc`-Paket dabei nie -- `USMCClient.__init__`
legt DB und Schema an, wenn der Pfad noch nicht existiert, und das ist ein
Schreibpfad, den die Regel "nur lesen, niemals schreiben" dieses Projekts
ausschliesst. Der Adapter oeffnet den konfigurierten `db_path` (Default
`~/.usmc/usmc_memory.db`) stattdessen mit SQLites `mode=ro` -- demselben
Vertrag, den das `gardener`-Backend bereits nutzt.

`available()` verlangt alle drei Tabellen; eine Datei, die zwar existiert
aber kein USMC-Schema traegt, gilt wie eine fehlende Datei -- nicht wie ein
leeres Suchergebnis. Der Rang kombiniert, wie viele unterschiedliche
Suchterme in einer Zeile vorkommen, mit USMCs eigenem Kuratierungssignal
(Lesson-Severity, Fakten-Konfidenz, Working-Memory-Prioritaet): eine
`critical`-Lesson schlaegt bei gleicher Treffguete eine `low`-Lesson, und
kuratierte Fakten/Lessons schlagen Working-Memory-Notizen.

## Datenschutz und Lizenz

Das Datei-Backend liest nur ausdrücklich konfigurierte Markdown-Wurzeln. Die
Gardener- und USMC-Adapter öffnen konfigurierte Datenbanken read-only.
Treffer und Pfade können sensibel sein und dürfen nicht ungeprüft
veröffentlicht werden. Vor der Hook-Ausgabe redigiert MemoryHooker gängige
Secret-Zuweisungen, Token und absolute lokale Pfade deterministisch und
begrenzt anschließend Text, Quelle, Metadaten und Gesamtnachricht. Rohtreffer
bleiben ausschließlich im Backend-Prozess und werden nie im Session-State
gespeichert.
Sicherheitsmeldungen beschreibt [SECURITY.md](SECURITY.md), die Herkunft
[PROVENANCE.md](PROVENANCE.md). Lizenz: MIT, siehe [LICENSE](LICENSE).
