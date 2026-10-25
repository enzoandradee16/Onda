"""Translation of raw diagnostics and preservation of diagnostic values."""
import json,unittest
from pathlib import Path
from error_localization import error_text,technical_text,rules
from i18n import tr,set_language

class ErrorLocalizationTests(unittest.TestCase):
    def tearDown(self):set_language('pt-BR')
    def test_every_diagnostic_in_all_languages(self):
        for row in rules()[0]['phrases']:
            for source in [row['en']]:
                for target in ('pt-BR','es','en'):
                    with self.subTest(source=source,target=target):
                        self.assertEqual(technical_text(source,target),row[target])
                        self.assertEqual(technical_text(row[target],target),row[target])
    def test_music_titles_are_not_treated_as_errors(self):
        for language in ("pt-BR","es","en"):
            for title in ("Forbidden","Not Found","Permission denied"):
                self.assertEqual(tr(title,language),title)
    def test_permission_error_preserves_class_code_and_path(self):
        raw="PermissionError: [Errno 13] Permission denied: '/data/user/0/br.com.onda.mobile/files/jukebox/audio.mp3'"
        for language,word in [('pt-BR','Permissão negada'),('es','Permiso denegado'),('en','Permission denied')]:
            result=error_text(raw,language)
            self.assertIn(word,result);self.assertIn('PermissionError: [Errno 13]',result)
            self.assertIn("'/data/user/0/br.com.onda.mobile/files/jukebox/audio.mp3'",result)
    def test_urls_paths_codecs_and_metadata_are_unchanged(self):
        for text in ['https://example.com/Forbidden/NotFound?error=Permission%20denied','C:\\Music\\Permission denied.mp3','/storage/emulated/0/Conversion failed.wav','Stardust · Music Sounds Better With You','libmp3lame / aac / HTTP 403 / errno=13']:
            for language in ('pt-BR','es','en'):self.assertEqual(technical_text(text,language),text)
    def test_nested_http_and_multiline_messages(self):
        raw='ERROR: [youtube] ABC: Unable to download webpage: HTTP Error 429: Too Many Requests\nhttps://example.org/video/ABC'
        es=error_text(raw,'es');self.assertIn('No se pudo descargar la página',es);self.assertIn('Error HTTP 429: Demasiadas solicitudes',es);self.assertTrue(es.endswith('https://example.org/video/ABC'))
        raw='Escolha um arquivo de áudio.\nHTTP Error 403: Forbidden'
        self.assertEqual(tr(raw,'en'),'Choose an audio file.\nHTTP Error 403: Forbidden')
    def test_unknown_errors_have_localized_explanation_and_original_details(self):
        raw='VendorUnexpectedStateException: XQ_018 at decoder.cc:57'
        for language in ('pt-BR','es','en'):
            result=error_text(raw,language)
            self.assertTrue(result.startswith(rules()[0]['unknown'][language]));self.assertIn(raw,result)
            self.assertEqual(error_text(result,language),result)
        self.assertEqual(error_text(error_text(raw,'es'),'en'),error_text(raw,'en'))
    def test_extractor_wrapper_keeps_identity_and_translates_cause(self):
        raw='ERROR: [onda:kwai] p/BUZC05Uf: '+next(key for key in __import__('i18n').catalog('en') if 'Nenhum vídeo recomendado foi baixado.' in key)
        result=error_text(raw,'en')
        self.assertTrue(result.startswith('ERROR: [onda:kwai] p/BUZC05Uf: Kwai did not find'))
        self.assertNotIn('Nenhum vídeo',result)
    def test_catalog_messages_and_dynamic_values(self):
        for language in ('pt-BR','es','en'):
            self.assertEqual(error_text('Escolha um arquivo de áudio.',language),tr('Escolha um arquivo de áudio.',language))
        self.assertEqual(tr('O servidor encerrou o download antes de completar o FLAC.','en'),'The server ended the download before the FLAC was complete.')



    def test_paths_with_spaces_unc_and_relative_paths_are_unchanged(self):
        for raw in ["'C:/Invalid argument Permission denied/Forbidden song.mp3'", '\\\\Server\\Forbidden\\Music', '.\\Forbidden', '../Permission denied/folder']:
            for language in ("pt-BR","es","en"):
                self.assertEqual(error_text(raw,language),raw)

if __name__=='__main__':unittest.main()
