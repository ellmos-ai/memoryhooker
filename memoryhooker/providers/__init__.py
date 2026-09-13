"""Provider-Adapter -- binden MemoryHooker an unterschiedliche Hook-Systeme.

Siehe README.md, Abschnitt "Provider: verschiedene Hook-Systeme, ein Modul".
``PROVIDER_REGISTRY`` haelt alle bekannten Provider in der Reihenfolge, die
``[providers].order`` in der Config referenziert; ``resolve_provider()``
liefert den ersten verfuegbaren.
"""

from __future__ import annotations

from ..config import ProvidersConfig
from .agy import AgyProvider
from .base import Provider, UnimplementedProvider
from .claude import ClaudeProvider
from .codex import CodexProvider
from .git import GitProvider
from .kimi import KimiProvider
from .manual import ManualProvider

PROVIDER_REGISTRY: dict[str, Provider] = {
    "claude": ClaudeProvider(),
    "codex": CodexProvider(),
    "git": GitProvider(),
    "manual": ManualProvider(),
    "agy": AgyProvider(),
    "kimi": KimiProvider(),
}

__all__ = [
    "PROVIDER_REGISTRY",
    "AgyProvider",
    "ClaudeProvider",
    "CodexProvider",
    "GitProvider",
    "KimiProvider",
    "ManualProvider",
    "Provider",
    "UnimplementedProvider",
    "resolve_provider",
]


def resolve_provider(config: ProvidersConfig) -> Provider:
    """Erster verfuegbarer Provider in ``config.order`` gewinnt (Fallback-Kette).

    ``manual`` ist immer verfuegbar und damit der garantierte Endpunkt der
    Kette -- das Modul kann so nie ganz ohne Provider dastehen.
    """
    for name in config.order:
        provider = PROVIDER_REGISTRY.get(name)
        if provider is not None and provider.is_available():
            return provider
    return PROVIDER_REGISTRY["manual"]
