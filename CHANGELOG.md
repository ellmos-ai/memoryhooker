# Changelog

All notable public changes are documented in this file.

## Unreleased

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
