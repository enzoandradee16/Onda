"""Transfer transaction checks: preparation never interrupts the origin."""

import os
import unittest
from types import SimpleNamespace
from collections import deque
from remote_control import transferable_record


class TransferRecordTests(unittest.TestCase):
    def test_reference_excludes_private_state_and_rejects_direct_sources(self):
        record = dict(
            title='Song',
            artists=['Artist'],
            album='Album',
            duration_ms=123000,
            cache='private',
            source='C:/song',
        )
        self.assertEqual(
            transferable_record(record),
            dict(title='Song', artists=['Artist'], album='Album', duration_ms=123000),
        )
        self.assertIsNone(
            transferable_record(dict(record, source_url='https://example.com'))
        )
        self.assertIsNone(transferable_record(dict(record, _jukebox_direct=True)))


@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'), 'Optional Qt handoff tests')
class TransferTransactionTests(unittest.TestCase):
    def setUp(self):
        from qt_remote_ui import RemoteControl

        class Bridge:
            def __init__(self):
                self.playlist = [
                    dict(
                        id='origin',
                        kind='catalog',
                        record=dict(title='Original', artists=['Artist']),
                    )
                ]
                self.queue_index = 0
                self.model = {}
                self.state = dict(ready=True, playing=True, paused=False)
                self._prepared = {}
                self.sourcePosition = 83.25
                self.stops = 0
                self._transport_revision = 0

            def enqueueRecords(self, records):
                self.playlist.append(
                    dict(
                        id='incoming',
                        kind='catalog',
                        record=records[0],
                        analysis='pending',
                    )
                )
                return 1

            def prepare_next_queued(self):
                pass

            def removeQueued(self, index):
                self.playlist.pop(index)

            def stop(self, reset_timer=False):
                self.stops += 1
                self.state.update(playing=False, paused=False)

            def playQueued(self, index, *, auto_play=True):
                self._transport_revision += 1
                self.queue_index = index
                self.state.update(ready=True, playing=auto_play, paused=False)
                self.sourcePosition = self.playlist[index].pop('restore_seconds', 0)

            def playPause(self):
                self._transport_revision += 1
                self.state['paused'] = not self.state['paused']

        self.bridge = Bridge()
        self.remote = SimpleNamespace(
            workspace=SimpleNamespace(bridge=self.bridge),
            _handoff={},
            _handoff_closed=deque(maxlen=128),
            _handoff_transport=0,
            _handoff_entry='',
            _handoff_origin='',
            _handoff_deadline=0,
        )
        for name in (
            'track_id',
            'handoff_command',
            'handoff_tick',
            'cancel_handoff',
            'transfer_record',
        ):
            setattr(
                self.remote, name, getattr(RemoteControl, name).__get__(self.remote)
            )

    def prepare(self):
        self.remote.handoff_command(
            'handoff_prepare',
            dict(id='test123', record=dict(title='Song', artists=['Artist'])),
        )

    def test_prepare_then_commit_preserves_position_and_never_stops_early(self):
        self.prepare()
        self.assertEqual(self.bridge.stops, 0)
        self.assertTrue(self.bridge.state['playing'])
        self.assertEqual(self.remote._handoff['status'], 'preparing')
        self.bridge._prepared['incoming'] = {}
        self.remote.handoff_tick()
        self.assertEqual(self.remote._handoff['status'], 'ready')
        self.remote.handoff_command(
            'handoff_commit', dict(id='test123', position=96.75, playing=True)
        )
        self.assertEqual(self.bridge.sourcePosition, 96.75)
        self.assertEqual(self.bridge.stops, 1)
        self.assertEqual(self.remote._handoff['status'], 'starting')
        self.remote.handoff_tick()
        self.assertEqual(self.remote._handoff['status'], 'starting')
        self.bridge.sourcePosition += 0.1
        self.remote.handoff_tick()
        self.assertEqual(self.remote._handoff['status'], 'started')
        self.remote.handoff_command('handoff_cancel', dict(id='test123'))
        self.assertTrue(self.bridge.state['paused'])

    def test_cancel_and_expiry_do_not_play_later(self):
        self.prepare()
        self.remote._handoff_deadline = 1
        self.remote.handoff_tick()
        self.assertEqual(len(self.bridge.playlist), 1)
        self.assertEqual(self.bridge.stops, 0)
        self.assertEqual(self.remote._handoff['status'], 'error')
        self.remote.handoff_command(
            'handoff_commit', dict(id='test123', position=10, playing=True)
        )
        self.assertEqual(self.bridge.stops, 0)

    def test_release_is_guarded_idempotent_and_can_be_rolled_back(self):
        self.remote.handoff_command(
            'handoff_release', dict(id='wrong', track_id='old-track')
        )
        self.assertFalse(self.bridge.state['paused'])
        self.remote.handoff_command(
            'handoff_release', dict(id='test123', track_id='origin')
        )
        self.assertTrue(self.bridge.state['paused'])
        self.assertEqual(self.remote._handoff['position'], 83.25)
        self.remote.handoff_command(
            'handoff_release', dict(id='test123', track_id='origin')
        )
        self.assertTrue(self.remote._handoff['playing'])
        self.remote.handoff_command('handoff_cancel', dict(id='test123'))
        self.assertFalse(self.bridge.state['paused'])

    def test_commit_rejects_destination_navigation_during_preparation(self):
        self.prepare()
        self.bridge._prepared['incoming'] = {}
        self.remote.handoff_tick()
        self.bridge.playlist[0]['id'] = 'changed'
        self.remote.handoff_command(
            'handoff_commit', dict(id='test123', position=10, playing=True)
        )
        self.assertEqual(self.bridge.stops, 0)
        self.assertEqual(self.remote._handoff['status'], 'error')

    def test_cancel_before_prepare_prevents_late_activation(self):
        self.remote.handoff_command('handoff_cancel', dict(id='test123'))
        self.prepare()
        self.assertEqual(len(self.bridge.playlist), 1)
        self.assertEqual(self.bridge.stops, 0)

    def test_duplicate_prepare_and_commit_do_not_add_or_restart_twice(self):
        self.prepare()
        self.prepare()
        self.assertEqual(len(self.bridge.playlist), 2)
        self.bridge._prepared['incoming'] = {}
        self.remote.handoff_tick()
        value = dict(id='test123', position=20, playing=True)
        self.remote.handoff_command('handoff_commit', value)
        self.remote.handoff_command('handoff_commit', value)
        self.assertEqual(self.bridge.stops, 1)
        self.assertEqual(self.remote._handoff['status'], 'starting')

    def test_playback_start_timeout_does_not_claim_success(self):
        self.prepare()
        self.bridge._prepared['incoming'] = {}
        self.remote.handoff_tick()
        self.remote.handoff_command(
            'handoff_commit', dict(id='test123', position=20, playing=True)
        )
        self.remote._handoff_deadline = 1
        self.remote.handoff_tick()
        self.assertEqual(self.remote._handoff['status'], 'error')
        self.assertTrue(self.bridge.state['paused'])

    def test_paused_transfer_never_opens_audio_output(self):
        self.prepare()
        self.bridge._prepared['incoming'] = {}
        self.remote.handoff_tick()
        self.remote.handoff_command(
            'handoff_commit', dict(id='test123', position=42.5, playing=False)
        )
        self.assertEqual(self.bridge.sourcePosition, 42.5)
        self.assertFalse(self.bridge.state['playing'])
        self.assertEqual(self.remote._handoff['status'], 'started')

    def test_release_lease_restores_pc_after_lost_client(self):
        self.remote.handoff_command(
            'handoff_release', dict(id='test123', track_id='origin', ack_required=True)
        )
        self.assertTrue(self.bridge.state['paused'])
        self.remote._handoff_deadline = 1
        self.remote.handoff_tick()
        self.assertFalse(self.bridge.state['paused'])
        self.assertEqual(self.remote._handoff['status'], 'error')

    def test_confirmed_release_and_late_cancel_do_not_restart_pc(self):
        self.remote.handoff_command(
            'handoff_release', dict(id='test123', track_id='origin', ack_required=True)
        )
        self.remote.handoff_command('handoff_complete', dict(id='test123'))
        self.remote._handoff_deadline = 1
        self.remote.handoff_tick()
        self.remote.handoff_command('handoff_cancel', dict(id='test123'))
        self.assertTrue(self.bridge.state['paused'])
        self.assertEqual(self.remote._handoff['status'], 'complete')

    def test_cancel_does_not_override_a_later_user_transport_action(self):
        self.remote.handoff_command(
            'handoff_release', dict(id='test123', track_id='origin', ack_required=True)
        )
        self.bridge._transport_revision += 1
        self.remote.handoff_command('handoff_cancel', dict(id='test123'))
        self.assertTrue(self.bridge.state['paused'])

    def test_second_transfer_does_not_cancel_first_in_progress(self):
        self.prepare()
        self.remote.handoff_command(
            'handoff_release', dict(id='other', track_id='origin', ack_required=True)
        )
        self.assertEqual(self.remote._handoff['id'], 'test123')
        self.assertEqual(len(self.bridge.playlist), 2)
        self.assertFalse(self.bridge.state['paused'])

    def test_old_client_without_ack_remains_compatible(self):
        self.remote.handoff_command(
            'handoff_release', dict(id='legacy', track_id='origin')
        )
        self.assertEqual(self.remote._handoff_deadline, 0)
        self.remote.handoff_tick()
        self.assertTrue(self.bridge.state['paused'])
        self.prepare()
        self.assertEqual(self.remote._handoff['id'], 'test123')

    def test_completion_does_not_overwrite_a_new_user_action(self):
        self.remote.handoff_command(
            'handoff_release', dict(id='test123', track_id='origin', ack_required=True)
        )
        self.bridge._transport_revision += 1
        self.remote.handoff_command('handoff_complete', dict(id='test123'))
        self.assertEqual(self.remote._handoff['status'], 'error')
        self.assertTrue(self.bridge.state['paused'])

    def test_cleared_cache_before_commit_does_not_stop_original_or_autoplay_later(self):
        self.prepare()
        self.bridge._prepared['incoming'] = {'cache': 'Z:/nonexistent-onda-fixture'}
        self.remote.handoff_tick()
        self.remote.handoff_command(
            'handoff_commit', dict(id='test123', position=20, playing=True)
        )
        self.assertEqual(self.bridge.stops, 0)
        self.assertEqual(len(self.bridge.playlist), 1)
        self.assertEqual(self.remote._handoff['status'], 'error')

    def test_changed_effects_reject_incompatible_prepared_stream_before_stop(self):
        self.prepare()
        self.bridge._prepared['incoming'] = {
            '_stream': {'url': 'https://example.com/audio'}
        }
        self.bridge.can_stream = lambda: False
        self.remote.handoff_tick()
        self.remote.handoff_command(
            'handoff_commit', dict(id='test123', position=20, playing=True)
        )
        self.assertEqual(self.bridge.stops, 0)
        self.assertEqual(self.remote._handoff['status'], 'error')

    def test_failed_activation_clears_delayed_autoplay(self):
        self.prepare()
        self.bridge._prepared['incoming'] = {}
        self.remote.handoff_tick()

        def stale(index, auto_play=True):
            self.bridge._autoplay_entry = 'incoming'

        self.bridge.playQueued = stale
        self.remote.handoff_command(
            'handoff_commit', dict(id='test123', position=20, playing=True)
        )
        self.assertIsNone(self.bridge._autoplay_entry)
        self.assertEqual(len(self.bridge.playlist), 1)
        self.assertEqual(self.remote._handoff['status'], 'error')
