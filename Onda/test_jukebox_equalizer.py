import json,math,os,tempfile,unittest
from array import array
from pathlib import Path
from jukebox_equalizer import Equalizer,clean

def tone(frequency=1000,frames=22050,left=1000,right=1000):
    data=array('h')
    for i in range(frames):
        value=math.sin(2*math.pi*frequency*i/44100)
        data.extend((round(left*value),round(right*value)))
    return data.tobytes()

def rms(pcm):
    data=array('h',pcm)[-10000:]
    return math.sqrt(sum(x*x for x in data)/len(data))

def settings(frequency=1000,gain=6,q=1.4):
    value=clean({'enabled':True,'preamp':0});value['bands'][5].update(frequency=frequency,gain=gain,q=q)
    return value

class EqualizerTests(unittest.TestCase):
    def test_disabled_and_flat_are_exact_bypass(self):
        raw=tone();eq=Equalizer();eq.configure(settings());eq.configure({'enabled':False})
        eq.process(raw) # finish the change ramp
        self.assertIs(eq.process(raw),raw)
        eq=Equalizer();eq.configure({'enabled':True,'preamp':0});self.assertIs(eq.process(raw),raw)
    def test_center_gain_and_cut_match_db(self):
        raw=tone()
        for db in (-12,6,12):
            eq=Equalizer();eq.configure(settings(gain=db))
            self.assertAlmostEqual(rms(eq.process(raw))/rms(raw),10**(db/20),delta=.015)
    def test_frequency_and_q_control_band_response(self):
        raw=tone(1500)
        def response(value):
            eq=Equalizer();eq.configure(value);return rms(eq.process(raw))/rms(raw)
        self.assertGreater(response(settings(q=.3)),response(settings(q=8))+.3)
        self.assertGreater(response(settings(frequency=1500)),response(settings(frequency=100))+.7)
    def test_stereo_channels_are_independent(self):
        eq=Equalizer();eq.configure(settings());data=array('h',eq.process(tone(right=0)))
        self.assertTrue(any(data[::2]));self.assertFalse(any(data[1::2]))
    def test_filter_state_survives_pcm_chunks(self):
        raw=tone();a=Equalizer();b=Equalizer();a.configure(settings());b.configure(settings())
        expected=a.process(raw)
        actual=b''.join(b.process(raw[i:i+4096]) for i in range(0,len(raw),4096))
        self.assertEqual(expected,actual)
    def test_preamp_and_overflow_are_bounded(self):
        eq=Equalizer();eq.configure({'enabled':True,'preamp':-12})
        raw=tone();self.assertAlmostEqual(rms(eq.process(raw))/rms(raw),10**(-12/20),delta=.002)
        eq=Equalizer();eq.configure(settings(gain=12))
        data=array('h',eq.process(tone(left=30000,right=30000)))
        self.assertEqual(max(data),32767);self.assertEqual(min(data),-32768)
    def test_setting_change_crossfades_and_finishes(self):
        eq=Equalizer();eq.configure({'enabled':False});eq.configure({'enabled':True,'preamp':-24})
        raw=array('h',[10000]*4000).tobytes();data=array('h',eq.process(raw))
        self.assertGreater(data[0],9900);self.assertAlmostEqual(data[-1],631,delta=1);self.assertIsNone(eq.transition)
    def test_invalid_settings_are_sanitized(self):
        for value in (None,False,'broken',[],{'bands':[{'frequency':float('nan'),'gain':float('inf'),'q':-1}]}):
            result=clean(value);self.assertEqual(len(result['bands']),10)
            for row in result['bands']:self.assertTrue(all(math.isfinite(v) for v in row.values()))
        result=clean({'enabled':1,'preamp':99,'bands':[{'frequency':1,'gain':99,'q':99}]})
        self.assertFalse(result['enabled']);self.assertEqual(result['preamp'],0)
        self.assertEqual(result['bands'][0],{'frequency':20,'gain':12,'q':10})
    def test_preferences_roundtrip(self):
        from preferences import PreferenceStore
        with tempfile.TemporaryDirectory() as folder:
            store=PreferenceStore(Path(folder)/'settings.json');value=settings(q=3)
            store.save({'jukebox_equalizer':json.dumps(value)})
            self.assertEqual(clean(store.load()['jukebox_equalizer']),value)
    @unittest.skipUnless(os.environ.get('ONDA_UI_TESTS'),'Tk integration')
    def test_desktop_editor_saves_ten_bands_and_restores(self):
        import tkinter as tk
        from jukebox_equalizer_ui import EqualizerWindow
        root=tk.Tk();root.withdraw();root.jukebox_equalizer=tk.StringVar(value='{}')
        try:
            dialog=EqualizerWindow(root);dialog.update_idletasks()
            self.assertEqual(len(dialog.gain_sliders),10)
            for slider in dialog.gain_sliders:
                self.assertEqual(str(slider.cget('orient')),'vertical')
                self.assertEqual(float(slider.cget('from')),12)
                self.assertEqual(float(slider.cget('to')),-12)
            dialog.enabled.set(True);f,g,q=dialog.bands[2];f.set('300');g.set(4);q.set('2,5');dialog.save()
            value=clean(root.jukebox_equalizer.get());self.assertTrue(value['enabled'])
            self.assertEqual(value['bands'][2],{'frequency':300,'gain':4,'q':2.5})
            dialog.finish();dialog=EqualizerWindow(root)
            self.assertEqual(dialog.bands[2][1].get(),4);dialog.reset()
            self.assertTrue(all(row['gain']==0 for row in clean(root.jukebox_equalizer.get())['bands']))
            dialog.finish()
        finally:root.destroy()

if __name__=='__main__':unittest.main()
