"""Run recording and search invariants in Android's packaged Python runtime."""

import json
import tempfile
from pathlib import Path


def verify(folder):
    from matching import (
        select_candidate,
        AmbiguousMatch,
        revalidate_match,
        NoCompatibleMatch,
    )
    from catalog_match import rank_catalog
    from music_search import parse_query, accepts, SearchCancelled, search_music
    from metadata import MetadataClient
    from search_choices import ChoiceStore

    anchor = dict(
        title='Colette - Remastered 2022',
        artists=['Piero Piccioni'],
        album='Addio Alexandra',
        duration_ms=105700,
        release_date='2022-01-07',
        isrc='ITC002100939',
    )
    other = dict(
        anchor,
        title='Colette',
        duration_ms=105000,
        source_url='https://www.deezer.com/track/4204565132',
    )
    assert rank_catalog(anchor, [other])[0]['same_isrc']
    assert not rank_catalog(anchor, [dict(other, title='Colette - Remastered 2011')])
    assert accepts(
        other,
        parse_query('Colette artista:"Piero Piccioni" ano:2022 duracao:1:40-1:50'),
    )
    video = dict(
        id='abcdefghijk',
        title='Colette',
        channel='Piero Piccioni - Topic',
        duration=105,
    )
    match = select_candidate(other, [video])
    revalidate_match(other, match, video)
    try:
        revalidate_match(other, match, dict(video, duration=300))
    except NoCompatibleMatch:
        pass
    else:
        raise AssertionError('Changed duration accepted')
    assert (
        select_candidate(
            other, [video, dict(video, id='other123456')], prefer_best=True
        )['id']
        == video['id']
    )
    try:
        select_candidate(other, [video, dict(video, id='other123456')])
    except AmbiguousMatch:
        pass
    else:
        raise AssertionError('Manual ambiguity confirmation lost')
    client = MetadataClient()
    try:
        try:
            search_music(client, 'Colette', cancelled=lambda: True)
        except SearchCancelled:
            pass
        else:
            raise AssertionError('Cancelled search continued')
    finally:
        client.close()
    with tempfile.TemporaryDirectory(dir=folder) as temporary:
        store = ChoiceStore(Path(temporary) / 'choices.sqlite')
        store.set(other, video['id'], True)
        assert store.get(other)[video['id']]
        store.clear(other)
        assert not store.get(other)
    from matching import score_candidate, version_signature

    soundtrack = dict(other, title='La Famiglia', duration_ms=200000)
    styled = dict(
        video,
        title='Film Music | "La Famiglia" ● Piero Piccioni (HD Audio)',
        duration=200,
    )
    assert score_candidate(soundtrack, styled) > 0.94
    assert version_signature('Cue Version 3') == version_signature('Cue part.3')
    assert version_signature('Cue Version 2') != version_signature('Cue part.3')
    return json.dumps({'checks': 10, 'success': True})
