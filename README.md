![MemoryHooker](docs/assets/banner.svg)

# MemoryHooker

> **Contributing:** development happens in the private twin `memoryhooker-provenance`; this repository carries the curated result. See [CONTRIBUTING.md](CONTRIBUTING.md).


MemoryHooker connects local memory sources to lifecycle hooks exposed by coding
agents. It can emit a reminder to search memory, add a short clue, or perform a
local search and return selected hits. The package makes no network requests
and does not modify host configuration.

## Features

- `files` backend for one or more Markdown directories.
- Read-only `gardener` backend for compatible SQLite FTS5 databases.
- Ordered backend chains that skip unavailable sources.
- `remember`, `clue`, and `remember+search` modes.
- Per-session injection limits and cooldowns.
- Provider adapters for Claude Code, Codex CLI, Kimi Code CLI, Antigravity,
  Git, and manual execution.

The `usmc` and `bach` backend names are reserved adapters. They currently fail
open and return no hits; no direct database access is implemented for them.

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
order = ["gardener", "files"]

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

## Command line

```shell
python -m memoryhooker --config memoryhooker.toml check "deployment checklist"
python -m memoryhooker providers
python -m memoryhooker install-snippet --provider codex
python -m memoryhooker install-snippet --provider kimi
```

`install-snippet` prints a configuration fragment. It never writes to the
host's settings. Review and merge the fragment manually.

## Data and security boundaries

The file backend reads Markdown below explicitly configured roots. The
Gardener adapter opens configured databases with SQLite read-only mode and
never bundles database contents. Search hits and paths can be sensitive, so do
not publish hook output or state files without review.

See [SECURITY.md](SECURITY.md) for private vulnerability reporting and
[PROVENANCE.md](PROVENANCE.md) for source-history and BACH lineage notes.

## License

MIT. See [LICENSE](LICENSE).
