# Changelog

All notable public changes are documented in this file.

## Unreleased

### Added

- `diagnose` command: reports each of the three gates (config source, session
  cap/cooldown, per-backend availability/hit-count/top-rank) individually for
  a given prompt, without writing to any hook output and without mutating
  session state or counting against the injection budget. Closes Befund 2 of
  Ticket T-20260816-132994550: `check`/`hook-run` collapse the three gates
  into an opaque yes/no by design (a hook with nothing to say must never look
  like an error), which is correct for the hook path but made a missing
  `--config` indistinguishable from "no hit" during debugging.
- `clear` command: deletes the state file targeted by `--session-id`/
  `--state-dir` (the shared `session-default.json` by default), giving
  operators an explicit reset for a session cap that got stuck.

### Fixed

- `SessionState` now carries a `state_date` (calendar day) and resets on
  `load()` when that day has passed or is missing entirely. Without this, a
  state file with no session id in the hook payload -- most commonly manual
  `check`/`hook-run` calls made while debugging -- accumulated forever;
  `~/.memoryhooker/session-default.json` was found stuck at
  `injections_count == max_injections_per_session` (Befund 1 of Ticket
  T-20260816-132994550). A file predating this field (no `state_date` key)
  resets on the very next `load()`, healing the exact stuck file the ticket
  describes.

### Documentation

- Documented two debugging stumbling blocks from the acceptance round behind
  Ticket T-20260816-132994550 in the CLI module docstring and README.md:
  `--config`/`--session-id`/`--state-dir` are top-level argparse arguments
  and must precede the subcommand; a missing `--config` silently loads
  library defaults (`files` backend without roots) and never reaches a
  configured Gardener/USMC/BACH backend.

## 0.3.1 - 2026-08-16

### Maintenance & Technical Hygiene (Pfad A)

- Standardized linting configuration: added `[tool.ruff]` and `[tool.ruff.lint]` configuration in `pyproject.toml` (`target-version = "py310"`, `line-length = 120`, `E402`/`E501` ignore).
- Fixed unused import `default_state_dir` in `memoryhooker/cli.py`.
- Reorganized module imports in `tests/test_providers.py`.
- Added automated metadata & manifest contract test suite in `tests/test_metadata.py` (verifying version parity across `pyproject.toml`, `ellmos-module.v2.json`, and `__version__`, required fields, and module exports).
- Synchronized documentation badges (139/139 passed).

## 0.3.0

### Added

- Added a read-only `usmc` backend that queries USMC's curated tables
  directly -- `usmc_facts`, `usmc_lessons`, and `usmc_working` -- instead of
  a generic full-text index over raw material. Ranking combines matched-term
  count with USMC's own curation signal (lesson severity, fact confidence,
  working-memory priority). The adapter never imports the `usmc` package: its
  client constructor creates the database and schema on first use, a write
  path this project's read-only boundary rules out, so the adapter opens the
  configured path with SQLite `mode=ro` instead, mirroring the `gardener`
  adapter's contract. Closes T-20260816-972236043 ("USMC-Lessons erreichen
  keine Sitzung") for the `usmc` link of the chain; the live default
  `~/.memoryhooker.toml` now lists `order = ["usmc", "gardener", "files"]`.

### Documentation & Discoverability

- Added ecosystem (`ellmos-ai`) and umbrella (`open-bricks`) Shields.io badges to `README.md` and `README_de.md`.
- Added GFM Callout boxes and explicit `llms.txt` navigation links for AI agent indexing.
- Synchronized header banner and language toggles across English and German documentation.
- Updated `llms.txt` verification timestamp to 2026-08-03.

### Fixed

- Search now targets curated memory instead of raw material. The query ran
  over the whole `everything` table with no type or tag filter, so on this
  machine 14,251 `observed` entries competed with the actual memory for three
  injection slots -- and 83% of them were conversation transcripts, i.e.
  truncated fragments of old sessions. Gardener itself draws that line
  (`recall()` reads only memory/lesson/session); a backend going straight to
  the database has to draw it too. The filter deliberately does not exclude
  `observed` as a whole -- skills, rule files and other tools' lesson tables
  live there and are worth surfacing. Both filters are configurable.
- Duplicate hits no longer take several slots each. The same hint used to
  appear repeatedly: one file indexed through two observe sources, `SKILL.md`
  next to `SKILL.fr.md`, or the same skill filed under two categories.
  De-duplication now compares both the text and a language-neutral source key.

Measured across four typical prompts, three hits each: before, nine of nine
hits came from raw material including transcript fragments and two duplicates;
after, twelve distinct and topically relevant hits.

## 0.2.1

- Added file and read-only Gardener backends with ordered fallback chains.
- Added `remember`, `clue`, and `remember+search` modes.
- Added provider adapters for Claude Code, Codex CLI, Kimi Code CLI,
  Antigravity, Git, and manual execution.
- Added safe session-ID extraction and content-block prompt extraction.
- Added per-session injection limits and cooldowns.
- Kept host-configuration installation as an explicit manual step.
