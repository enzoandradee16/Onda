"""The desktop adapters localize failures while retaining original diagnostics."""
import os,unittest
from i18n import set_language
from test_qt_playback_queue import PlaybackQueueDrawerTests

@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'),'Optional Qt desktop tests')
class DesktopErrorLocalizationTests(unittest.TestCase):
    def setUp(self):
        self.case=PlaybackQueueDrawerTests();self.case.setUp()
    def tearDown(self):
        self.case.tearDown();set_language('pt-BR')
    def test_task_failures_translate_but_logs_remain_original(self):
        ws=self.case.ws
        raw="PermissionError: [Errno 13] Permission denied: 'C:/Music/input.mp3'"
        for language,phrase in [('pt-BR','Permissão negada'),('es','Permiso denegado'),('en','Permission denied')]:
            set_language(language);ws.generations['effects_info']=7
            ws.on_event('task_error',{'action':'effects_info','revision':7,'error':raw})
            self.assertIn(phrase,ws.status);self.assertIn("'C:/Music/input.mp3'",ws.status)
            self.assertEqual(ws.logs[-1],raw)
            self.assertEqual(ws._status,raw)
    def test_jukebox_uses_selected_language_and_keeps_raw_reason(self):
        bridge=self.case.bridge;raw='HTTP Error 403: Forbidden'
        bridge.handle_event(bridge.revision,'error',raw)
        for language,phrase in [('pt-BR','Acesso proibido'),('es','Acceso prohibido'),('en','Forbidden')]:
            set_language(language)
            self.assertIn(phrase,bridge.state['status']);self.assertIn('403',bridge.state['status'])
            self.assertEqual(bridge._state['status'],raw)
        bridge.update_state(status='Pronta para reproduzir')
        self.assertFalse(bridge._state['status_error'])

    def test_error_result_is_a_localized_notice_not_a_json_dump(self):
        ws=self.case.ws;received=[]
        ws.message.connect(lambda title,body:received.append((title,body)))
        set_language('es');ws.show_result({'error':'HTTP Error 503: Service Unavailable'},notification=False)
        self.assertIn('Error HTTP 503: Servicio no disponible',ws.status)
        self.assertEqual(received[-1][1],'Error HTTP 503: Servicio no disponible')
        self.assertEqual(ws.logs[-1],'HTTP Error 503: Service Unavailable')
