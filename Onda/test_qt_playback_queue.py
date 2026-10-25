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
