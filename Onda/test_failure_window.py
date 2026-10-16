import os,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch

@unittest.skipUnless(os.environ.get("ONDA_UI_TESTS"),"Tk integration")
class FailureWindowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.env=patch.dict(os.environ,{"LOCALAPPDATA":self.temp.name});self.env.start()
        from app import App
        self.app=App(show_welcome=False);self.app.withdraw();self.app.folder.set(self.temp.name)
        self.window=None
    def tearDown(self):
        if self.window and self.window.winfo_exists():self.window.close()
        self.app.destroy();self.env.stop();self.temp.cleanup()
    def test_search_choose_export_and_retry_without_duplicating_jobs(self):
        from failure_ui import FailureWindow
        app=self.app;ids=app.add(lines=["https://example.com/failed","https://example.com/success"])
        app.jobs[ids[0]].update(mode="mp3",display_name="Original song",last_error="No compatible version")
        app.set_state(ids[0],"Falhou");app.set_state(ids[1],"Concluído")
        self.window=window=FailureWindow(app);window.withdraw();app.update()
        self.assertEqual(window.table.get_children(),(ids[0],))
        self.assertEqual(window.query.get(),"Original song")
        chosen=dict(source_url="https://www.deezer.com/track/123",title="Chosen song",artists=["Artist"],album="Album")
        with patch('failure_ui.MetadataClient') as client:
            client.return_value.search.return_value=[chosen]
            window.search()
            deadline=time.monotonic()+2
            while not window.results and time.monotonic()<deadline:app.update();time.sleep(.02)
        self.assertEqual(window.results,[chosen])
        window.results_table.selection_set('0');app.update();window.apply()
        self.assertEqual(app.jobs[ids[0]]['url'],chosen['source_url']);self.assertEqual(app.jobs[ids[0]]['state'],'Na fila')
        self.assertEqual(len(app.jobs),2)
        path=Path(self.temp.name)/'failures.txt'
        with patch('failure_ui.filedialog.asksaveasfilename',return_value=str(path)):window.save()
        report=path.read_text(encoding='utf-8');self.assertIn('Original song',report);self.assertIn('No compatible version',report);self.assertNotIn('https://example.com/success',report)
        with patch.object(app.parallel,'start') as start:window.retry();start.assert_called_once_with([ids[0]])
        self.assertFalse(window.winfo_exists())
    def test_footer_visible_at_minimum_size_with_long_error(self):
        from failure_ui import FailureWindow
        key=self.app.add(lines=["https://example.com/failed"])[0]
        self.app.jobs[key]['last_error']='Long error message '*1000
        self.app.set_state(key,'Falhou')
        self.window=window=FailureWindow(self.app);window.geometry('800x620');window.update()
        for widget in (window.buttons,window.use,window.results_table):
            bottom=widget.winfo_rooty()-window.winfo_rooty()+widget.winfo_height()
            self.assertLessEqual(bottom,window.winfo_height(),str(widget))
            self.assertGreater(widget.winfo_height(),15)
        self.assertIn('Long error message',window.reason_text.get('1.0','end'))
    def test_empty_successful_run_does_not_open_window(self):
        from failure_ui import show_failures
        with patch('failure_ui.FailureWindow') as window:show_failures(self.app);window.assert_not_called()

if __name__=='__main__':unittest.main()
