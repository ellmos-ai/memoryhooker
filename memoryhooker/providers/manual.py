from __future__ import annotations

from hook_master.providers.manual import ManualProvider as BaseManualProvider


class ManualProvider(BaseManualProvider):
    """Kein Hook -- das Modul stellt nur eine CLI bereit, die der Agent
    selbst aufruft (``python -m memoryhooker check "<prompt>"``).

    Immer verfuegbar: garantiert, dass die Provider-Fallback-Kette nie ganz
    leerlaeuft.
    """

    name = "manual"


__all__ = ["ManualProvider"]
