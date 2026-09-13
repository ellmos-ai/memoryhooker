# Third-Party Licenses & Transparency Notice

> **Project:** `ellmos-ai/memoryhooker`<br/>
> **Audited:** 2026-09-14<br/>
> **Repository License:** [MIT License](LICENSE)<br/>
> **Architecture & Privacy:** 100% Local-First, Zero-Egress Core, Read-Only External Storage, Unprivileged User-Mode (`RunAsInvoker`)

---

## Executive Summary & Compliance Assurance

`memoryhooker` is architected with a strict standard: **the core memory retrieval, lifecycle hook integration, ranking, gate evaluation, and privacy sanitization engine has zero mandatory external runtime dependencies**. The runtime is built entirely on the Python Standard Library. External memory sources (such as USMC or Gardener SQLite databases) are accessed exclusively via standard-library SQLite connectors in strict read-only mode (`mode=ro`) without importing heavy external packages or initializing network sockets.

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
| **Python Standard Library** | Core engine, SQLite FTS5 querying (`sqlite3`), token sanitization (`re`), cryptographic digests (`hashlib`), file traversal (`pathlib`), JSON state persistence (`json`), CLI parsing (`argparse`), typing & dataclasses | [PSFL-2.0](https://docs.python.org/3/license.html) | [python/cpython](https://github.com/python/cpython) |

---

## Development & Quality Assurance Tooling

| Package | Usage & Purpose | License | Source / Upstream |
|:---|:---|:---|:---|
| **pytest** | Automated test runner, contract validation suites, fixture isolation | [MIT](https://github.com/pytest-dev/pytest/blob/main/LICENSE) | [pytest-dev/pytest](https://github.com/pytest-dev/pytest) |
| **ruff** | High-performance Python linter and code style enforcement | [MIT / Apache-2.0](https://github.com/astral-sh/ruff/blob/main/LICENSE-MIT) | [astral-sh/ruff](https://github.com/astral-sh/ruff) |
| **setuptools** | Package build backend (PEP 517 / PEP 621 compliant packaging) | [MIT](https://github.com/pypa/setuptools/blob/main/LICENSE) | [pypa/setuptools](https://github.com/pypa/setuptools) |

---

## Full License Texts (Excerpts & Notices)

### 1. Python Software Foundation License Version 2 (PSFL-2.0)
Python standard library modules (e.g. `sqlite3`, `pathlib`, `json`, `re`, `hashlib`, `argparse`, `sys`, `time`, `dataclasses`) are used under the PSF License Agreement.
Copyright (c) 2001-2026 Python Software Foundation. All rights reserved.

### 2. MIT License (MIT)
Used by `memoryhooker`, `pytest`, `ruff` (dual-licensed), and `setuptools`.
> Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:  
> The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

### 3. Apache License, Version 2.0 (Apache-2.0)
Used by `ruff` (dual-licensed).
> Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at `http://www.apache.org/licenses/LICENSE-2.0`.
