from memoryhooker.backends.bach import BachBackend

# UsmcBackend ist seit T-20260816-972236043 kein Stub mehr -- siehe
# tests/test_backends_usmc.py fuer die echten Verhaltenstests (inkl. der
# Garantie, dass ein fehlender DB-Pfad weiterhin "unavailable" bleibt).


def test_bach_backend_always_unavailable():
    backend = BachBackend()
    assert backend.available() is False
    assert backend.search("x") == []
