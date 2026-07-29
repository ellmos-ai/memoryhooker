"""Minimaler TOML-Reader mit stdlib-Vorrang.

``tomllib`` ist erst ab Python 3.11 in der Stdlib. Das Modul bleibt laut
``pyproject.toml`` bei ``requires-python >= 3.10`` und zero-dependency --
deshalb hier ein winziger Fallback-Parser fuer genau das Teilmengen-Schema,
das die eigene Config braucht: Abschnitte (``[a]``, ``[a.b]``), Zeilen der
Form ``key = value`` mit String/Bool/Int/Float/Array-von-Strings als Wert.

Kein Anspruch auf TOML-Vollstaendigkeit (keine Multiline-Strings, keine
Inline-Tabellen, keine Datumswerte). Wird das je zu wenig, ist der saubere
Ausweg ein echtes drittes-Partei-Paket -- nicht dieser Parser.
"""

from __future__ import annotations

import re

try:  # pragma: no cover - abhaengig von der Python-Version
    import tomllib as _tomllib
except ImportError:  # pragma: no cover - Python < 3.11
    _tomllib = None


_SECTION_RE = re.compile(r"^\[(?P<name>[A-Za-z0-9_.\-]+)\]$")
_KV_RE = re.compile(r"^(?P<key>[A-Za-z0-9_\-]+)\s*=\s*(?P<value>.+)$")


def loads(text: str) -> dict:
    """Parst TOML-Text zu einem verschachtelten dict.

    Nutzt ``tomllib`` wenn verfuegbar (Python >= 3.11); sonst den
    Fallback-Parser in :func:`loads_fallback`.
    """
    if _tomllib is not None:
        return _tomllib.loads(text)
    return loads_fallback(text)


def loads_fallback(text: str) -> dict:
    """Fallback-Parser fuer das MemoryHooker-Config-Teilschema.

    Wird bewusst auch unter Python >= 3.11 direkt getestet (siehe
    ``tests/test_toml_fallback.py``), damit der Fallback-Pfad nicht nur auf
    alten Interpretern Testabdeckung hat.
    """
    root: dict = {}
    current: dict = root

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        section_match = _SECTION_RE.match(line)
        if section_match:
            current = _ensure_section(root, section_match.group("name"))
            continue

        kv_match = _KV_RE.match(line)
        if not kv_match:
            raise ValueError(f"unlesbare TOML-Zeile (Fallback-Parser): {raw_line!r}")

        current[kv_match.group("key")] = _parse_value(kv_match.group("value").strip())

    return root


def _ensure_section(root: dict, dotted_name: str) -> dict:
    node = root
    for part in dotted_name.split("."):
        node = node.setdefault(part, {})
    return node


def _parse_value(raw: str):
    # Inline-Kommentar abschneiden (nur ausserhalb von Anfuehrungszeichen)
    raw = _strip_inline_comment(raw)

    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(item.strip()) for item in _split_top_level(inner)]

    return _parse_scalar(raw)


def _split_top_level(inner: str) -> list[str]:
    items: list[str] = []
    depth = 0
    current = []
    in_string = False
    for ch in inner:
        if ch == '"' and (not current or current[-1] != "\\"):
            in_string = not in_string
        if ch == "," and depth == 0 and not in_string:
            items.append("".join(current))
            current = []
            continue
        if ch in "[{" and not in_string:
            depth += 1
        if ch in "]}" and not in_string:
            depth -= 1
        current.append(ch)
    if current:
        items.append("".join(current))
    return items


def _parse_scalar(raw: str):
    if len(raw) >= 2 and raw[0] == '"' and raw[-1] == '"':
        return raw[1:-1]
    if len(raw) >= 2 and raw[0] == "'" and raw[-1] == "'":
        return raw[1:-1]
    if raw in ("true", "false"):
        return raw == "true"
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    raise ValueError(f"unlesbarer TOML-Wert (Fallback-Parser): {raw!r}")


def _strip_inline_comment(raw: str) -> str:
    in_string = False
    for i, ch in enumerate(raw):
        if ch == '"':
            in_string = not in_string
        if ch == "#" and not in_string:
            return raw[:i].strip()
    return raw
