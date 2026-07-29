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
