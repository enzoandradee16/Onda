"""Regression coverage for old history migration and incremental durable queue writes."""
from contextlib import contextmanager
from pathlib import Path
import sqlite3,tempfile,unittest
from unittest.mock import patch
from library import LibraryStore

class LibraryPerformanceTests(unittest.TestCase):
    def test_indexed_queue_identity_preserves_duplicate_rules(self):
        from duplicate_links import duplicate_job,queue_duplicate_key
        one={'url':'https://youtu.be/abc','mode':'mp3','audio_quality':'320 kbps'}
        records=[one,dict(one,url='https://youtube.com/watch?v=abc&si=sharing'),dict(one,mode='flac'),dict(one,_operation='convert'),dict(one,playlist=True),dict(one,playlist_title='Album'),dict(one,image_options={'width':100,'nested':[1,True]}),dict(one,image_options={'nested':[1,1.0],'width':100.0}),dict(one,image_options={'nested':[True,1],'width':100}),dict(one,audio_quality='128 kbps')]
        for first in records:
            for second in records:
                a,b=queue_duplicate_key(first),queue_duplicate_key(second)
                self.assertEqual(duplicate_job(first,second),a is not None and a==b)

    def test_queue_writes_only_changed_positions_and_removes_tail(self):
        with tempfile.TemporaryDirectory() as folder:
            store=LibraryStore(Path(folder)/'library.db');changes=[]
            connect=store.connect
            @contextmanager
            def measured():
                with connect() as db:
                    before=db.total_changes
                    yield db
                    changes.append(db.total_changes-before)
            jobs=[dict(url=f'https://example.com/{i}',folder=folder,mode='mp3',state='Na fila') for i in range(100)]
            with patch.object(store,'connect',measured):
                store.save_queue(jobs);self.assertEqual(changes[-1],100)
                store.save_queue(jobs);self.assertEqual(changes[-1],0)
                jobs[50]['display_name']='Updated';store.save_queue(jobs);self.assertEqual(changes[-1],1)
                store.save_queue(jobs[:90]);self.assertEqual(changes[-1],10)
                self.assertEqual(len(store.load_queue()),90)
                store.save_queue([]);self.assertEqual(changes[-1],90)
                self.assertEqual(store.load_queue(),[])
    def test_failed_incremental_save_rolls_back_all_positions(self):
        with tempfile.TemporaryDirectory() as folder:
            store=LibraryStore(Path(folder)/'library.db')
            jobs=[dict(url=f'https://example.com/{i}',folder=folder,mode='mp3') for i in range(100)]
            store.save_queue(jobs)
            with store.connect() as db:
                db.execute("CREATE TRIGGER reject_update BEFORE UPDATE ON queue WHEN NEW.position=50 BEGIN SELECT RAISE(ABORT,'fixture');END")
            jobs[1]['url']='https://example.com/changed';jobs[50]['url']='https://example.com/rejected'
            with self.assertRaises(sqlite3.IntegrityError):store.save_queue(jobs)
            saved=store.load_queue()
            self.assertEqual(saved[1]['url'],'https://example.com/1')
            self.assertEqual(saved[50]['url'],'https://example.com/50')

    def test_migrates_old_history_and_uses_canonical_index(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'library.db';audio=Path(folder)/'track.mp3';audio.write_bytes(b'fixture')
            with sqlite3.connect(path) as db:
                db.execute('CREATE TABLE history(id INTEGER PRIMARY KEY,date TEXT,path TEXT,name TEXT,mode TEXT,source TEXT)')
                db.executemany('INSERT INTO history VALUES(?,?,?,?,?,?)',[(i,'date',str(audio),'Track','MP3',f'https://youtu.be/video{i}?si=old') for i in range(1200)])
            db.close()
            store=LibraryStore(path)
            for index in (0,499,500,1199):
                self.assertEqual(store.find_duplicate(f'https://www.youtube.com/watch?v=video{index}','mp3'),str(audio))
            with store.connect() as db:
                self.assertEqual(db.execute('SELECT count(*) FROM history WHERE source_key IS NOT NULL').fetchone()[0],1200)
                plan=db.execute('EXPLAIN QUERY PLAN SELECT path FROM history WHERE source_key=? AND mode_key=? ORDER BY id DESC',('youtube:video:video0','mp3')).fetchall()
                self.assertIn('history_duplicate_key',str(plan))
            self.assertEqual(set(store.history()[0]),{'id','date','path','name','mode','source'})
            self.assertEqual(LibraryStore(path).find_duplicate('https://youtu.be/video1199','mp3'),str(audio))
