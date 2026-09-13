# Security Policy

## Supported Versions

| Version | Supported |
|:---|:---|
| `0.3.x` | :white_check_mark: Supported (Current Stable Release) |
| `< 0.3.0` | :x: End of Life (Upgrade Recommended) |

---

## Reporting a Vulnerability

We take the security of local AI workflows and developer memory infrastructure seriously. If you discover a potential vulnerability in `memoryhooker`, please report it responsibly.

> [!IMPORTANT]
> **Do NOT file public GitHub issues for security vulnerabilities.** Do not include secrets, memory contents, internal local paths, hook payloads, or database files in a public issue.

### Private Reporting Channels
1. **GitHub Security Advisories (Recommended):** Submit a confidential advisory report directly via the **Security** tab of the [`ellmos-ai/memoryhooker`](https://github.com/ellmos-ai/memoryhooker/security/advisories) repository.
2. **Security Contact:** Alternatively, contact the security stewards directly at `security@ellmos.ai` or `security@open-bricks.org`.

### Information to Include
- Affected version of `memoryhooker` and Python runtime environment.
- Operating system (Windows, macOS, Linux) and shell environment.
- Provider and memory backend in use (e.g. Claude Code, Codex, USMC, Gardener, Files).
- Minimal synthetic reproduction steps (using synthetic test directories or mock databases—never real user data).
- Potential security impact and classification.

### Response & Triage SLA
- **Initial Response:** Within **48 hours** of receiving the report.
- **Vulnerability Triage & Assessment:** Within **5 business days**.
- **Fix & Disclosure Coordination:** Remediation patches are prepared in private forks and coordinated before public release notes are published.

---

## Security Scope & Threat Model

`memoryhooker` connects local memory sources (Markdown directories, SQLite FTS5 databases) to lifecycle hooks of coding agents. Its threat model enforces strict boundaries:

1. **Zero Network Sockets (Zero-Egress):** The core engine performs no HTTP, WebSocket, gRPC, or TCP/UDP operations. Memory queries and hook injections remain strictly confined to the local machine.
2. **Read-Only External Storage:** The Gardener and USMC adapters open configured SQLite databases strictly in read-only mode (`mode=ro`). MemoryHooker never mutates, locks, or creates schemas in third-party databases.
3. **Unprivileged User Mode (`RunAsInvoker`):** MemoryHooker operates under standard unprivileged user credentials and never requests Administrator or root elevation.
4. **Deterministic Privacy Boundary:** All backend-derived hook outputs cross a mandatory sanitization boundary. Secret tokens, API keys, and absolute local filesystem paths are redacted (`[redacted]`) before per-field and total message bounds are applied.
5. **Session Cap & Rate Limiting:** Per-session injection counters and cooldowns prevent agent loops from flooding context windows. Session state files persist only counters, timestamps, and an optional SHA-256 digest of sanitized selections—never raw prompts or unredacted hits.
