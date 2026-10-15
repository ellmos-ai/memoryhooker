"""Behaviors present in the private lineage that the public core must retain."""

import os
from pathlib import Path

import pytest

from memoryhooker.backends.files import FilesBackend
from memoryhooker.config import ClueConfig, Config, GateConfig, ModeConfig
from memoryhooker.modes import evaluate_prompt
from memoryhooker.state import SessionState


def _directory_link(target: Path, link: Path) -> None:
    if os.name == 'nt':
        import _winapi

        _winapi.CreateJunction(str(target), str(link))
    else:
        link.symlink_to(target, target_is_directory=True)


def test_search_rejects_directory_link_outside_root(tmp_path):
    root = tmp_path / 'allowed'
    outside = tmp_path / 'private'
    root.mkdir()
    outside.mkdir()
    (root / 'own.md').write_text('gardener internal note', encoding='utf-8')
    (outside / 'secret.md').write_text('gardener external secret', encoding='utf-8')
    _directory_link(outside, root / 'linked')

    hits = FilesBackend(root).search('gardener')

    assert [hit.source for hit in hits] == ['own.md']
    assert all('external secret' not in hit.text for hit in hits)


def test_explicit_file_root_remains_allowed_after_rejected_link(tmp_path):
    root = tmp_path / 'allowed'
    outside = tmp_path / 'explicit'
    root.mkdir()
    outside.mkdir()
    file = outside / 'note.md'
    file.write_text('gardener explicitly selected', encoding='utf-8')
    _directory_link(outside, root / 'linked')

    hits = FilesBackend(roots=[root, file]).search('gardener')

    assert len(hits) == 1
    assert hits[0].source == 'note.md'
    assert hits[0].meta['root'] == str(outside)


@pytest.mark.parametrize('gated', [False, True])
def test_clue_does_not_match_inside_longer_word(tmp_path, gated):
    (tmp_path / 'note.md').write_text('memory memory memory', encoding='utf-8')
    config = Config(mode=ModeConfig(active='clue', min_rank=0.1),
                    clue=ClueConfig(triggers=['memory']), gate=GateConfig(enabled=gated))
    state = SessionState()

    assert evaluate_prompt('memoryhooker is a module', config, FilesBackend(tmp_path), state) is None
    assert state.injections_count == 0


@pytest.mark.parametrize('gated', [False, True])
@pytest.mark.parametrize(('trigger', 'prompt'), [
    ('User Prompt', 'User\n   Prompt wurde gesendet'),
    ('Straße', 'STRASSE wurde erwähnt'),
])
def test_clue_normalizes_phrase_whitespace_and_unicode(tmp_path, gated, trigger, prompt):
    (tmp_path / 'note.md').write_text((trigger + ' ') * 4, encoding='utf-8')
    config = Config(mode=ModeConfig(active='clue', min_rank=0.1),
                    clue=ClueConfig(triggers=[trigger]), gate=GateConfig(enabled=gated))
    state = SessionState()

    message = evaluate_prompt(prompt, config, FilesBackend(tmp_path), state)

    assert message is not None
    assert 'note.md' in message
    assert state.injections_count == 1
