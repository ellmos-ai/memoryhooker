# -*- coding: utf-8 -*-
"""MemoryHooker -- Hook-getriebenes Gedaechtnis.

Ein Hook, der im Harness sitzt (nicht im Speicher) und das LLM ans Suchen
erinnert -- oder selbst sucht und den Treffer mitliefert. Siehe README.md
und ROADMAP.md.

Status: v0.2.1.
"""

from .config import Config, load_config
from .protocol import Hit, MemoryBackend

__version__ = "0.2.1"

__all__ = ["Hit", "MemoryBackend", "Config", "load_config", "__version__"]
