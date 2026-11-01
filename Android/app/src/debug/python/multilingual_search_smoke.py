"""On-device script normalization and recording guards; no network dependency."""

import json
from matching import words, version_signature
from lyrics_service import best_recording
from text_search import equivalent, contains_terms


def verify():
    assert words('ｶﾞﾗｽ') == words('がらす') == words('ガラス')
    assert words('ガラス') != words('カラス')
    assert words('й') != words('и')
    assert words('माल') != words('मल')
    assert words('한글') == words('한글')
    assert equivalent('サヨナラ', 'Sayonara')
    assert contains_terms('さよなら', 'サヨナラの季節')
    assert version_signature('Song (ライブ)') == {'live'}
    assert version_signature('Song (리믹스)') == {'remix'}
    row = dict(
        trackName='サヨナラ', artistName='Artist', duration=200, plainLyrics='Fixture'
    )
    assert best_recording([row], 'さよなら', 'Artist', duration=200) is row
    assert best_recording([row], 'Sayonara', 'Artist', duration=200) is row
    assert best_recording([row], 'Sayonara', 'Other', duration=200) is None
    assert best_recording([row], 'Sayonara', 'Artist', duration=260) is None
    assert (
        best_recording(
            [dict(row, trackName='サヨナラ (ライブ)')],
            'さよなら',
            'Artist',
            duration=200,
        )
        is None
    )
    return json.dumps(
        dict(ok=True, kana=True, multilingual=True, recording_guards=True)
    )
