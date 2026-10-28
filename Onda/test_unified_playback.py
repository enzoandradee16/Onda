"""Shared source, original analysis, actual FFmpeg effects and one playback UI."""
import json,os,time,unittest,wave
from pathlib import Path
from unittest.mock import patch
import test_jukebox as fixtures


class CombinedAudioTests(unittest.TestCase):
    setUp=fixtures.JukeboxTests.setUp;tearDown=fixtures.JukeboxTests.tearDown
    def test_normal_crossfade_cannot_run_past_outgoing_track_end(self):
        from jukebox_stream import Stream
        from jukebox import RATE
        stream=Stream(str(self.base))
        try:
            for _ in range(31):stream.chunk(45,0,100,True)
            stream.switch(str(self.base),10)
            self.assertEqual(stream.fade_frames,RATE//4)
            frames=0
            while stream.transitioning:frames+=len(stream.chunk(45,0,100,True)['pcm'])//4
            self.assertEqual(frames,RATE//4)
        finally:stream.close()
    def test_effects_preserve_original_analysis_and_scale_audio_duration(self):
        from jukebox import Session
        player=Session(self.base)
        original=(self.base/'analysis.json').read_bytes()
        effect=dict(enabled=True,speed=85,reverb=25,keep_pitch=True)
        try:
            initial=player.chunk(45,0,100,True,effects=effect)
            self.assertTrue(initial['effects_pending'])
            deadline=time.monotonic()+30
            while player.effects.thread.is_alive() and time.monotonic()<deadline:time.sleep(.02)
            self.assertFalse(player.effects.error,player.effects.error)
            player.seek(0)
            pieces=[player.chunk(100,0,100,True,effects=effect) for _ in range(32)]
            self.assertEqual((self.base/'analysis.json').read_bytes(),original)
            self.assertAlmostEqual(sum(p['seconds'] for p in pieces),8/.85,delta=.01)
            self.assertTrue(pieces[-1]['finished']);self.assertFalse(pieces[0]['finished'])
            self.assertFalse(pieces[0]['effects_pending'])
            player.seek(4);player.story_until=0;player.since_jump=32;player.model['neighbors'][4]=[20];player._variation=None
            with patch('jukebox.loop_boundary',return_value=None),patch.object(player.random,'random',return_value=0):part=player.chunk(100,35,100,False,effects=effect)
            self.assertTrue(part['jumped']);self.assertFalse(part['finished'])
            player.seek(0);dry=player.chunk(45,0,100,True,effects=dict(enabled=False))
            self.assertIsNone(player.effect_key);self.assertAlmostEqual(dry['seconds'],.25)
        finally:
            player.close()
            if player.effects.thread:player.effects.thread.join(5)
    def test_invalid_effect_values_are_clamped_and_closed_worker_cancels(self):
        from playback_effects import clean,PreparedEffects
        self.assertEqual(clean(dict(enabled=True,speed=999,reverb=-4))['speed'],150)
        effects=PreparedEffects(self.base);effects.configure(dict(enabled=True,speed=80,reverb=20));effects.close()
        if effects.thread:effects.thread.join(10);self.assertFalse(effects.thread.is_alive())


@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'),'Qt interface')
class UnifiedDesktopTests(unittest.TestCase):
    from test_qt_workspace import NativeDesktopTests as Fixture
    setUpClass=classmethod(Fixture.setUpClass.__func__)
    setUp=Fixture.setUp;tearDown=Fixture.tearDown;settle=Fixture.settle
    def test_closing_queue_search_preserves_queue_and_open_drawer(self):
        self.ws.setOption('jukeboxQueueOpen',True)
        self.ws.setOption('jukeboxQueueResults',[dict(title='Search result')])
        self.bridge.playlist=[dict(id='kept',title='Queued song')]
        with patch.object(self.ws,'cancel_task') as cancel:
            self.ws.dispatch('playback_queue_close_search',{})
        cancel.assert_called_once_with('playback_input')
        self.assertEqual(self.ws.options['jukeboxQueueResults'],[])
        self.assertTrue(self.ws.options['jukeboxQueueOpen']);self.assertEqual(len(self.bridge.playlist),1)
    def test_manual_lyrics_offers_choices_while_automatic_keeps_best_match(self):
        self.bridge.model=dict(source='song.wav',media_title='Song',media_artist='Artist',duration=200)
        original=[(0,'Current lyric')];self.ws._jukebox_lyrics=list(original)
        with patch.object(self.ws,'run_task') as task,patch.object(self.ws,'present_choice') as chooser:
            self.ws.dispatch('lyrics_online',{})
            self.assertTrue(task.call_args.args[1]['alternatives'])
            candidate=dict(id='42',title='Other recording',lines=[(0,'Other lyric')],synced=True)
            task.call_args.args[2](dict(candidates=[candidate]))
            self.assertEqual(self.ws._jukebox_lyrics,original)
            chooser.call_args.args[2](dict(cancel=True));self.assertEqual(self.ws._jukebox_lyrics,original)
            chooser.call_args.args[2](dict(selected_id='42'));self.assertEqual(self.ws._jukebox_lyrics,candidate['lines'])
            self.ws.dispatch('lyrics_online',dict(automatic=True))
            self.assertFalse(task.call_args.args[1]['alternatives'])
    def test_generic_cache_name_never_replaces_catalog_metadata(self):
        record=dict(title='One More Time',artists=['Daft Punk'],album='Discovery',cover_url='https://example.org/cover.jpg')
        entry=dict(id='track',kind='file',source='audio.wav',title='One More Time',record=record)
        self.bridge.playlist=[entry];self.bridge.queue_index=0
        model=dict(title='audio',media_title='audio',source='audio.wav',duration=320,beats=[0,1],neighbors=[[]],links=0)
        with patch.object(self.bridge,'prepare_next_queued'):
            self.bridge.handle_event(0,'queue_prepared',dict(id='track',model=model))
        self.assertEqual(entry['title'],'One More Time');self.assertEqual(entry['cover'],record['cover_url'])
        self.bridge.handle_event(self.bridge.revision,'result',self.bridge._prepared['track'])
        self.assertEqual(self.bridge.state['title'],'One More Time');self.assertEqual(self.bridge.state['artist'],'Daft Punk')
        self.assertEqual(self.bridge.state['cover'],record['cover_url'])
        genuine=self.bridge.retain_media_metadata(dict(media_title='Different tagged edition'),entry)
        self.assertEqual(genuine['media_title'],'Different tagged edition')
    def test_both_navigation_entries_and_destinations_use_one_queue(self):
        self.ws.selectPage('effects');self.assertEqual(self.ws.currentPage,'jukebox')
        self.ws.models['catalog'].replace([dict(title='Track',artists=['Artist'],source_url='https://example.org/a')])
        with patch.object(self.bridge,'prepare_next_queued'):
            self.ws.dispatch('effects_add',dict(index=0))
        self.assertEqual(len(self.bridge.playlist),1);self.assertEqual(self.ws.options['effectsQueue'],[])
        self.ws.setOption('effectsQueueOpen',True);self.assertTrue(self.ws.options['jukeboxQueueOpen'])
        self.ws.setOption('effectsEnabled',True);self.ws.setOption('speed',90)
        self.assertTrue(self.bridge._effects['enabled']);self.assertEqual(self.bridge._effects['speed'],90)
    def test_migration_is_once_and_never_starts_audio(self):
        from playback_session import save,restore
        source=self.root/'source.wav'
        from test_jukebox import song
        song(source)
        self.ws.options.update(effectsSource=str(source),duration=8,position=2,effectsQueue=[dict(source=str(source),record=dict(title='Old effects'),duration=8)])
        save(self.ws)
        target=self.store.path.with_name('playback-session.json');data=json.loads(target.read_text());data.pop('unified');target.write_text(json.dumps(data))
        with patch.object(self.bridge,'playPause') as play:
            restore(self.ws);self.assertEqual(len(self.bridge.playlist),1);play.assert_not_called()
            save(self.ws);restore(self.ws);self.assertEqual(len(self.bridge.playlist),1)
        self.assertEqual(self.ws.options['position'],2)
    def test_unified_qml_loads_without_errors(self):
        from qt_desktop_ui import create_application,close_application
        from PySide6.QtGui import QFontDatabase
        QFontDatabase.addApplicationFont('C:/Windows/Fonts/segoeui.ttf')
        app,engine,bridge=create_application(complete=False)
        self.assertTrue(engine.rootObjects())
        warnings=[];engine.warnings.connect(lambda values:warnings.extend(v.toString() for v in values))
        try:
            engine.workspace.selectPage('effects')
            ws=engine.workspace
            bridge.setAppearance('Preto puro','Verde-Água',False)
            ws.setSetting('pure_black_separators',True)
            source=self.root/'sample.wav';fixtures.song(source)
            from PySide6.QtGui import QImage,QPainter,QColor,QFont
            from PySide6.QtCore import QBuffer,QIODevice
            cover=QImage(256,256,QImage.Format_RGB32);cover.fill(QColor('#112640'))
            painter=QPainter(cover);painter.setPen(QColor('#ddba69'));painter.drawRect(8,8,239,239);painter.setFont(QFont('Segoe UI',22,QFont.Bold));painter.drawText(30,136,'STARDUST');painter.end()
            buffer=QBuffer();buffer.open(QIODevice.WriteOnly);cover.save(buffer,'PNG')
            bridge.handle_event(bridge.revision,'result',dict(title='Music Sounds Better With You',media_title='Music Sounds Better With You',media_artist='Stardust',album='Music Sounds Better With You',source=str(source),cache=str(self.root),duration=265,beats=list(range(33)),neighbors=[[] for _ in range(32)],links=0,_cover=bytes(buffer.data())))
            ws._lyric_source=str(source);ws._jukebox_lyrics=[]
            with patch.object(bridge,'prepare_next_queued'):
                bridge.enqueueRecord(dict(title='One More Time',artists=['Daft Punk'],album='Discovery',source_url='https://example.org/one'))
                bridge.enqueueRecord(dict(title='Digital Love',artists=['Daft Punk'],album='Discovery',source_url='https://example.org/two'))
            ws.options['effectsEnabled']=True;ws.optionsChanged.emit()
            bridge.setParams(45,35,80,False)
            for _ in range(4):self.settle()
            self.assertEqual(engine.workspace.currentPage,'jukebox')
            root=engine.rootObjects()[0];root.setWidth(1550);root.setHeight(950)
            self.settle()
            output=Path(__file__).resolve().parents[1]/'Testes/auditoria-melhorias/unified-pc.png'
            root.grabWindow().save(str(output))
            def find(name):
                def walk(item):
                    if item.objectName()==name:return item
                    for child in item.childItems():
                        found=walk(child)
                        if found is not None:return found
                return walk(root.contentItem())
            from PySide6.QtTest import QTest
            from PySide6.QtCore import Qt,QPointF,QMetaObject
            from PySide6.QtCore import QObject
            equalizer=find('playbackEqualizerButton');self.assertIsNotNone(equalizer)
            self.assertEqual(equalizer.property('glyph'),'equalizer')
            QMetaObject.invokeMethod(equalizer,'clicked');self.settle()
            opened=[p for p in root.findChildren(QObject,'equalizerPopup') if p.property('opened')]
            self.assertTrue(opened)
            for popup in opened:QMetaObject.invokeMethod(popup,'close')
            self.settle()
            repeat=find('playbackRepeatButton')
            bridge.setQueueRepeat('Desativada')
            for mode in ('Todas','Uma','Desativada'):
                QMetaObject.invokeMethod(repeat,'clicked');self.settle()
                self.assertEqual(bridge.queueRepeat,mode)
                self.assertEqual(repeat.property('glyph'),'repeat-one' if mode=='Uma' else 'repeat')
            first=find('unifiedQueueTrack0');last=find('unifiedQueueTrack2')
            self.assertIsNotNone(first);self.assertIsNotNone(last)
            start=first.mapToScene(QPointF(first.width()*.7,first.height()/2)).toPoint()
            end=last.mapToScene(QPointF(last.width()*.7,last.height()/2)).toPoint()
            QTest.mousePress(root,Qt.LeftButton,Qt.NoModifier,start)
            QTest.mouseMove(root,end,40);self.settle()
            self.assertTrue(find('unifiedQueueDrag0').property('dragging'))
            self.assertNotEqual(find('unifiedQueueDrag1').property('cardOffset'),0)
            QTest.mouseRelease(root,Qt.LeftButton,Qt.NoModifier,end);self.settle()
            self.assertEqual(bridge.playlist[-1]['title'],'Music Sounds Better With You')
            self.assertEqual(bridge.queue_index,2)
            root.resize(920,720);self.settle()
            transport=find('jukeboxPlaybackControlsTransport');extras=find('unifiedPlaybackExtras')
            transport_end=transport.mapToScene(QPointF(transport.width(),0)).x()
            extras_start=extras.mapToScene(QPointF(0,0)).x()
            self.assertLessEqual(transport_end,extras_start)
            root.grabWindow().save(str(output.with_name('unified-pc-compact.png')))
            self.assertFalse([w for w in warnings if 'Error' in w],warnings)
        finally:close_application(engine,bridge)
