# Changelog

All notable public changes are documented in this file.

## [Unreleased]

### Discoverability, Visual Architecture, ASCII 4-View Topology & Level 1 SBOM Re-Audit (Pfad B Stand 2026-10-01)

- **Version-Freeze Disziplin (T-20260920-167562623)**: Maintained version `0.3.3` in `pyproject.toml`, `ellmos-module.v2.json`, and source code strictly frozen; 0 version diffs.
- **ASCII Four-View Architectural Topology Projection**: Integrated Four-View architectural topology projection in Section 02 of `README.md` and `README_de.md` (`VIEW 1: CALLER RUNTIMES, LIFECYCLE HOOKS & AGENT CLIENTS`, `VIEW 2: MEMORYHOOKER SOVEREIGN CORE ENGINE & PIPELINE ORCHESTRATOR`, `VIEW 3: RUNTIME PERSISTENCE, SHARED MEMORY SCHEMAS & AUDIT LEDGER`, `VIEW 4: AIR-GAP DEFENSE PERIMETER, RUNASINVOKER & ZERO-EGRESS GOVERNANCE`; German `SICHT 1`..`SICHT 4`).
- **18-Point Bilingual Navigation Parity**: Upgraded quick navigation in `README.md` and `README_de.md` from 16 to 18 points with reciprocal dual HTML anchors (`<a id="sec-01"></a>` through `<a id="sec-18"></a>`) and exact slug synchronization.
- **Target Personas & SEO Discovery**: Highlighted target personas (`[PERSONA-01]` through `[PERSONA-04]`) and high-intent search queries across both languages.
- **10-Dimensional Comparative Matrix**: Refined comparative differentiation matrix against 4 alternatives mapped across runtime invariants `INV-LOCAL-01` through `INV-SLA-10`.
- **Level 1 SBOM Re-Audit & Plain-Text Companion**: Re-audited `THIRD_PARTY_LICENSES.md` and `THIRD_PARTY_LICENSES.txt` Stand 2026-10-01 certifying 100% permissive runtime (`hook-master` MIT, Python stdlib PSF-2.0), zero copyleft, unprivileged `RunAsInvoker` execution, and 10/10 invariant compliance (`INV-LOCAL-01`..`INV-SLA-10` all PASS).
- **Statutory Legal Notice & Security SLA**: Formalized statutory disclaimer under German law (§ 521 BGB Gefälligkeitsrecht) and 48-hour security response SLA in Section 18 of both READMEs.
- **Remote Discoverability Saturation**: Saturated 20/20 GitHub repository topics via `gh repo edit` and configured canonical repository homepage URL (`https://github.com/ellmos-ai/memoryhooker#readme`). Aligned PEP 621 homepage URL in `pyproject.toml`.
- **Context Index & Shields.io Badges**: Updated `llms.txt` with Stand 2026-10-01 and 213 verified tests baseline. Synchronized verification badges (`Verified: 2026-10-01`, `213 passed | 100% green`).
- **Automated Contract Tests**: Expanded `tests/test_metadata.py` with 18-point dual anchor parity, ASCII 4-view topology projection, § 521 BGB disclaimer, and audit recency contract tests.

### Repository Hygiene, CI Lifecycle Workflows & Level 1 SBOM Text Companion (Pfad A)

- **Version-Freeze Disziplin (T-20260920-167562623)**: Maintained version `0.3.3` in `pyproject.toml`, `ellmos-module.v2.json`, and source code unchanged.
- **CI/CD Lifecycle Workflows**:
  - Provisioned `.github/workflows/auto-assign.yml` with `actions/github-script@v7`, `timeout-minutes: 5`, concurrency `cancel-in-progress: true`, and least-privilege permissions (`issues: write`, `pull-requests: write`).
  - Provisioned `.github/workflows/label-sync.yml` with `EndBug/label-sync@v2`, `timeout-minutes: 5`, concurrency `cancel-in-progress: true`, and permissions `issues: write`.
  - Provisioned `.github/labels.yml` with 11 standard labels per GOVERNANCE.md §4.2.
  - Provisioned `.github/workflows/stale.yml` with daily cron `30 1 * * *`, `timeout-minutes: 10`, concurrency `cancel-in-progress: true`, and least-privilege permissions.
  - Provisioned `.github/workflows/welcome.yml` with `actions/first-interaction@v3`, `timeout-minutes: 5`, and concurrency `cancel-in-progress: true`.
- **Multi-Host Cloud-Sync & Lock Defense**: Hardened `.gitignore` against cloud synchronization conflict copies (`*-ASUS*`, `*-IDEAPAD*`, `*_WORKSTATION*`, `*-WORKSTATION-LG.*`), canonical locks (`LOCK`, `LOCK.*`, `LOCK.user.*`, `LOCK.until.*`, `LOCK.condition.*`), test/coverage caches (`.pytest_temp/`, `.pytest_tmp*/`, `.tox/`), and OS artifacts (`Desktop.ini`, `desktop.ini`, `ehthumbs.db`).
- **Canonical Open-Source NOTICE**: Created `NOTICE` attribution file in repository root cross-referencing `THIRD_PARTY_LICENSES.md` and `THIRD_PARTY_LICENSES.txt`.
- **Level 1 SBOM Plain-Text Companion**: Created `THIRD_PARTY_LICENSES.txt` companion file with direct runtime dependency inventory (`hook-master`, Python stdlib) and Invariant Cross-Reference Matrix table certifying all 10 governance and runtime invariants (`INV-LOCAL-01` through `INV-SLA-10`).
- **Level 1 SBOM Re-Audit**: Re-audited `THIRD_PARTY_LICENSES.md` Stand 2026-09-29 incorporating `hook-master`, Level 1 SBOM Invariant Compliance Status table, and links to `NOTICE` and `THIRD_PARTY_LICENSES.txt`.
- **PEP 621 Standardisation**:
  - Expanded `license-files` in `pyproject.toml` to `["LICENSE", "NOTICE", "THIRD_PARTY_LICENSES.md", "THIRD_PARTY_LICENSES.txt"]`.
  - Saturated `keywords` with 20 relevant topics for GitHub discoverability.
  - Registered project URLs for `Notice`, `Third-Party Licenses (Text)`, `Plain-Text Licenses`, and `Level 1 SBOM`.
  - Hardened `[tool.pytest.ini_options]` with `minversion = "7.0"`, `addopts = "-ra -v --basetemp=.pytest_temp"`, and `norecursedirs`.
- **Documentation & Context Parity**: Updated test count (`210+ passed | 100% green`), verification badges (`Verified: 2026-09-29`), Attribution and Level 1 SBOM Plain-Text badges across `README.md` and `README_de.md`, synchronized `llms.txt`, and registered Pfad A review in `MARKETING-LOG.txt`.
- **Automated Contract Tests**: Expanded `tests/test_metadata.py` with contract tests verifying workflows, labels, canonical NOTICE, plain-text SBOM, PEP 621 license files/pytest options, .gitignore multi-host patterns, and changelog/marketing-log recency.

## [0.3.3] - 2026-09-14

### Discoverability & Marketing Architecture (Pfad B)

- **Bilingual Documentation Parity**: Synchronized English (`README.md`) and German (`README_de.md`) documentation with full 16-point navigation anchor parity.
- **Target Personas & SEO Discovery**: Added detailed persona breakdowns (Coding Agent Engineers, Local-First Privacy Advocates, Multi-Agent Swarm Orchestrators, Compliance Officers) with high-intent search keywords.
- **5-Way Comparative Matrix**: Structured comparative analysis across 10 dimensions vs. ad-hoc scripts, cloud vector DB RAG, raw chat history buffers, and heavy agent memory frameworks (MemGPT/Letta).
- **System Architecture & Lifecycle Visuals**: Designed Mermaid flowchart and sequence diagrams for end-to-end task flows and security gates.
- **10 Governance & Runtime Invariants**: Formalized invariants `INV-LOCAL-01` through `INV-SLA-10` covering zero-egress, read-only storage, unprivileged execution, redaction, and SLAs.
- **Third-Party License Audit**: Created [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md) verifying 100% permissive dependencies (PSFL-2.0, MIT, Apache-2.0) with zero copyleft.
- **PEP 621 Metadata URLs**: Expanded URLs in `pyproject.toml` to include Third-Party Licenses, Marketing Log, and LLM Ready links.
- **Extended Contract Test Suite**: Added automated tests in `tests/test_metadata.py` validating navigation anchor parity, personas, matrices, invariants, and package manifests.
- **Visual Assets**: Generated raster asset `docs/assets/banner.png` from vector `docs/assets/banner.svg`.

### Added

- Optional `[gate]` relevance/change thresholds with a backwards-compatible
  disabled default. The gate uses deterministic sanitized hit selection and
  persists only a SHA-256 selection digest; source status/version metadata is
  passed through without truth resolution.
- Normalized `FilesBackend` ranking combining term coverage (60%) and bounded
  term frequency saturation (40%) in `(0, 1]`, with support for individual file paths
  alongside directories and multi-root deduplication.
- A shared synthetic contract matrix for contradicted/stale metadata, missing
  anchors, budget/cooldown ordering, repeated selections, deterministic ties,
  malformed hits, redaction, and output bounds.
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

- Backend-derived hook output now crosses one deterministic privacy/size
  boundary before interpolation or persistence. Common secret assignments,
  tokens, and absolute local paths are redacted before per-field and whole
  message bounds are applied; malformed records fail silent instead of
  crashing the hook.
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
