"""Regression coverage for the shared playback drawer; no network or audio output."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'), 'Optional Qt desktop tests')
class PlaybackQueueDrawerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ,{'LOCALAPPDATA':self.temp.name,'ONDA_ALIAS_CACHE_ROOT':self.temp.name})
        self.env.start()
        from qt_desktop_ui import create_application
        self.app,self.engine,self.bridge=create_application(complete=False)
        self.ws=self.engine.workspace
        self.window=self.engine.rootObjects()[0]
        self.settle()
    def tearDown(self):
        from qt_desktop_ui import close_application
        close_application(self.engine,self.bridge)
        self.env.stop();self.temp.cleanup()
    def settle(self):
        from PySide6.QtCore import QEventLoop,QTimer
        loop=QEventLoop();QTimer.singleShot(80,loop.quit);loop.exec()
    def drawer(self,effects):
        from PySide6.QtCore import QObject
        return self.window.findChild(QObject,'effectsQueueDrawer' if effects else 'jukeboxQueueDrawer')
    def call(self,drawer,name,*args):
        from PySide6.QtCore import QMetaObject,Q_ARG
        self.assertTrue(QMetaObject.invokeMethod(drawer,name,*(Q_ARG('QVariant',x) for x in args)))
        self.settle()
    def seed(self):
        self.ws.setOption('effectsQueue',[{'source':f'{i}.wav','record':{'title':f'Effect {i}','artists':['Artist'],'album':'Album'},'duration':120,'cover_url':''} for i in range(3)])
        self.ws.setOption('effectsQueueIndex',1)
        self.bridge.playlist=[{'id':str(i),'title':f'Jukebox {i}','artist':'Artist','album':'Album','duration':120,'cover':'','analysis':'ready'} for i in range(3)]
        self.bridge.queue_index=1;self.bridge.queueChanged.emit();self.bridge.changed.emit()
        self.settle()
    def test_both_drawers_open_close_without_changing_tab_or_other_queue(self):
        self.seed()
        for effects in (True,False):
            key='effectsQueueOpen' if effects else 'jukeboxQueueOpen'
            drawer=self.drawer(effects)
            self.assertIsNotNone(drawer)
            original=self.ws.currentPage
            self.ws.setOption(key,True);self.settle()
            self.assertTrue(drawer.property('visible'))
            self.assertEqual(self.ws.currentPage,original)
            self.assertEqual(len(drawer.property('tracks')),3)
            from PySide6.QtCore import QMetaObject
            QMetaObject.invokeMethod(drawer,'close');self.settle()
            self.assertFalse(self.ws.values[key])
        self.assertEqual(len(self.bridge.playlist),3)
        self.assertEqual(len(self.ws.values['effectsQueue']),3)
    def test_reordering_and_removing_preserve_active_identity_and_isolation(self):
        self.seed()
        for effects in (True,False):
            drawer=self.drawer(effects)
            self.call(drawer,'move',1,-1)
            self.call(drawer,'remove',2)
            if effects:
                self.assertEqual(self.ws.values['effectsQueueIndex'],0)
                self.assertEqual(self.ws.values['effectsQueue'][0]['source'],'1.wav')
                self.assertEqual(len(self.bridge.playlist),3)
            else:
                self.assertEqual(self.bridge.queue_index,0)
                self.assertEqual(self.bridge.playlist[0]['id'],'1')
                self.assertEqual(len(self.ws.values['effectsQueue']),2)
    def test_play_routes_to_corresponding_transport(self):
        self.seed()
        with patch.object(self.ws,'play_effects_entry') as effects,patch.object(self.bridge,'playQueued') as jukebox:
            self.call(self.drawer(True),'play',2)
            effects.assert_called_once_with(2);jukebox.assert_not_called()
            self.call(self.drawer(False),'play',1)
            jukebox.assert_called_once_with(1)
    def test_clear_only_affects_selected_drawer(self):
        self.seed()
        from PySide6.QtCore import QObject,QMetaObject
        for effects in (True,False):
            button=self.drawer(effects).findChild(QObject,'clearPlaybackQueue')
            self.assertTrue(button.property('enabled'))
            self.assertTrue(QMetaObject.invokeMethod(button,'clicked'));self.settle()
            self.assertFalse(button.property('enabled'))
            self.assertEqual(len(self.bridge.playlist),3 if effects else 0)
            self.assertEqual(len(self.ws.values['effectsQueue']),0)

    def test_repeat_does_not_change_other_transport(self):
        self.seed()
        self.ws.options.update(effectsQueueIndex=2,effectsRepeat='Todas')
        with patch.object(self.ws,'play_effects_entry') as play:
            self.ws.advance_effects()
            play.assert_called_once_with(0)
        self.assertEqual(self.bridge.queueRepeat,'Desativada')
        self.ws.options.update(effectsRepeat='Desativada')
        with patch.object(self.ws,'play_effects_entry') as play:
            self.ws.advance_effects()
            play.assert_not_called()

    def test_shuffle_is_an_icon_in_each_bar_and_keeps_queues_independent(self):
        from PySide6.QtCore import QObject,QMetaObject
        fx=self.window.findChild(QObject,'effectsShuffleButton');juke=self.window.findChild(QObject,'jukeboxShuffleButton')
        for button in (fx,juke):
            self.assertIsNotNone(button);self.assertEqual(button.property('text'),'');self.assertEqual(button.property('glyph'),'shuffle')
        self.assertTrue(QMetaObject.invokeMethod(fx,'clicked'));self.settle()
        self.assertTrue(self.ws.options['effectsShuffle']);self.assertFalse(self.bridge.queueShuffle)
        self.assertTrue(QMetaObject.invokeMethod(juke,'clicked'));self.settle()
        self.assertTrue(self.bridge.queueShuffle)
        self.assertTrue(QMetaObject.invokeMethod(fx,'clicked'));self.settle()
        self.assertFalse(self.ws.options['effectsShuffle']);self.assertTrue(self.bridge.queueShuffle)

    def test_session_restores_jukebox_identity_position_and_settings_without_playing(self):
        from playback_session import save,restore
        source=Path(self.temp.name)/'music.wav';source.write_bytes(b'fixture')
        cache=Path(self.temp.name)/'analysis';cache.mkdir();(cache/'analysis.json').write_text('{}')
        self.bridge.playlist=[dict(id='missing',kind='file',source=str(source.with_name('gone.wav'))),dict(id='current',kind='file',source=str(source))]
        self.bridge.queue_index=1
        self.bridge.model=dict(cache=str(cache),title='Restored',source=str(source),beats=[0,1,2,3],neighbors=[[1],[2],[0]],links=3,duration=3)
        self.bridge._position=1;self.bridge._phase=.4;self.bridge._params=(30.,20.,75.,True)
        save(self.ws)
        self.bridge.playlist=[];self.bridge.queue_index=-1;self.bridge.model=None;self.bridge._position=0
        with patch.object(self.ws.player,'play') as effects,patch.object(self.bridge,'playPause') as juke:
            restore(self.ws);effects.assert_not_called();juke.assert_not_called()
        self.assertEqual(self.bridge.queue_index,0);self.assertEqual(self.bridge.playlist[0]['id'],'current')
        self.assertEqual(self.bridge.position,1);self.assertAlmostEqual(self.bridge.phase,.4)
        self.assertFalse(self.bridge.state['playing']);self.assertEqual(self.bridge._params,(30.,20.,75.,True))

    def test_image_gallery_remains_complete_under_history_search_filter(self):
        for name in ['first.png','second.png']:self.ws.library.add_history(Path(self.temp.name)/name,'png','https://example.com/post')
        self.ws.setOption('historyQuery','first');self.ws.refresh_history()
        row=self.ws.models['history'].rows[0]
        self.ws.dispatch('history_preview',{'id':row['id']})
        self.assertEqual([r['name'] for r in self.ws.values['imageGallery']],['first','second'])

    def test_session_restores_position_without_audio(self):
        from playback_session import save,restore
        source=Path(self.temp.name)/'music.wav';source.write_bytes(b'test')
        self.ws.options.update(effectsSource=str(source),duration=100,position=42,
                               effectsQueue=[dict(source=str(source),duration=100,record={})],effectsQueueIndex=0)
        save(self.ws)
        self.ws.options.update(effectsSource='',position=0,effectsQueue=[])
        with patch.object(self.ws.player,'play') as play,patch.object(self.bridge,'playPause') as juke:
            restore(self.ws)
            play.assert_not_called();juke.assert_not_called()
        self.assertEqual(self.ws.options['position'],42)
        self.assertEqual(self.ws.options['effectsQueueIndex'],0)
        self.assertFalse(self.ws.options['previewActive'])

    def test_image_gallery_groups_only_same_origin(self):
        for name,source in [('first.png','https://example.com/post'),('second.png','https://example.com/post'),('other.png','https://example.com/other')]:
            self.ws.library.add_history(Path(self.temp.name)/name,'png',source)
        self.ws.refresh_history()
        row=next(row for row in self.ws.models['history'].rows if row['name']=='first')
        self.ws.dispatch('history_preview',{'id':row['id']})
        self.assertEqual({r['name'] for r in self.ws.values['imageGallery']},{'first','second'})
        self.assertEqual(self.ws.values['imageGallery'][self.ws.values['imageGalleryIndex']]['name'],'first')

    def test_expired_undo_cannot_restore_removed_record(self):
        self.ws.library.add_history(Path(self.temp.name)/'old.png','png')
        row=self.ws.library.history()[0]
        self.ws.dispatch('history_remove',{'id':row['id']})
        self.assertTrue(self.ws.values['historyUndo'])
        self.ws.expire_history_undo()
        self.ws.dispatch('history_undo',{})
        self.assertEqual(self.ws.library.history(),[])
