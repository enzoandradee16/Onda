import unittest
from unittest.mock import Mock, patch
from matching import version_signature
from search_evidence import explicit_conflict
from qt_online_playback_ui import OnlinePlayback


class PlaybackRegressionTests(unittest.TestCase):
    def test_output_failure_can_honor_an_already_prepared_switch_request(self):
        from types import SimpleNamespace
        from qt_jukebox_ui import JukeboxBridge

        model = {'cache': 'prepared'}
        bridge = SimpleNamespace(
            closed=False,
            revision=7,
            playlist=[{'id': 'next'}],
            _switch_pending='next',
            _prepared={'next': model},
            activate_queued=Mock(),
        )
        JukeboxBridge.handle_event(bridge, 7, 'error', 'Previous output failed')
        bridge.activate_queued.assert_called_once_with(0, model, auto_play=True)

    def test_stream_to_prepared_local_track_does_not_wait_for_a_pcm_worker(self):
        import tempfile, threading
        from pathlib import Path
        from types import SimpleNamespace
        from qt_jukebox_ui import JukeboxBridge

        with tempfile.TemporaryDirectory() as directory:
            Path(directory, 'analysis.json').write_text('{}')
            model = dict(cache=directory)
            bridge = SimpleNamespace(
                _transport_revision=0,
                playlist=[dict(id='local')],
                _prepared={'local': model},
                model={'_stream': {'url': 'https://example.com/audio'}},
                _state={'playing': True},
                paused=threading.Event(),
                activate_queued=Mock(),
            )
            JukeboxBridge.playQueued(bridge, 0)
            bridge.activate_queued.assert_called_once_with(0, model, auto_play=True)

    def test_paused_request_is_retained_while_track_is_preparing(self):
        from types import SimpleNamespace
        from qt_jukebox_ui import JukeboxBridge

        bridge = SimpleNamespace(
            _transport_revision=0,
            playlist=[dict(id='waiting', analysis='pending')],
            _prepared={},
            _switch_pending=None,
            prepare_next_queued=Mock(),
        )
        JukeboxBridge.playQueued(bridge, 0, auto_play=False)
        self.assertEqual(bridge._autoplay_entry, 'waiting')
        self.assertFalse(bridge._autoplay_requested)

    def test_explicit_retry_prepares_selected_track_before_ordinary_next(self):
        from types import SimpleNamespace
        from qt_jukebox_ui import JukeboxBridge

        bridge = SimpleNamespace(
            closed=False,
            _queue_preparing=False,
            _queue_timeout_timer=Mock(),
            preferences={},
            queue_index=0,
            playlist=[
                dict(id=name, analysis='pending')
                for name in ('current', 'next', 'retry')
            ],
            _prepared={},
            _queue_cancel={},
            _autoplay_entry=None,
            _queue_priority='retry',
            _switch_pending=None,
            _switch_after=None,
            _switch_models={},
            normal_next_index=lambda: 1,
            config=lambda: {},
            can_stream=lambda: True,
            _state={'playing': False},
            queueChanged=Mock(),
            preparationChanged=Mock(),
            start_worker=Mock(),
        )
        JukeboxBridge.prepare_next_queued(bridge)
        self.assertEqual(list(bridge._queue_cancel), ['retry'])

    def test_original_never_silently_selects_censored_edition(self):
        for label in ['Clean Version', 'Censored', 'Censurada', 'Sem palavrões']:
            self.assertTrue(
                explicit_conflict(
                    dict(title='Song'), dict(title='Song (' + label + ')')
                )
            )
        self.assertFalse(
            explicit_conflict(dict(title='Song (Clean)'), dict(title='Song (Clean)'))
        )

    def test_instrumental_aliases_are_edition_evidence(self):
        for label in ['Off Vocal', 'Backing Track', 'Minus One']:
            self.assertIn('instrumental', version_signature('Song (' + label + ')'))

    def test_stream_fade_waits_for_audible_input_then_cancels_outgoing(self):
        bridge = Mock(transitionSeconds=2)
        player = OnlinePlayback(bridge)
        old = Mock()
        player.outgoing = old
        self.assertEqual(player.gain(), 0)
        player.fade_in = 10
        with patch('qt_online_playback_ui.time.monotonic', return_value=11):
            self.assertEqual(player.gain(), 0.5)
        player.cancel()
        old.cancel.assert_called_once()

    def test_reorder_cancels_obsolete_preparation_before_next_track(self):
        import threading
        from types import SimpleNamespace
        from qt_jukebox_ui import JukeboxBridge

        cancelled = threading.Event()
        bridge = SimpleNamespace(
            closed=False,
            _queue_preparing=True,
            _autoplay_entry=None,
            normal_next_index=lambda: 1,
            playlist=[dict(id='current'), dict(id='next')],
            _prepared={},
            _queue_cancel={'old': cancelled},
            preferences={},
            queue_index=0,
            _queue_priority=None,
            _switch_pending=None,
            _switch_after=None,
            _switch_models={},
            config=lambda: {},
            can_stream=lambda: True,
            _state={'playing': True},
            queueChanged=Mock(),
            preparationChanged=Mock(),
            start_worker=Mock(),
            _queue_timeout_timer=Mock(),
        )
        bridge.playlist[1]['analysis'] = 'pending'
        JukeboxBridge.prepare_next_queued(bridge)
        self.assertTrue(cancelled.is_set())
        bridge.start_worker.assert_called_once()
        self.assertIn('next', bridge._queue_cancel)

    def test_streaming_track_participates_in_gradual_transition(self):
        import threading
        from types import SimpleNamespace
        from qt_jukebox_ui import JukeboxBridge

        bridge = SimpleNamespace(
            model={'_stream': {}},
            online=SimpleNamespace(outgoing=None),
            _params=(0, 0, 0, True),
            _state={'playing': True},
            paused=threading.Event(),
            track_minutes=0,
            preferences={'jukebox_gradual_transition': True},
            _switch_pending=None,
            _autoplay_entry=None,
            normal_next_index=lambda: 1,
            normal_remaining=lambda: 1,
            transitionSeconds=2,
            playlist=[dict(id='current'), dict(id='next')],
            _prepared={'next': {}},
            queue_repeat='Desativada',
            nextTrack=Mock(),
        )
        JukeboxBridge.normal_transition(bridge)
        bridge.nextTrack.assert_called_once()

    def test_pause_freezes_both_sides_of_stream_transition(self):
        bridge = Mock(transitionSeconds=2)
        player = OnlinePlayback(bridge)
        old = OnlinePlayback(bridge)
        player.outgoing = old
        player.fade_in = 10
        old.fade_out = 10
        with patch('qt_online_playback_ui.time.monotonic', return_value=10.5):
            player.pause_fade(True)
        with patch('qt_online_playback_ui.time.monotonic', return_value=30):
            self.assertEqual(player.gain(), 0.25)
            self.assertEqual(old.gain(), 0.75)
            player.pause_fade(False)
            self.assertEqual(player.gain(), 0.25)
            self.assertEqual(old.gain(), 0.75)

    def test_seeking_during_overlap_stops_previous_audio(self):
        player = OnlinePlayback(Mock(_state={'playing': True}))
        old = Mock()
        player.outgoing = old
        player.fade_in = 10
        player.seek(12)
        old.cancel.assert_called_once()
        self.assertIsNone(player.outgoing)
        self.assertEqual(player.gain(), 1)

    def test_short_stream_does_not_start_another_transition_during_overlap(self):
        from types import SimpleNamespace
        from qt_jukebox_ui import JukeboxBridge

        bridge = SimpleNamespace(
            model={'_stream': {'url': 'https://example.com/audio'}},
            online=SimpleNamespace(outgoing=object()),
            nextTrack=Mock(),
        )
        JukeboxBridge.normal_transition(bridge)
        bridge.nextTrack.assert_not_called()

    def test_pause_without_overlap_cannot_amplify_a_future_transition(self):
        player = OnlinePlayback(Mock(transitionSeconds=2))
        with patch('qt_online_playback_ui.time.monotonic', return_value=5):
            player.pause_fade(True)
        self.assertIsNone(player.fade_paused_at)
        player.fade_out = 10
        with patch('qt_online_playback_ui.time.monotonic', return_value=10):
            self.assertEqual(player.gain(), 1)

    def test_explicit_collection_request_is_not_cancelled_for_old_queue_head(self):
        import threading
        from types import SimpleNamespace
        from qt_jukebox_ui import JukeboxBridge

        active = threading.Event()
        bridge = SimpleNamespace(
            closed=False,
            _queue_preparing=True,
            _autoplay_entry='new-collection',
            normal_next_index=lambda: 1,
            playlist=[dict(id='current'), dict(id='old-next')],
            _prepared={},
            _queue_cancel={'new-collection': active},
        )
        JukeboxBridge.prepare_next_queued(bridge)
        self.assertFalse(active.is_set())
