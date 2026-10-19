"""Real Windows SMTC lifecycle; no keyboard injection or audible playback."""
import ctypes as c
import os,unittest

@unittest.skipUnless(os.name=='nt' and os.environ.get('ONDA_UI_TESTS'),'Windows UI integration')
class WindowsMediaTests(unittest.TestCase):
    def test_native_status_metadata_and_cleanup(self):
        import tkinter as tk
        from windows_media import MediaControls,method,checked
        root=tk.Tk();root.update();controls=None
        try:
            controls=MediaControls(root)
            for playing,paused,expected in ((True,False,3),(True,True,4),(False,False,2)):
                controls.update('ONDA — silent test','Test artist',playing,paused)
                state=c.c_int();checked(method(controls.controls,6,c.POINTER(c.c_int))(controls.controls,c.byref(state)))
                self.assertEqual(state.value,expected)
            # Exercise the COM delegate with an artificial ButtonPressed argument.
            getter=c.WINFUNCTYPE(c.c_long,c.c_void_p,c.POINTER(c.c_int))(lambda this,out: (setattr(out.contents,'value',1) or 0))
            table=(c.c_void_p*7)(*([None]*6+[c.cast(getter,c.c_void_p)]))
            class Args(c.Structure):_fields_=[('table',c.POINTER(c.c_void_p))]
            args=Args(table)
            self.assertEqual(controls.callbacks[3](c.byref(controls.delegate),None,c.byref(args)),0)
            self.assertEqual(controls.events.get_nowait(),1)
            controls.close();self.assertFalse(controls.controls)
        finally:
            if controls:controls.close()
            root.destroy()
