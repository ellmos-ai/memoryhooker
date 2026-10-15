"""The MemoryHooker Codex provider must consume the shared Windows fix."""
import sys

from memoryhooker.providers.codex import CodexProvider


def test_codex_memory_hooks_invoke_quoted_python():
    snippet = CodexProvider().hook_snippet(python_executable=f'"{sys.executable}"')
    for groups in snippet["hooks"].values():
        handler = groups[0]["hooks"][0]
        assert handler["commandWindows"] == "& " + handler["command"]
