from __future__ import annotations

try:
    from hook_master.providers.git import GitProvider as BaseGitProvider
except ImportError:
    from .base import UnimplementedProvider as BaseGitProvider


class GitProvider(BaseGitProvider):
    """Universeller Git-Hook-Fallback (``pre-commit``, ``post-checkout``, ...).

    Laut README der "kleinste gemeinsame Nenner aller Agenten" -- fuer das
    Stufe-1-MVP aber bewusst noch nicht verdrahtet (Auftrag: "Codex/git als
    dokumentierte Stubs"). Die eigentliche Installation eines Git-Hooks
    (Datei unter ``.git/hooks/`` anlegen) ist ROADMAP v0.2+.
    """

    name = "git"
    reason = "Git-Hook-Installation ist fuer v0.1 bewusst nicht gebaut (siehe ROADMAP v0.2+)."
