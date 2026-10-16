import unittest
from unittest.mock import patch
from parallel_queue import ParallelQueue

class Value:
    def __init__(self,value):self.value=value
    def get(self):return self.value
    def set(self,value):self.value=value

class Button:
    def configure(self,**_):pass

class Event:
    def clear(self):pass
    def is_set(self):return False

class Tree:
    def __init__(self,app):self.app=app
    def get_children(self):return tuple(self.app.jobs)

class App:
    def __init__(self,limit):
        self.concurrent_downloads=Value(limit)
        self.jobs={key:{'state':'Na fila'} for key in ('first','second','unrequested')}
        self.tree=Tree(self)
        self.ffmpeg=self.social_cookies=self.spotify_client_id=self.spotify_client_secret=Value('')
        self.auto_metadata=Value(False)
        self.auto_match=self.resume_downloads=Value(False)
        self.cancelled=Event();self.start_button=self.cancel_button=Button()
        self.closing=False;self.running=False;self.messages=[]
        self.status=Value("");self.detail=Value("");self.progress=None
    def supervise(self,*_):pass
    def set_progress(self,value):self.progress=value
    def set_state(self,key,state):self.jobs[key]['state']=state
    def write_log(self,message):self.messages.append(message)
    def refresh_queue(self):pass
    def persist_queue(self):pass

class DynamicDownloadsTests(unittest.TestCase):
    def test_workers_receive_live_automatic_metadata_preference(self):
        app=App(1);app.auto_metadata.set(True)
        scheduler=ParallelQueue(app)
        with patch('parallel_queue.threading.Thread') as thread:
            scheduler.start(('first',))
        self.assertTrue(thread.call_args.kwargs['args'][1]['auto_metadata'])
        self.assertTrue(thread.call_args.kwargs['args'][1]['_cleanup_work'])

    def test_high_concurrency_is_saved_and_bounded_to_fifteen(self):
        from advanced_options import clean_advanced
        for limit in (10,15):
            self.assertEqual(clean_advanced({'concurrent_downloads':str(limit)}),
                             {'concurrent_downloads':str(limit)})
        self.assertNotIn('concurrent_downloads',clean_advanced({'concurrent_downloads':'16'}))
        app=App(15)
        app.jobs={str(i):{'state':'Na fila'} for i in range(20)}
        scheduler=ParallelQueue(app)
        with patch('parallel_queue.threading.Thread'):
            scheduler.start(None)
        self.assertEqual(len(scheduler.workers),15)
        self.assertEqual(sum(job['state']=='Na fila' for job in app.jobs.values()),5)

    def test_second_immediate_starts_while_first_is_active(self):
        app=App(2);scheduler=ParallelQueue(app)
        with patch('parallel_queue.threading.Thread'):
            scheduler.start(('first',))
            scheduler.extend(('second',))
        self.assertEqual(scheduler.workers,{'first','second'})
        self.assertEqual(app.jobs['unrequested']['state'],'Na fila')

    def test_limit_one_keeps_second_until_current_finishes(self):
        app=App(1);scheduler=ParallelQueue(app)
        with patch('parallel_queue.threading.Thread'):
            scheduler.start(('first',))
            scheduler.extend(('second',))
            self.assertEqual(scheduler.workers,{'first'})
            self.assertEqual(app.jobs['second']['state'],'Na fila')
            scheduler.finish('first',{'success':True,'cancelled':False})
        self.assertEqual(scheduler.workers,{'second'})
        self.assertEqual(app.jobs['first']['state'],'Concluído')
        self.assertEqual(app.jobs['unrequested']['state'],'Na fila')

    def test_repeated_request_does_not_restart_active_item(self):
        app=App(2);scheduler=ParallelQueue(app)
        with patch('parallel_queue.threading.Thread') as thread:
            scheduler.start(('first',))
            scheduler.extend(('first',))
        self.assertEqual(thread.call_count,1)

    def test_new_request_observes_changed_limit(self):
        app=App(1);scheduler=ParallelQueue(app)
        with patch('parallel_queue.threading.Thread'):
            scheduler.start(('first',))
            app.concurrent_downloads.value=2
            scheduler.extend(('second',))
        self.assertEqual(scheduler.workers,{'first','second'})

    def test_last_completion_stops_progress_and_finalizes_queue(self):
        app=App(1);scheduler=ParallelQueue(app)
        with patch('parallel_queue.threading.Thread'):
            scheduler.start(('first',))
            scheduler.finish('first',{'success':True,'cancelled':False})
        self.assertFalse(app.running)
        self.assertEqual(app.progress,100)
        self.assertEqual(app.status.get(),'Fila finalizada')

    def test_global_queue_keeps_accepting_new_requests(self):
        app=App(2);scheduler=ParallelQueue(app)
        with patch('parallel_queue.threading.Thread'):
            scheduler.start(None)
            scheduler.extend(('second',))
        self.assertIsNone(scheduler.scope)
        self.assertEqual(len(scheduler.workers),2)

if __name__=='__main__':unittest.main()
