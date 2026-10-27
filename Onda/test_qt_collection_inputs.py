"""Controller/UI coverage for collection controls and player input isolation."""
import os,unittest
from unittest.mock import Mock,patch
import test_qt_workspace as fixture


@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'),'Optional Qt desktop tests')
class CollectionInputTests(unittest.TestCase):
    setUpClass=classmethod(fixture.NativeDesktopTests.setUpClass.__func__)
    setUp=fixture.NativeDesktopTests.setUp
    tearDown=fixture.NativeDesktopTests.tearDown
    settle=fixture.NativeDesktopTests.settle

    def test_effects_destination_adds_selected_catalog_track_without_opening_or_playing(self):
        record={'title':'Selected','artists':['Artist'],'source_url':'https://example.com/selected'}
        self.ws.models['catalog'].replace([record]);self.ws.options['effectsResults']=[dict(record,title='Different search')]
        self.ws.setOption('effectsQueueOpen',False);self.ws.selectPage('catalog')
        with patch.object(self.ws,'run_task') as task,patch.object(self.ws,'accept_files') as accept,patch.object(self.ws,'play_effects_entry') as play:
            self.ws.dispatch('effects_add',{'index':0})
            self.assertEqual(task.call_args.args[1]['record']['title'],'Selected')
            task.call_args.args[2]({'source':'cached.wav','record':record})
            accept.assert_called_once_with('effects_queue',['cached.wav']);play.assert_not_called()
        self.assertEqual(self.ws.effects_catalog_records['cached.wav'],record)
        self.assertFalse(self.ws.options['effectsQueueOpen']);self.assertEqual(self.ws.currentPage,'catalog')

    def test_playlist_card_actions_use_playlist_record(self):
        catalog={'title':'Catalog','source_url':'https://example.com/catalog','artists':[]}
        playlist={'title':'Playlist','source_url':'https://example.com/playlist','artists':[]}
        self.ws.models['catalog'].replace([catalog]);self.ws.models['playlists'].replace([playlist])
        with patch.object(self.ws,'choose_download_format') as download:
            self.ws.dispatch('catalog_download',{'model':'playlists','index':0})
        self.assertEqual(download.call_args.args[0]['source_url'],playlist['source_url'])
        self.ws.selectPage('playlists')
        with patch.object(self.ws,'enqueue') as enqueue:
            self.ws.dispatch('catalog_add',{'model':'playlists','index':0})
        self.assertEqual(enqueue.call_args.args[0],[playlist['source_url']]);self.assertEqual(self.ws.currentPage,'playlists')

    def test_sidebar_collection_keeps_current_page_and_drawer_state(self):
        rows=[{'title':'A','source_url':'https://example.com/a'},{'title':'B','source_url':'https://example.com/b'}]
        self.ws.selectPage('catalog');self.ws.setOption('jukeboxQueueOpen',False)
        with patch.object(self.ws,'run_task') as task,patch.object(self.bridge,'enqueueRecord') as enqueue:
            self.ws.dispatch('playback_queue_search',{'effects':False,'query':'collection'})
            task.call_args.args[2]({'is_collection':True,'tracks':rows})
        self.assertEqual(enqueue.call_count,2);self.assertEqual(self.ws.currentPage,'catalog');self.assertFalse(self.ws.options['jukeboxQueueOpen'])

    def test_effects_sidebar_add_keeps_actual_download_metadata_and_stays_closed(self):
        record={'title':'URL','source_url':'https://example.com/a'}
        self.ws.setOption('effectsQueueResults',[record]);self.ws.setOption('effectsQueueOpen',False)
        with patch.object(self.ws,'run_task') as task,patch.object(self.ws,'accept_files') as accept:
            self.ws.dispatch('playback_queue_add',{'effects':True,'index':0})
            task.call_args.args[2]({'source':'cached.wav','record':dict(record,title='Actual song')})
        self.assertEqual(self.ws.effects_catalog_records['cached.wav']['title'],'Actual song');accept.assert_called_once_with('effects_queue',['cached.wav']);self.assertFalse(self.ws.options['effectsQueueOpen'])

    def test_metadata_callback_matches_url_after_rows_reorder(self):
        original={'title':'A','artists':[],'source_url':'https://www.deezer.com/track/1','checked':True}
        other={'title':'B','artists':[],'source_url':'https://www.deezer.com/track/2','checked':False}
        self.ws.models['playlists'].replace([original,other]);self.ws.dispatch('request_card_details',{'model':'playlists','source':original['source_url']})
        with patch.object(self.ws,'run_task') as task:
            self.ws.flush_card_details();self.ws.models['playlists'].replace([other,original])
            task.call_args.args[2]([{'model':'playlists','source':original['source_url'],'record':dict(original,cover_url='cover',release_date='1998-07-20',_details_checked=True)}])
        rows=self.ws.models['playlists'].rows;self.assertNotIn('cover_url',rows[0]);self.assertEqual(rows[1]['cover_url'],'cover');self.assertTrue(rows[1]['checked'])

    def test_qml_views_load_without_errors_and_collection_button_tracks_state(self):
        from qt_desktop_ui import create_application,close_application
        from PySide6.QtCore import QObject
        from PySide6.QtQuick import QQuickItem
        app,engine,bridge=create_application(complete=False);ws=engine.workspace;warnings=[]
        engine.warnings.connect(lambda rows:warnings.extend(row.toString() for row in rows))
        def find(name):
            def walk(item):
                if item.objectName()==name:return item
                for child in item.childItems():
                    result=walk(child)
                    if result is not None:return result
            return walk(engine.rootObjects()[0].contentItem())
        try:
            ws.selectPage('playlists');self.settle();button=find('libraryLoadButton');self.assertIsNotNone(button);self.assertEqual(button.property('text'),'Carregar')
            ws.setOption('playlistUrl','https://example.com/list');ws.collection_loaded({'title':'Album','_collection_url':'https://example.com/list','tracks':[]});self.settle();self.assertEqual(button.property('text'),'Atualizar')
            ws.tasks['collection']=Mock();ws.statusChanged.emit();self.settle();self.assertEqual(button.property('text'),'Cancelar');ws.tasks.clear();ws.statusChanged.emit()
            for page in ('effects','jukebox','converter','images','metadata','catalog','history','downloads','queue'):
                ws.selectPage(page);self.settle()
            self.assertFalse(warnings,'\n'.join(warnings))
        finally:close_application(engine,bridge)

