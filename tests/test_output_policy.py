from memoryhooker.config import OutputConfig
from memoryhooker.output_policy import deterministic_hits, sanitize_hit, sanitize_message
from memoryhooker.protocol import Hit


def test_redacts_local_paths_and_secrets_before_bounding():
    config = OutputConfig(max_message_chars=120)
    raw = "token=super-secret C:\\Users\\alice\\private\\memory.md /home/alice/private.txt"

    cleaned = sanitize_message(raw, config)

    assert "super-secret" not in cleaned
    assert "alice" not in cleaned
    assert cleaned.count("[redacted]") == 3
    assert len(cleaned) <= 120


def test_redacts_windows_paths_with_spaces_atomically():
    config = OutputConfig(max_message_chars=200)

    cleaned = sanitize_message(
        r'open "C:\Users\Alice Smith\private notes.txt" or C:\Users\Alice Smith\secret.txt',
        config,
    )

    assert "Alice" not in cleaned
    assert "Smith" not in cleaned
    assert "private notes" not in cleaned
    assert "secret.txt" not in cleaned
    assert cleaned == "open [redacted] or [redacted]"


def test_long_unicode_hit_is_bounded_deterministically():
    config = OutputConfig(max_text_chars=20, truncation_marker="…")

    cleaned = sanitize_hit(Hit("ä" * 30, "relative.md", 0.8), config)

    assert cleaned.text == "ä" * 19 + "…"
    assert len(cleaned.text) == 20


def test_sensitive_meta_is_redacted_but_status_and_version_pass_through():
    config = OutputConfig()
    hit = Hit(
        "note",
        "relative.md",
        0.8,
        {"status": "contradicted", "version": "stale-v1", "api_key": "secret"},
    )

    cleaned = sanitize_hit(hit, config)

    assert cleaned.meta == {
        "api_key": "[redacted]",
        "status": "contradicted",
        "version": "stale-v1",
    }


def test_malformed_hit_is_hook_safe():
    class Broken:
        text = None
        source = None
        rank = "not-a-number"
        meta = ["not", "a", "mapping"]

    cleaned = sanitize_hit(Broken(), OutputConfig())

    assert cleaned == Hit(text="", source="", rank=0.0, meta={})


def test_raising_hit_properties_are_hook_safe():
    class Broken:
        def __getattribute__(self, name):
            if name in {"text", "source", "rank", "meta"}:
                raise RuntimeError("hostile backend record")
            return super().__getattribute__(name)

    cleaned = sanitize_hit(Broken(), OutputConfig())

    assert cleaned == Hit(text="", source="", rank=0.0, meta={})


def test_metadata_has_entry_total_and_numeric_magnitude_bounds():
    config = OutputConfig(max_meta_entries=2, max_meta_total_chars=20)
    hit = Hit(
        "note",
        "a.md",
        0.8,
        {"a": 10**100_000, "b": "short", "c": "must-not-appear"},
    )

    cleaned = sanitize_hit(hit, config)

    assert len(cleaned.meta) <= 2
    assert cleaned.meta["a"] == "…[truncated]"
    assert "c" not in cleaned.meta


def test_deterministic_tie_order_uses_source_then_text_and_keeps_missing_anchor():
    hits = [
        Hit("z", "b.md", 0.8),
        Hit("missing", "", 0.8, {"status": "candidate"}),
        Hit("a", "a.md", 0.8),
    ]

    selected = deterministic_hits(hits, OutputConfig(), 3)

    assert [(hit.source, hit.text) for hit in selected] == [
        ("", "missing"),
        ("a.md", "a"),
        ("b.md", "z"),
    ]
    assert selected[0].meta["status"] == "candidate"
