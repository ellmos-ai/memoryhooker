![MemoryHooker](docs/assets/banner.svg)

# MemoryHooker

[![ellmos-ai](https://img.shields.io/badge/ecosystem-ellmos--ai-blue.svg)](https://github.com/ellmos-ai)
[![open-bricks](https://img.shields.io/badge/umbrella-open--bricks-indigo.svg)](https://github.com/open-bricks)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-156%20passed-brightgreen.svg)](tests/)
[![llms.txt](https://img.shields.io/badge/llms.txt-available-0055ff?logo=markdown)](llms.txt)
[![Language: Deutsch](https://img.shields.io/badge/Language-Deutsch-de.svg)](README_de.md)

> [!NOTE]
> **AI & Agent Indexing:** This repository provides an [`llms.txt`](llms.txt) machine-readable summary for AI agents, LLM tools, and lifecycle hooks.

> **Contributing:** development happens in the private twin `memoryhooker-provenance`; this repository carries the curated result. See [CONTRIBUTING.md](CONTRIBUTING.md).


MemoryHooker connects local memory sources to lifecycle hooks exposed by coding
agents. It can emit a reminder to search memory, add a short clue, or perform a
local search and return selected hits. The package makes no network requests
and does not modify host configuration.

## Features

- `files` backend for one or more Markdown directories.
- Read-only `gardener` backend for compatible SQLite FTS5 databases.
- Read-only `usmc` backend for USMC's curated facts, lessons, and working
  memory (see "USMC backend" below).
- Ordered backend chains that skip unavailable sources.
- `remember`, `clue`, and `remember+search` modes.
- Per-session injection limits and cooldowns.
- Provider adapters for Claude Code, Codex CLI, Kimi Code CLI, Antigravity,
  Git, and manual execution.

The `bach` backend name is a reserved adapter. It currently fails open and
returns no hits; no direct database access is implemented for it.

## Requirements and installation

MemoryHooker requires Python 3.10 or newer.

```shell
python -m pip install .
```

For development:

```shell
python -m pip install -e ".[dev]"
python -m pytest
```

## Configuration

Create `memoryhooker.toml`:

```toml
[mode]
active = "remember+search"
search_after_n_searches = 3
max_hits = 3
min_rank = 0.5
max_injections_per_session = 5
cooldown_seconds = 60

[backend]
order = ["usmc", "gardener", "files"]

[backend.usmc]
db_path = "~/.usmc/usmc_memory.db"

[backend.gardener]
db_path = "~/.gardener/gardener.db"
user_db_path = "~/.gardener/user.db"

[backend.files]
path = "./memory"

[providers]
order = ["claude", "codex", "kimi", "agy", "git", "manual"]
```

The default mode is `remember`. A missing backend is not an error; the hook
stays silent when no configured source is available.

### USMC backend

The `usmc` backend reads [USMC](https://pypi.org/project/usmc/)'s three
curated tables directly and read-only: `usmc_facts`, `usmc_lessons`, and
`usmc_working` (facts, lessons learned, and working-memory notes). It never
imports or instantiates the `usmc` package -- `USMCClient.__init__` creates
the database and its schema when the path does not yet exist, which is a
write path this project's "read-only, never write" boundary rules out. The
adapter opens the configured `db_path` (default `~/.usmc/usmc_memory.db`)
with SQLite's `mode=ro` instead, the same contract the `gardener` backend
already uses.

`available()` requires all three tables to exist; a file that happens to
exist but carries no USMC schema is treated the same as a missing file, not
as an empty match. Ranking combines how many distinct query terms a row
contains with USMC's own curation signal -- lesson severity, fact
confidence, or working-memory priority -- so a `critical` lesson outranks an
equally-matched `low` one, and curated facts/lessons outrank working-memory
notes at the same match strength.

## Command line

```shell
python -m memoryhooker --config memoryhooker.toml check "deployment checklist"
python -m memoryhooker providers
python -m memoryhooker install-snippet --provider codex
python -m memoryhooker install-snippet --provider kimi
python -m memoryhooker --config memoryhooker.toml diagnose "deployment checklist"
python -m memoryhooker clear
```

`install-snippet` prints a configuration fragment. It never writes to the
host's settings. Review and merge the fragment manually.

`diagnose` evaluates the same three gates as `check`/`hook-run` -- config
source, session cap/cooldown, and per-backend availability/hit-count/top-rank
-- but reports each one individually instead of collapsing them into a
silent yes/no. It never writes to the state file and never counts against
`max_injections_per_session`; it is a read-only probe.

`clear` deletes the state file targeted by `--session-id`/`--state-dir`
(the shared `session-default.json` by default). Use it when a session's
`injections_count` is stuck at `max_injections_per_session` -- most commonly
after repeated manual `check`/`hook-run` calls made without `--session-id`
while debugging, since those all share the same default state file. The
state file also resets on its own once its stored calendar day is stale, so
`clear` is for an immediate reset; the automatic TTL is the long-running
safety net.

### Troubleshooting: a silent hook

`check`/`hook-run` intentionally give no output when they have nothing to
say -- a hook must never look like an error. That makes two mistakes look
identical to "no hit" from the outside:

- `--config`, `--session-id`, and `--state-dir` are **top-level** arguments.
  They must precede the subcommand: `memoryhooker --config x.toml check
  "..."`, not `memoryhooker check --config x.toml "..."` (argparse
  subparser scoping).
- A missing or non-existent `--config` file is not an error either -- it
  silently loads library defaults (a `files` backend with no configured
  roots), which never reaches a configured Gardener/USMC/BACH backend.

Run `diagnose` with the same prompt and flags to see which of these it is.

## Data and security boundaries

The file backend reads Markdown below explicitly configured roots. The
Gardener and USMC adapters open configured databases with SQLite read-only
mode and never bundle database contents. Search hits and paths can be
sensitive, so do not publish hook output or state files without review.

See [SECURITY.md](SECURITY.md) for private vulnerability reporting and
[PROVENANCE.md](PROVENANCE.md) for source-history and BACH lineage notes.

## License

MIT. See [LICENSE](LICENSE).
