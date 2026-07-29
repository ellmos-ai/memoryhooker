from memoryhooker.protocol import Hit


def test_hit_defaults_meta_to_empty_dict():
    hit = Hit(text="x", source="y", rank=0.9)
    assert hit.meta == {}


def test_hit_is_frozen():
    import dataclasses

    hit = Hit(text="x", source="y", rank=0.9)
    with __import__("pytest").raises(dataclasses.FrozenInstanceError):
        hit.rank = 0.1  # type: ignore[misc]
