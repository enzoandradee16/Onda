import array
import math
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import wave
from audio_tools import effects_filter


class KeepPitchFilterTests(unittest.TestCase):
    def test_independent_speed_and_reverb_filters(self):
        self.assertEqual(effects_filter(75,0,True),'atempo=0.75')
        self.assertEqual(effects_filter(125,0,True),'atempo=1.25')
        self.assertEqual(effects_filter(100,0,True),'anull')
        self.assertIn('asetrate=36000',effects_filter(75,0))
        self.assertNotIn('asetrate',effects_filter(75,30,True))
        self.assertIn('aecho',effects_filter(75,30,True))
        with self.assertRaises(ValueError):effects_filter(75,0,'yes')

    def test_rendered_duration_changes_but_pitch_is_preserved(self):
        from effects_worker import render
        from audio_tools import executable
        folder=os.environ.get('ONDA_FFMPEG','')
        try:executable('ffmpeg',folder)
        except ValueError:self.skipTest('FFmpeg required')
        with tempfile.TemporaryDirectory() as temporary:
            source=Path(temporary)/'tone.wav'
            rate=48000
            samples=array.array('h',(round(14000*math.sin(2*math.pi*440*i/rate)) for i in range(2*rate)))
            with wave.open(str(source),'wb') as output:
                output.setnchannels(1);output.setsampwidth(2);output.setframerate(rate);output.writeframes(samples.tobytes())
            for speed,keep_pitch in ((75,True),(125,True),(75,False),(125,False)):
                target=Path(temporary)/f'{speed}-{keep_pitch}.wav'
                with patch('effects_worker.emit'):
                    self.assertEqual(render({'source':str(source),'output':str(target),'speed':speed,'reverb':0,'keep_pitch':keep_pitch,'ffmpeg':folder}),0)
                with wave.open(str(target),'rb') as output:
                    duration=output.getnframes()/output.getframerate()
                    self.assertAlmostEqual(duration,2/(speed/100),delta=.12)
                    output.setpos(int(.2*output.getframerate()))
                    audio=array.array('h',output.readframes(int(output.getframerate())))
                crossings=sum(a<=0<b for a,b in zip(audio,audio[1:]))
                self.assertAlmostEqual(crossings,440 if keep_pitch else 440*speed/100,delta=6)


@unittest.skipUnless(os.environ.get('ONDA_UI_TESTS'),'Tk integration')
class KeepPitchUiTests(unittest.TestCase):
    def test_preview_export_persistence_and_reset(self):
        from app import App
        from reset_settings import apply_defaults
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'LOCALAPPDATA':folder}):
            app=App(show_welcome=False)
            try:
                source=Path(folder)/'music.wav';source.write_bytes(b'test')
                pane=app.effects_page.ensure_ready().effects
                pane.source.set(str(source));pane.speed.set(75);pane.reverb.set(0)
                pane.keep_pitch.set(True)
                with patch.object(pane.player,'play') as play:
                    pane.preview()
                    self.assertTrue(play.call_args.kwargs['keep_pitch'])
                    pane.preview(False)
                    self.assertFalse(play.call_args.kwargs['keep_pitch'])
                with patch('effects_ui.filedialog.asksaveasfilename',return_value=str(Path(folder)/'out.wav')),patch.object(pane,'render') as render:
                    pane.mode.set('WAV');pane.export()
                    import time
                    for _ in range(100):
                        if render.called:break
                        time.sleep(.005)
                    self.assertTrue(render.call_args.args[0]['keep_pitch'])
                pane.busy=False
                app.remember_settings.set(True);app.persist_preferences()
                app.destroy()
                app=App(show_welcome=False)
                self.assertTrue(app.effects_page.keep_pitch.get())
                apply_defaults(app,{'effects_keep_pitch'})
                self.assertFalse(app.effects_page.keep_pitch.get())
            finally:app.destroy()
