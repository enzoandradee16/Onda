import os,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from queue_control import sorted_keys,replace_pending,storage_report,estimated_bytes,observe

def job(title,duration=None,state='Na fila'):
    return {'url':'https://example.com/'+title,'display_name':title,'state':state,'mode':'mp3','audio_quality':'320 kbps','queue_info':{'duration_ms':duration},'folder':'.'}

class QueuePolicyTests(unittest.TestCase):
    def test_sort_missing_last_and_protect_active_slots(self):
        jobs={'a':job('Z',10000),'busy':job('Active',5000,'Em andamento'),'b':job('B',3000),'unknown':job('A')}
        order=sorted_keys(['a','b','unknown'],jobs,'Maior duração')
        self.assertEqual(order,['a','b','unknown'])
        self.assertEqual(sorted_keys(['a','b','unknown'],jobs,'Menor duração'),['b','a','unknown'])
        self.assertEqual(replace_pending(list(jobs),jobs,['unknown','b','a']),['unknown','busy','b','a'])
        for index,key in enumerate(jobs):jobs[key]['queue_original']=index
        self.assertEqual(sorted_keys(['b','a'],jobs,'Ordem original'),['a','b'])

    def test_storage_unknown_and_same_volume_margin(self):
        with patch('queue_control.shutil.disk_usage',return_value=SimpleNamespace(free=1)):
            report=storage_report([job('one',10000),job('two',10000),job('unknown')],2)
        size=estimated_bytes(job('one',10000))
        self.assertEqual(report,(size*2,1,size*6,True))
        self.assertIsNone(estimated_bytes(dict(job('list',10000),playlist=True)))
        self.assertIsNone(estimated_bytes(dict(job('flac',10000),mode='flac')))

    def test_activity_records_each_workers_events(self):
        app=SimpleNamespace(jobs={'a':job('A',state='Em andamento'),'b':job('B',state='Em andamento')},tree=SimpleNamespace(set=lambda *args:None),parallel=SimpleNamespace(memory_wait=None))
        observe(app,'a',{'type':'stage','message':'Consultando metadados da música…'})
        observe(app,'b',{'type':'processing'})
        self.assertEqual(app.jobs['a']['_queue_activity'],'Consultando metadados da música…')
        self.assertEqual(app.jobs['b']['_queue_activity'],'Convertendo arquivo…')
        observe(app,'a',{'type':'choose_version'})
        self.assertEqual(app.jobs['a']['_queue_activity'],'Aguardando sua escolha')

@unittest.skipUnless(os.environ.get('ONDA_UI_TESTS'),'Tk integration')
class QueueControlUiTests(unittest.TestCase):
    def test_filters_drag_arrows_persistence_and_space_confirmation(self):
        from app import App
        with tempfile.TemporaryDirectory() as root,patch.dict(os.environ,{'LOCALAPPDATA':root}):
            app=App(show_welcome=False);app.clipboard_watch.shutdown();app.folder.set(root)
            try:
                a=app.add(lines=['https://example.com/a'],overrides={'mode':'mp3','audio_quality':'320 kbps','display_name':'Z','queue_info':{'duration_ms':10000}})[0]
                b=app.add(lines=['https://example.com/b'],overrides={'mode':'mp3','audio_quality':'320 kbps','display_name':'B','queue_info':{'duration_ms':3000}})[0]
                c=app.add(lines=['https://example.com/c'],overrides={'mode':'mp3','audio_quality':'320 kbps','display_name':'A'})[0]
                ctl=app.queue_control;ctl.order.set('Título');ctl.sort()
                self.assertEqual(app.tree.get_children(),(c,b,a))
                ctl.order.set('Ordem original');ctl.sort();self.assertEqual(app.tree.get_children(),(a,b,c))
                app.set_state(b,'Em andamento');ctl.move_before(c,a)
                self.assertEqual(app.tree.get_children(),(c,b,a))
                app.queue_filter.query.set('Z');app.update()
                self.assertEqual(app.queue_filter.visible_keys(),(a,))
                app.tree.selection_set(a);ctl.move_selection(-1)
                self.assertEqual(app.tree.get_children(),(a,b,c))
                self.assertEqual([row['url'] for row in app.library.load_queue()],[app.jobs[k]['url'] for k in (a,b,c)])
                app.set_state(b,'Na fila')
                with patch('queue_control.shutil.disk_usage',return_value=SimpleNamespace(free=1)),patch('tkinter.messagebox.askyesno',return_value=False) as question:
                    self.assertFalse(ctl.confirm(None));question.assert_called_once()
                    self.assertFalse(ctl.confirm(None,scheduled=True));question.assert_called_once()
                app.queue_filter.clear();app.queue_view.set('Completa');app.update()
                self.assertEqual(len(app.queue_cards.rows),3)
                self.assertTrue(any(getattr(widget,'cget',lambda key:'')('text')=='↕' for widget in app.queue_cards.rows[a][0].winfo_children() if 'text' in widget.keys()))
                ctl.order.set('Menor tamanho estimado');ctl.sort();self.assertEqual(app.tree.get_children(),(b,a,c))
                with patch('parallel_queue.threading.Thread') as worker:
                    app.parallel.start(None)
                    self.assertEqual(worker.call_args.kwargs['args'][0],b)
                app.parallel.workers.clear();app.running=False
            finally:app.destroy()
