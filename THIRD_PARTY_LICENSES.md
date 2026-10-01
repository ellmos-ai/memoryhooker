# Third-Party Licenses & Transparency Notice

> **Project:** `ellmos-ai/memoryhooker`<br/>
> **Audited:** 2026-10-01<br/>
> **Repository License:** [MIT License](LICENSE)<br/>
> **Canonical Attribution:** [NOTICE](NOTICE)<br/>
> **Plain-Text Companion:** [THIRD_PARTY_LICENSES.txt](THIRD_PARTY_LICENSES.txt)<br/>
> **Architecture & Privacy:** 100% Local-First, Zero-Egress Core, Read-Only External Storage, Unprivileged User-Mode (`RunAsInvoker`)

---

## Executive Summary & Compliance Assurance

`memoryhooker` is architected with a strict standard: **the core memory retrieval, lifecycle hook integration, ranking, gate evaluation, and privacy sanitization engine operates locally without external data exfiltration**. The runtime relies on lightweight, standard-compliant components. External memory sources (such as USMC or Gardener SQLite databases) are accessed exclusively via standard-library SQLite connectors in strict read-only mode (`mode=ro`) without importing heavy external packages or initializing network sockets.

All direct and development dependencies used or referenced in `memoryhooker` are licensed under strictly **permissive open-source licenses** (MIT, Apache 2.0, PSFL). There are **zero copyleft or AGPL-style viral dependencies**, ensuring full compatibility for corporate enterprise environments, autonomous agent loops, compliance pipelines, and proprietary integrations.

Furthermore, `memoryhooker` enforces an uncompromising **Zero-Egress & Data Privacy Boundary**:
1. The engine initializes no HTTP, WebSocket, gRPC, or TCP/UDP network sockets; memory queries and hook injections remain 100% local to the host machine.
2. External databases are opened strictly in read-only mode (`mode=ro`), guaranteeing that memory retrieval never mutates or writes to host databases.
3. Hook output crosses a deterministic sanitization boundary that redacts sensitive auth tokens, API keys, and absolute local filesystem paths before output bounds are enforced.
4. Execution runs strictly in unprivileged user mode (`RunAsInvoker`), never requesting root or Administrator privileges.

---

## Runtime Dependency Matrix

| Package / Tool | Role / Functional Scope | License | Project Repository / Source |
|:---|:---|:---|:---|
| **hook-master** | Host-agnostic lifecycle hook provider contracts, base classes, and hook invariants | [MIT](https://github.com/ellmos-ai/hook-master/blob/main/LICENSE) | [ellmos-ai/hook-master](https://github.com/ellmos-ai/hook-master) |
| **Python Standard Library** | Core engine, SQLite FTS5 querying (`sqlite3`), token sanitization (`re`), cryptographic digests (`hashlib`), file traversal (`pathlib`), JSON state persistence (`json`), CLI parsing (`argparse`), typing & dataclasses | [PSFL-2.0](https://docs.python.org/3/license.html) | [python/cpython](https://github.com/python/cpython) |

---

## Development & Quality Assurance Tooling

| Package | Usage & Purpose | License | Source / Upstream |
|:---|:---|:---|:---|
| **pytest** | Automated test runner, contract validation suites, fixture isolation | [MIT](https://github.com/pytest-dev/pytest/blob/main/LICENSE) | [pytest-dev/pytest](https://github.com/pytest-dev/pytest) |
| **ruff** | High-performance Python linter and code style enforcement | [MIT / Apache-2.0](https://github.com/astral-sh/ruff/blob/main/LICENSE-MIT) | [astral-sh/ruff](https://github.com/astral-sh/ruff) |
| **setuptools** | Package build backend (PEP 517 / PEP 621 compliant packaging) | [MIT](https://github.com/pypa/setuptools/blob/main/LICENSE) | [pypa/setuptools](https://github.com/pypa/setuptools) |

---

## Level 1 SBOM Invariant Compliance Status

| Invariant ID | Requirement / Scope | Status | Verification & Evidence |
|:---|:---|:---|:---|
| **INV-LOCAL-01** | 100% Local-First & Zero Egress; no external sockets or network egress | **PASS** | Core uses local SQLite & file backends; zero socket connections |
| **INV-READONLY-02** | External databases opened strictly in read-only mode (`mode=ro`) | **PASS** | Verified in USMC & Gardener backends; immutable query operations |
| **INV-UNPRIV-03** | Execution runs strictly in unprivileged user mode (`RunAsInvoker`) | **PASS** | No elevation, service installation or root privileges required |
| **INV-REDACT-04** | Deterministic privacy boundary redacting secret tokens and local paths | **PASS** | Regex masking of bearer tokens, API keys, passwords, and absolute paths |
| **INV-BOUND-05** | Deterministic output length, hit count, and whole-message bounds | **PASS** | Strict character and hit capping enforced before hook output emission |
| **INV-GATE-06** | Opt-in SHA-256 Change Gate persisting only hashes, never raw prompts | **PASS** | Change gate digests selections without persisting sensitive prompt content |
| **INV-SPAM-07** | Session injection caps, cooldown, and calendar-day TTL protection | **PASS** | `max_injections_per_session`, cooldown timer, and daily TTL reset |
| **INV-FAILOPEN-08** | Resilient fail-open behavior; hooks never crash calling harness | **PASS** | All exceptions trapped and logged gracefully; silent exit on errors |
| **INV-LLM-09** | Machine-readable `llms.txt` index for AI agent and tool integration | **PASS** | `llms.txt` maintained at repository root with structural metadata |
| **INV-SLA-10** | Binding Dual Security Response SLA: 48h Response, 5d Triage | **PASS** | Documented in `SECURITY.md` and monitored continuously |

---

## Full License Texts (Excerpts & Notices)

### 1. Python Software Foundation License Version 2 (PSFL-2.0)
Python standard library modules (e.g. `sqlite3`, `pathlib`, `json`, `re`, `hashlib`, `argparse`, `sys`, `time`, `dataclasses`) are used under the PSF License Agreement.
Copyright (c) 2001-2026 Python Software Foundation. All rights reserved.

### 2. MIT License (MIT)
Used by `memoryhooker`, `hook-master`, `pytest`, `ruff` (dual-licensed), and `setuptools`.
> Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:  
> The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

### 3. Apache License, Version 2.0 (Apache-2.0)
Used by `ruff` (dual-licensed).
> Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at `http://www.apache.org/licenses/LICENSE-2.0`.
