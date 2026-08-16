from pathlib import Path

import pytest

from memoryhooker.config import ProvidersConfig
from memoryhooker.providers import PROVIDER_REGISTRY, resolve_provider
from memoryhooker.providers.agy import AgyProvider
from memoryhooker.providers.claude import ClaudeProvider
from memoryhooker.providers.codex import CodexProvider
from memoryhooker.providers.git import GitProvider
from memoryhooker.providers.kimi import KimiProvider
from memoryhooker.providers.manual import ManualProvider


def test_claude_provider_never_emits_pretooluse():
    snippet = ClaudeProvider().hook_snippet()
    assert "PreToolUse" not in snippet["hooks"]
    assert set(snippet["hooks"]) == {"SessionStart", "UserPromptSubmit"}


def test_claude_provider_available():
    assert ClaudeProvider().is_available() is True


def test_agy_provider_never_emits_pretooluse():
    snippet = AgyProvider().hook_snippet()
    assert "PreToolUse" not in snippet["hooks"]
    assert set(snippet["hooks"]) == {"PreInvocation", "PostToolUse"}


def test_agy_provider_available():
    assert AgyProvider().is_available() is True


def test_codex_provider_emits_verified_codex_hook_shape():
    provider = CodexProvider()
    assert provider.is_available() is True
    snippet = provider.hook_snippet()
    assert set(snippet["hooks"]) == {"SessionStart", "UserPromptSubmit"}
    assert "PreToolUse" not in snippet["hooks"]
    command = snippet["hooks"]["SessionStart"][0]["hooks"][0]
    assert command["commandWindows"] == command["command"]
    assert command["timeout"] == 10


def test_git_remains_documented_stub():
    assert GitProvider().is_available() is False
    assert GitProvider().reason


def test_manual_provider_always_available():
    assert ManualProvider().is_available() is True


def test_resolve_provider_picks_codex_when_ordered():
    config = ProvidersConfig(order=["codex", "git", "manual"])
    chosen = resolve_provider(config)
    assert chosen.name == "codex"


def test_resolve_provider_picks_claude_first_when_listed():
    config = ProvidersConfig(order=["claude", "codex", "git", "manual"])
    chosen = resolve_provider(config)
    assert chosen.name == "claude"


def test_resolve_provider_picks_agy_when_ordered():
    config = ProvidersConfig(order=["agy", "manual"])
    chosen = resolve_provider(config)
    assert chosen.name == "agy"


def test_provider_registry_has_all_six():
    assert set(PROVIDER_REGISTRY) == {"claude", "codex", "agy", "kimi", "git", "manual"}


def test_kimi_provider_emits_only_userpromptsubmit_in_plain_format():
    """Kimi-Vertrag (Probe 2026-07-28, CLI 0.29.2): nur UserPromptSubmit speist
    stdout als Kontext ein; SessionStart ist ein Beobachtungs-Event und wird
    absichtlich NICHT registriert (stille Falle)."""
    snippet = KimiProvider().hook_snippet()
    events = {h["event"] for h in snippet["hooks"]}
    assert events == {"UserPromptSubmit"}
    assert "PreToolUse" not in events
    assert "SessionStart" not in events
    assert "--format plain" in snippet["hooks"][0]["command"]


def test_kimi_provider_availability_mirrors_config_existence():
    expected = (Path.home() / ".kimi-code" / "config.toml").exists()
    assert KimiProvider().is_available() is expected


def test_resolve_provider_picks_kimi_when_ordered_and_available():
    if not KimiProvider().is_available():
        pytest.skip("keine ~/.kimi-code/config.toml auf diesem Host")
    config = ProvidersConfig(order=["kimi", "manual"])
    assert resolve_provider(config).name == "kimi"
