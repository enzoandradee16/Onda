import io
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

from filename_metadata import filename_hint, search, details, identify_entries


def candidate(title='Music Sounds Better With You', artist='Stardust', identity='1'):
    return dict(title=title, artists=[artist], album='Original', duration_ms=240000,
                platform='Deezer', explicit=False, source_url='https://www.deezer.com/track/' + identity)


class FilenameRecognitionTests(unittest.TestCase):
    def test_filename_cleanup_keeps_version_and_meaningful_numbers(self):
        for name in ('01 - Stardust - Music Sounds Better With You [Official Audio] [aBcD1234567].mp3',
                     '01_Stardust_-_Music_Sounds_Better_With_You_(Official_Video).flac'):
            with self.subTest(name=name):
                hint = filename_hint(name)
                self.assertEqual(hint['title'], 'Music Sounds Better With You')
                self.assertEqual(hint['artists'], ['Stardust'])
        self.assertEqual(filename_hint('Artist - Song (Live Remix).mp3')['title'], 'Song (Live Remix)')
        self.assertEqual(filename_hint('1999.mp3')['title'], '1999')
        self.assertEqual(filename_hint('Artist - Song.part.2.mp3')['title'], 'Song.part.2')

    def test_existing_tags_take_priority_and_fallback_title_is_not_a_tag(self):
        hint = filename_hint('Other - Filename.mp3', {'title': 'Correct', 'artists': ['Artist'], 'duration': 123})
        self.assertEqual(hint['title'], 'Correct')
        self.assertEqual(hint['artists'], ['Artist'])
        self.assertEqual(hint['duration_ms'], 123000)
        hint = filename_hint('Stardust - Song.mp3', {'title': 'Stardust - Song'})
        self.assertEqual(hint['title'], 'Song')

    def test_meaningless_name_requires_user_information(self):
        for name in ('track01.mp3', 'audio_123.wav', ''):
            with self.assertRaises(ValueError):
                filename_hint(name)

    def search_with(self, name, records, brainz=None):
        worker = Mock()
        worker.search.return_value = records
        with patch('metadata.MetadataClient', return_value=worker), patch('filename_metadata._brainz', return_value=brainz or []):
            return search({'filename': name}, threading.Event())

    def test_reversed_filename_and_different_version_require_review(self):
        result = self.search_with('Music Sounds Better With You - Stardust.mp3', [candidate()])
        self.assertEqual(result['anchor']['artists'], ['Stardust'])
        self.assertTrue(result['candidates'])
        result = self.search_with('Stardust - Music Sounds Better With You (Live).mp3', [candidate()])
        self.assertTrue(result['candidates'][0]['manual_review'])

    def test_radio_edit_is_offered_explicitly_when_filename_has_no_version(self):
        row = dict(candidate(), title='Music Sounds Better With You (Radio Edit)', title_version='(Radio Edit)')
        result = self.search_with('Stardust - Music Sounds Better With You.mp3', [row])
        self.assertEqual(result['candidates'][0]['title'], row['title'])
        self.assertIn('versão', result['candidates'][0]['match_reasons'][0])

    def test_extended_file_can_review_original_without_claiming_same_edition(self):
        result = self.search_with('Stardust - Music Sounds Better With You (Extended).mp3', [candidate()])
        self.assertEqual(result['anchor']['title'], 'Music Sounds Better With You (Extended)')
        self.assertTrue(result['candidates'][0]['manual_review'])
        self.assertIn('versão', result['candidates'][0]['match_reasons'][0])

    def test_instrumental_and_larger_duration_difference_are_review_suggestions(self):
        from filename_metadata import _rank
        from filename_metadata import _review_title
        self.assertEqual(_review_title('Song (Deliverance)'), 'Song (Deliverance)')
        anchor=dict(title='The Girl Is Mine (Instrumental)',artists=['Michael Jackson, Paul McCartney'],duration_ms=393651)
        rows=[dict(candidate('The Girl Is Mine','Michael Jackson'),duration_ms=222000)]
        self.assertTrue(_rank(anchor,rows)[0]['manual_review'])
        anchor=dict(title='Song',artists=['Artist'],duration_ms=200000)
        self.assertTrue(_rank(anchor,[dict(candidate('Song','Artist'),duration_ms=220000)])[0]['manual_review'])
        self.assertEqual(_rank(anchor,[dict(candidate('Song','Other Artist'),duration_ms=400000)]),[])
        self.assertEqual(_rank(anchor,[candidate('Completely Unrelated','Artist')]),[])

    def test_compilation_ranks_lower_and_one_failed_service_is_tolerated(self):
        compilation = dict(candidate(identity='2'), album='Greatest Hits')
        worker = Mock()
        worker.search.side_effect = lambda query, provider, **kw: [compilation, candidate()] if provider == 'Deezer' else (_ for _ in ()).throw(ValueError('offline'))
        with patch('metadata.MetadataClient', return_value=worker), patch('filename_metadata._brainz', side_effect=OSError('offline')):
            result = search({'filename': 'Stardust - Music Sounds Better With You.mp3'}, threading.Event())
        self.assertEqual(result['candidates'][0]['album'], 'Original')
        self.assertEqual(len(result['warnings']), 2)

    def test_one_provider_match_does_not_prevent_other_provider_fallbacks(self):
        worker = Mock()
        def lookup(query, provider, **kwargs):
            if provider == 'Deezer' and 'Instrumental' in query:
                return []
            return [dict(candidate('Song','Artist'), platform=provider,
                         source_url=provider + ':1')]
        worker.search.side_effect = lookup
        brainz = dict(candidate('Song','Artist'), platform='MusicBrainz',source_url='brainz:1')
        with patch('metadata.MetadataClient', return_value=worker), patch('filename_metadata._brainz',side_effect=lambda anchor: [] if 'Instrumental' in anchor['title'] else [brainz]):
            result=search({'filename':'Artist - Song (Instrumental).mp3'},threading.Event())
        self.assertEqual({row['platform'] for row in result['candidates']},{'Deezer','Apple / iTunes','MusicBrainz'})

    def test_musicbrainz_queries_grouped_artist_credits_as_alternatives(self):
        from filename_metadata import _brainz
        with patch('artist_alias_lookup.AliasCache'),patch('artist_alias_lookup.get_json',return_value={'recordings':[]}) as get:
            _brainz({'title':'Song','artists':['Michael Jackson, Paul McCartney']})
        query=get.call_args.args[1]['query']
        self.assertIn('OR artist:"Michael Jackson"',query)
        self.assertIn('OR artist:"Paul McCartney"',query)

    def test_all_unavailable_services_are_not_reported_as_no_matches(self):
        worker = Mock()
        worker.search.side_effect = ValueError('offline')
        with patch('metadata.MetadataClient', return_value=worker), patch('filename_metadata._brainz', side_effect=OSError('offline')):
            with self.assertRaisesRegex(ValueError, 'consultar os catálogos'):
                search({'filename': 'Artist - Song.mp3'}, threading.Event())

    def test_cancellation_never_launches_network_search(self):
        cancel = threading.Event()
        cancel.set()
        with patch('metadata.MetadataClient') as client, self.assertRaises(InterruptedError):
            search({'filename': 'Artist - Song.mp3'}, cancel)
        client.assert_not_called()

    def test_details_return_fields_without_erasing_unknown_existing_tags(self):
        worker = Mock()
        worker.fetch.return_value = dict(candidate(), track_number=2, genre='House', album_artists=['Album artist'], cover_url='https://example.org/cover.jpg')
        with patch('metadata.MetadataClient', return_value=worker):
            result = details(dict(candidate(), platform='Apple / iTunes'), threading.Event())
        self.assertEqual(result['changes']['track_number'], '2')
        self.assertEqual(result['changes']['album_artist'], 'Album artist')
        self.assertNotIn('comment', result['changes'])
        self.assertEqual(result['cover_url'], 'https://example.org/cover.jpg')

    def test_deezer_album_completes_genre_without_replacing_the_reviewed_artist(self):
        worker = Mock()
        worker.get_json.side_effect = [
            dict(id='1', title='Song', artist={'name': 'Stardust'}, contributors=[{'name': 'Stardust'}, {'name': 'Other credit'}], album={'id': 10, 'title': 'Original'}),
            dict(artist={'name': 'Stardust'}, genres={'data': [{'name': 'House'}]}),
        ]
        with patch('metadata.MetadataClient', return_value=worker):
            result = details(candidate('Song'), threading.Event())
        self.assertEqual(result['changes']['artists'], ['Stardust'])
        self.assertEqual(result['changes']['genre'], 'House')
        self.assertEqual(result['changes']['album_artist'], 'Stardust')

    def test_mobile_batch_uses_filename_without_importing_audio_and_requires_choice(self):
        cancel = threading.Event()
        entries = [dict(filename='Artist - One.mp3', identity='uri:one'), dict(filename='Artist - Two.mp3', identity='uri:two')]
        choose = Mock(side_effect=lambda anchor, rows: rows[0])
        with patch('filename_metadata.search', side_effect=[dict(anchor={'title': 'One'}, candidates=[candidate('One')]), dict(anchor={'title': 'Two'}, candidates=[candidate('Two')])]), patch('filename_metadata.details', side_effect=lambda row, _: {'changes': {'title': row['title']}, 'cover_url': ''}):
            result = identify_entries({'entries': entries}, cancel, choose, Mock())
        self.assertEqual([m['changes']['title'] for m in result['matches']], ['One', 'Two'])
        self.assertEqual(choose.call_count, 2)

    def test_cancelled_choice_does_not_apply_partial_batch_and_empty_batch_is_invalid(self):
        cancel = threading.Event()
        entries = [dict(filename='Artist - One.mp3', identity='uri:one')]
        def choose(*args):
            cancel.set()
            return candidate('One')
        with patch('filename_metadata.search', return_value=dict(anchor={}, candidates=[candidate('One')])), patch('filename_metadata.details') as complete:
            with self.assertRaises(InterruptedError):
                identify_entries({'entries': entries}, cancel, choose, Mock())
            complete.assert_not_called()
        with self.assertRaises(ValueError):
            identify_entries({'entries': []}, threading.Event(), Mock(), Mock())

    def test_batch_keeps_each_track_metadata_and_manual_fields_override_only_when_requested(self):
        from batch_metadata import edit_batch
        worker = Mock(return_value={'path': 'copy.wav'})
        config = dict(sources=[{'source': 'one.wav', 'changes': {'title': 'One'}}, {'source': 'two.wav', 'changes': {'title': 'Two'}}], changes={'album': 'Common'})
        with patch('batch_metadata.edit_copy', worker):
            result = edit_batch(config)
        self.assertFalse(result['errors'])
        self.assertEqual([call.args[0]['changes']['title'] for call in worker.call_args_list], ['One', 'Two'])
        self.assertTrue(all(call.args[0]['changes']['album'] == 'Common' for call in worker.call_args_list))

    def test_invalid_per_file_field_is_rejected_before_any_write(self):
        from batch_metadata import edit_batch
        with patch('batch_metadata.edit_copy') as worker, self.assertRaises(ValueError):
            edit_batch(dict(sources=[{'source': 'one.wav', 'changes': {'title': 'One'}}, {'source': 'two.wav', 'changes': {'invalid': 'x'}}]))
        worker.assert_not_called()

    def test_catalog_cover_is_only_downloaded_when_saving_and_source_audio_is_preserved(self):
        from PIL import Image
        from audio_library import edit_copy, read_audio, cover_preview
        from test_metadata_clipboard import audio
        cover = io.BytesIO()
        Image.new('RGB', (4, 4), 'red').save(cover, 'PNG')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'song.wav'
            audio(path)
            original = path.read_bytes()
            with patch('tagging.fetch_cover', return_value=(cover.getvalue(), 'image/png')) as fetch:
                result = edit_copy(dict(source=str(path), changes={'title': 'Recognized'}, edit_metadata=True, cover_url='https://example.org/cover.png'))
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(read_audio(result['path'])['title'], 'Recognized')
            self.assertTrue(cover_preview(result['path']))
            fetch.assert_called_once()


@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'), 'Optional desktop test')
class FilenameDesktopTests(unittest.TestCase):
    def test_real_desktop_worker_reviews_before_applying_and_never_saves_automatically(self):
        from test_qt_workspace import NativeDesktopTests
        from test_metadata_clipboard import audio
        NativeDesktopTests.setUpClass()
        fixture = NativeDesktopTests()
        fixture.setUp()
        try:
            source = fixture.root / 'Stardust - Song.wav'
            audio(source)
            before = source.read_bytes()
            fixture.ws.accept_files('metadata', [str(source)])
            fixture.task_done('audio_read')
            row = candidate('Song')
            found = dict(anchor={'title': 'Song', 'artists': ['Stardust']}, candidates=[row])
            chosen = dict(changes={'title': 'Song', 'album': 'Selected album'}, cover_url='')
            with patch('filename_metadata.search', return_value=found), patch('filename_metadata.details', return_value=chosen):
                fixture.ws.invoke('audio_identify_name', {})
                fixture.wait_for(lambda: bool(fixture.ws._choice))
                self.assertNotEqual(fixture.ws.options['metadata'].get('album'), 'Selected album')
                fixture.ws.replyChoice(fixture.ws._choice['identity'], {'selected_id': row['source_url']})
                fixture.wait_for(lambda: fixture.ws.options['metadata'].get('album') == 'Selected album')
            self.assertEqual(source.read_bytes(), before)
        finally:
            fixture.tearDown()

    def test_batch_stages_distinct_matches_and_ignores_results_for_another_selection(self):
        from qt_workspace_ui import DesktopWorkspace
        from types import SimpleNamespace
        workspace = SimpleNamespace(options={'metadataSources': ['one.wav', 'two.wav'], 'metadata': {'title': 'Old'}}, closed=False,
                                    cancel_task=Mock(), run_task=Mock(), present_choice=Mock(), optionsChanged=Mock(), notify=Mock(), message=Mock())
        DesktopWorkspace.identify_metadata_names(workspace)
        for title in ('One', 'Two'):
            found = workspace.run_task.call_args.args[2]
            row = candidate(title)
            found(dict(anchor={'title': title}, candidates=[row]))
            selected = workspace.present_choice.call_args.args[2]
            selected({'selected_id': row['source_url']})
            workspace.run_task.call_args.args[2]({'changes': {'title': title}, 'cover_url': ''})
        self.assertEqual(workspace.options['metadataMatches']['one.wav']['changes']['title'], 'One')
        self.assertEqual(workspace.options['metadataMatches']['two.wav']['changes']['title'], 'Two')
        self.assertEqual(workspace.options['metadataFields'], {})
        workspace.options['metadataSources'] = ['one.wav']
        DesktopWorkspace.identify_metadata_names(workspace)
        late = workspace.run_task.call_args.args[2]
        workspace.options['metadataSources'] = ['another.wav']
        previous = workspace.options['metadata'].copy()
        late(dict(anchor={'title': 'Late'}, candidates=[candidate('Late')]))
        self.assertEqual(workspace.options['metadata'], previous)
