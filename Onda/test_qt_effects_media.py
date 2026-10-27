"""System media commands follow the audible player, independently of the page."""
import os,queue,unittest
from types import SimpleNamespace
from unittest.mock import Mock,patch
import test_qt_workspace as fixture


@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'),'Optional Qt desktop tests')
class EffectsMediaTests(unittest.TestCase):
    setUpClass=classmethod(fixture.NativeDesktopTests.setUpClass.__func__)
    tearDown=fixture.NativeDesktopTests.tearDown
    def setUp(self):
        fixture.NativeDesktopTests.setUp(self)
        self.ws.player.close()
        self.player=Mock(active=False);self.player.messages.return_value=[];self.player.position_snapshot.return_value=42
        self.player.play.side_effect=lambda *a,**k:setattr(self.player,'active',True)
        self.player.stop.side_effect=lambda:setattr(self.player,'active',False)
        self.ws.player=self.player
        self.media=SimpleNamespace(events=queue.SimpleQueue(),update=Mock(),navigation=Mock(),close=Mock())
        self.bridge.media=self.media
        self.ws.options.update(effectsSource='song.wav',duration=120,effectsRecord={'title':'Effects song','artists':['Artist']},effectsCover='cover',effectsQueue=[{},{}],effectsQueueIndex=0)
    def send(self,button):self.media.events.put(button);self.bridge.sync_media()
    def test_effects_play_registers_media_and_pause_resume_preserves_position(self):
        with patch.object(self.bridge,'playPause') as jukebox:
            self.ws.dispatch('effects_play_pause',{})
            self.assertTrue(self.bridge.media_timer.isActive());self.assertEqual(self.ws.media_owner,'effects')
            self.assertEqual(self.media.update.call_args.args,('Effects song','Artist',True,False,'cover'))
            self.send(1);self.assertTrue(self.ws.options['effectsPaused']);self.assertFalse(self.player.active);self.assertEqual(self.ws.options['position'],42)
            self.assertEqual(self.media.update.call_args.args[2:4],(True,True));self.assertTrue(self.bridge.media_timer.isActive())
            self.send(0);self.assertTrue(self.player.active);self.assertFalse(self.ws.options['effectsPaused']);self.assertEqual(self.player.play.call_args.kwargs['start'],42)
            jukebox.assert_not_called()
    def test_stop_resets_only_effects(self):
        self.ws.dispatch('effects_play_pause',{})
        with patch.object(self.bridge,'stop') as stop:
            self.send(2);stop.assert_not_called()
        self.assertFalse(self.player.active);self.assertEqual(self.ws.options['position'],0)
        self.assertEqual(self.media.update.call_args.args[2:4],(False,False));self.assertFalse(self.bridge.media_timer.isActive())
    def test_next_previous_use_effects_queue(self):
        self.ws.dispatch('effects_play_pause',{});self.ws.options['effectsQueueIndex']=1
        with patch.object(self.ws,'advance_effects') as next_track,patch.object(self.ws,'play_effects_entry') as previous,patch.object(self.bridge,'nextTrack') as jukebox:
            self.send(6);self.send(7)
            next_track.assert_called_once();previous.assert_called_once_with(0);jukebox.assert_not_called()
    def test_media_owner_does_not_follow_the_visible_tab(self):
        self.ws.dispatch('effects_play_pause',{});self.ws.selectPage('catalog')
        self.assertEqual(self.ws.effects_media_state()['owner'],'effects')
        self.send(1);self.assertTrue(self.ws.options['effectsPaused'])
    def test_switching_to_jukebox_routes_commands_back_and_keeps_effects_position(self):
        self.ws.dispatch('effects_play_pause',{})
        self.bridge.playbackRequested.emit();self.bridge._state.update(playing=True,paused=False,title='Jukebox song')
        self.assertTrue(self.ws.options['effectsPaused']);self.assertEqual(self.ws.options['position'],42)
        with patch.object(self.bridge,'playPause') as toggle:
            self.send(1);toggle.assert_called_once()
        self.assertEqual(self.media.update.call_args.args[0],'Jukebox song');self.assertFalse(self.player.active)
    def test_jukebox_navigation_remains_available(self):
        self.bridge._state.update(playing=True,paused=False)
        with patch.object(self.bridge,'nextTrack') as next_track,patch.object(self.bridge,'previousTrack') as previous:
            self.send(6);self.send(7);next_track.assert_called_once();previous.assert_called_once()
    def test_windows_navigation_flags_use_correct_native_slots_and_skip_duplicates(self):
        from windows_media import MediaControls
        controls=object.__new__(MediaControls);controls.controls=object();calls=[]
        def native(pointer,index,*types):
            def call(*args):calls.append((index,args[-1]));return 0
            return call
        with patch('windows_media.method',side_effect=native):
            controls.navigation(True,False);controls.navigation(True,False)
        self.assertEqual(calls,[(25,True),(27,False)])
