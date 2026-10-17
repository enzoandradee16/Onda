import os,tempfile,unittest
from unittest.mock import patch,Mock
from pathlib import Path
from advanced_options import DEFAULTS,export_settings,import_settings
from preferences import PreferenceStore

class AutoSelectionTests(unittest.TestCase):
    def test_default_and_preference_roundtrip(self):
        self.assertTrue(DEFAULTS['auto_select_media'])
        with tempfile.TemporaryDirectory() as root:
            store=PreferenceStore(Path(root)/'prefs.json');store.save({'auto_select_media':False})
            self.assertFalse(store.load()['auto_select_media'])
        payload=export_settings({'auto_select_media':False},'android')
        self.assertFalse(import_settings(payload,'windows')['auto_select_media'])
    def test_two_photos_offer_individual_selection_and_keep_only_selected(self):
        from social_media import download_selected
        for enabled in (True,False):
            items=[('https://cdn.test/1.jpg',{'extension':'jpg'}),('https://cdn.test/2.jpg',{'extension':'jpg'})]
            chooser=Mock(return_value={'selected_ids':['2']})
            with patch('social_media.save_media',return_value='chosen.jpg') as save:
                self.assertEqual(download_selected(items,None,{'url':'https://instagram.com/p/x','mode':'social','auto_select_media':enabled},Mock(),Mock(),chooser),['chosen.jpg'])
                save.assert_called_once();self.assertEqual(save.call_args.args[1],'https://cdn.test/2.jpg')
                self.assertTrue(all(row['auto_select_media']==enabled for row in chooser.call_args.args[0]))

@unittest.skipUnless(os.environ.get('ONDA_UI_TESTS'),'Tk integration')
class PickerTests(unittest.TestCase):
    def test_toggle_individual_selection_disabled_confirmation_and_opt_out(self):
        import tkinter as tk
        from media_picker import MediaPicker
        root=tk.Tk();root.withdraw();root.social_cookies=tk.StringVar(value='')
        try:
            for enabled in (True,False):
                items=[{'id':str(i),'number':i,'kind':'Foto','title':'Photo','auto_select_media':enabled} for i in (1,2)]
                confirm=Mock();picker=MediaPicker(root,{'candidates':items},confirm,Mock());picker.update()
                try:
                    self.assertEqual(picker.selected(),['1','2'] if enabled else [])
                    self.assertEqual(picker.select_all_button.cget('text'),'Desmarcar todas' if enabled else 'Selecionar todas')
                    picker.select_all(True);picker.variables['1'].set(False);picker.changed()
                    self.assertEqual(picker.select_all_button.cget('text'),'Selecionar todas')
                    picker.accept();confirm.assert_called_once_with(['2'])
                    picker.select_all_button.invoke();self.assertEqual(picker.selected(),['1','2'])
                    picker.select_all_button.invoke();self.assertEqual(picker.selected(),[])
                    self.assertEqual(str(picker.download_button.cget('state')),'disabled')
                finally:picker.destroy()
        finally:root.destroy()
