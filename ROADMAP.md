# Roadmap

Future work is tracked against observable acceptance criteria:

- Add contract tests for each supported host version.
- Add a documented, read-only API before enabling the reserved BACH adapter
  (see `tests/test_backends_usmc.py` for the pattern the USMC adapter used:
  a pinned schema snapshot plus a `mode=ro` sqlite3 connection, the same
  contract the Gardener adapter already relies on).
- Add structured diagnostics that redact local paths and memory content.
- Add opt-in ranking diagnostics using synthetic data only.
- Publish signed artifacts after the release repository and reporting channel
  have been verified.

## Follow-ups (2026-07-31)

- Normalize the files-backend ranking (for example `score / max_score` or
  length normalization) so that `min_rank` becomes meaningful again; the
  current `score / (score + 3)` saturation renders everything above ~300
  as 1.00.
- Support individual file paths in the files backend; today only directories
  are scanned recursively and an explicit file list is silently ignored.
- Add an FTS5 backend built on the stdlib `sqlite3` module (unicode61
  tokenizer, bm25 mapped into (0, 1]); the backend protocol already
  anticipates FTS5-bm25 ranking. This addresses stopword inflation, score
  saturation and size bias structurally without new dependencies.
- Add a forgetfulness sidecar to the index (`last_accessed` / `access_count`
  with decay and a review threshold instead of hard deletion).
- Optionally add an embedding-based hybrid backend that reports
  `available() = False` when the optional packages are not installed.

Roadmap items are not promises and may change.
