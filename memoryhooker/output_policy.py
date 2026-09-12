"""Deterministic privacy and size boundary for backend-derived hook records."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from typing import Any

from .config import OutputConfig
from .protocol import Hit

_SENSITIVE_KEY = re.compile(
    r"(?:api[_-]?key|access[_-]?token|auth(?:orization)?|cookie|password|secret|token)",
    re.IGNORECASE,
)
_SENSITIVE_ASSIGNMENT = re.compile(
    r"\b(api[_-]?key|access[_-]?token|authorization|cookie|password|secret|token)"
    r"\b\s*[:=]\s*(?:\"[^\"]*\"|'[^']*'|[^\s,;]+)",
    re.IGNORECASE,
)
_TOKEN_VALUE = re.compile(
    r"(?i)(?:bearer\s+|sk-|ghp_|github_pat_)[A-Za-z0-9_.\-]{8,}"
)
_QUOTED_LOCAL_PATH = re.compile(
    r"(?P<quote>[\"'])(?:(?:[A-Za-z]:[\\/]|\\\\)|/(?:Users|home|root|tmp|var|private|mnt|opt)/)"
    r".*?(?P=quote)",
    re.IGNORECASE,
)
_WINDOWS_FILE_PATH_WITH_SPACES = re.compile(
    r"(?<![A-Za-z0-9_])(?:"
    r"(?:[A-Za-z]:\\|\\\\)(?:[^\\\r\n<>\"'|,;]+\\)+[^\\\r\n<>\"'|,;]*?"
    r"\.[A-Za-z0-9]{1,12}(?=$|[\s,;)\]])|"
    r"[A-Za-z]:/(?:[^/\r\n<>\"'|,;]+/)+[^/\r\n<>\"'|,;]*?"
    r"\.[A-Za-z0-9]{1,12}(?=$|[\s,;)\]])"
    r")"
)
_WINDOWS_PATH = re.compile(
    r"(?<![A-Za-z0-9_])(?:[A-Za-z]:[\\/]|\\\\)[^\s<>\"'|]+"
)
_POSIX_LOCAL_PATH = re.compile(
    r"(?<![A-Za-z0-9_])/(?:Users|home|root|tmp|var|private|mnt|opt)/[^\s<>\"']+"
)


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    try:
        return str(value)
    except Exception:
        return ""


def _bound(value: str, limit: int, marker: str) -> str:
    if len(value) <= limit:
        return value
    if limit <= len(marker):
        return marker[:limit]
    return value[: limit - len(marker)] + marker


def sanitize_text(value: Any, limit: int, config: OutputConfig) -> str:
    """Redact first, then apply a deterministic Unicode character bound."""
    text = _safe_text(value)
    marker = config.redaction_marker
    text = _SENSITIVE_ASSIGNMENT.sub(lambda match: f"{match.group(1)}={marker}", text)
    text = _TOKEN_VALUE.sub(marker, text)
    text = _QUOTED_LOCAL_PATH.sub(marker, text)
    text = _WINDOWS_FILE_PATH_WITH_SPACES.sub(marker, text)
    text = _WINDOWS_PATH.sub(marker, text)
    text = _POSIX_LOCAL_PATH.sub(marker, text)
    return _bound(text, limit, config.truncation_marker)


def _safe_rank(value: Any) -> float:
    try:
        rank = float(value)
    except (TypeError, ValueError, OverflowError):
        return 0.0
    if not math.isfinite(rank):
        return 0.0
    return min(1.0, max(0.0, rank))


def _sanitize_meta(meta: Any, config: OutputConfig) -> dict[str, Any]:
    if not isinstance(meta, Mapping):
        return {}
    cleaned: dict[str, Any] = {}
    total_chars = 0
    try:
        raw_keys = sorted(meta, key=lambda item: _safe_text(item))
        for raw_key in raw_keys[: config.max_meta_entries]:
            key = sanitize_text(raw_key, config.max_meta_chars, config)
            if not key:
                continue
            value = meta[raw_key]
            if _SENSITIVE_KEY.search(key):
                safe_value: Any = config.redaction_marker
            elif isinstance(value, bool) or value is None:
                safe_value = value
            elif isinstance(value, int):
                safe_value = value if value.bit_length() <= 63 else config.truncation_marker
            elif isinstance(value, float):
                safe_value = value if math.isfinite(value) else None
            else:
                safe_value = sanitize_text(value, config.max_meta_chars, config)
            entry_chars = len(key) + len(_safe_text(safe_value))
            if total_chars + entry_chars > config.max_meta_total_chars:
                break
            cleaned[key] = safe_value
            total_chars += entry_chars
    except Exception:
        return {}
    return cleaned


def _safe_attr(value: Any, name: str, default: Any) -> Any:
    try:
        return getattr(value, name, default)
    except Exception:
        return default


def sanitize_hit(value: Any, config: OutputConfig) -> Hit:
    """Turn even malformed backend values into a bounded, safe ``Hit``."""
    return Hit(
        text=sanitize_text(_safe_attr(value, "text", ""), config.max_text_chars, config),
        source=sanitize_text(_safe_attr(value, "source", ""), config.max_source_chars, config),
        rank=_safe_rank(_safe_attr(value, "rank", 0.0)),
        meta=_sanitize_meta(_safe_attr(value, "meta", {}), config),
    )


def sanitize_hits(values: Any, config: OutputConfig) -> list[Hit]:
    if not isinstance(values, (list, tuple)):
        return []
    return [sanitize_hit(value, config) for value in values]


def deterministic_hits(values: Any, config: OutputConfig, limit: int) -> list[Hit]:
    """Total ordering used only by the opt-in gate path."""
    hits = sanitize_hits(values, config)
    hits.sort(key=lambda hit: (-hit.rank, hit.source, hit.text, _canonical_meta(hit.meta)))
    return hits[: max(0, limit)]


def sanitize_message(value: Any, config: OutputConfig) -> str:
    return sanitize_text(value, config.max_message_chars, config)


def selection_digest(hits: list[Hit]) -> str:
    payload = [
        {"text": hit.text, "source": hit.source, "rank": hit.rank, "meta": hit.meta}
        for hit in hits
    ]
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _canonical_meta(meta: dict[str, Any]) -> str:
    return json.dumps(meta, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
