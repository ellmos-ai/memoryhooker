# Security policy

## Reporting a vulnerability

Do not include secrets, memory contents, local paths, hook payloads, or database
files in a public issue.

Use the private vulnerability-reporting form in the Security tab of the public
release repository. Publication is blocked until that private channel has been
enabled and verified.

Include the affected version, operating system, provider/backend, a minimal
reproduction using synthetic data, and the impact.

## Scope

MemoryHooker reads user-selected local files and may read configured SQLite
databases. The Gardener adapter opens databases read-only. Review generated hook
snippets before installation and restrict filesystem permissions around memory
and state directories. The package makes no network requests.

Backend records are sanitized at the shared hook-output boundary: common secret
assignments/tokens and absolute local paths are redacted before deterministic
size limits are applied. Session state stores counters, timestamps, and -- only
when the opt-in change gate is enabled -- a SHA-256 digest of the sanitized
selection. It never stores prompts or raw hits. Redaction is defense in depth;
synthetic reproductions and review are still required before publishing output.
