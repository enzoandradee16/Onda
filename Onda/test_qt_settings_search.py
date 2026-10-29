"""Settings results retain their category and support localized, accent-free queries."""

import json, os, unittest
from pathlib import Path
from i18n import set_language
from settings_search_index import matches


class SettingsSearchIndexTests(unittest.TestCase):
    def test_notification_aliases_and_categories_in_three_languages(self):
        fields = json.loads(
            (Path(__file__).parent / 'settings_schema/desktop.json').read_text(
                encoding='utf-8'
            )
        )['fields']
        for language, query in [
            ('pt-BR', 'notificacoes'),
            ('en', 'notifications'),
            ('es', 'notificaciones'),
        ]:
            found = {
                f['key']: f['category'] for f in fields if matches(query, f, language)
            }
            self.assertEqual(found['notice_duration'], 'Geral')
            self.assertEqual(found['notice_animation'], 'Geral')
            self.assertEqual(found['notifications_enabled'], 'Geral')
            self.assertEqual(found['finish_action'], 'Downloads')
        self.assertTrue(
            matches(
                'downloads simultaneos',
                next(f for f in fields if f['key'] == 'concurrent_downloads'),
                'pt-BR',
            )
        )
        self.assertFalse(
            any(matches('configuracao inexistente xyz', f, 'pt-BR') for f in fields)
        )


@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'), 'Optional Qt desktop tests')
class SettingsSearchLocationTests(unittest.TestCase):
    def setUp(self):
        import test_qt_playback_queue as queue_tests

        self.case = queue_tests.PlaybackQueueDrawerTests()
        self.case.setUp()
        from PySide6.QtCore import QObject, QMetaObject

        self.popup = self.case.window.findChild(QObject, 'settingsPopup')
        self.search = self.popup.findChild(QObject, 'settingsSearch')
        QMetaObject.invokeMethod(self.popup, 'open')
        self.case.settle()

    def tearDown(self):
        self.case.tearDown()
        set_language('pt-BR')

    def item(self, name):
        def walk(item):
            if item.objectName() == name:
                return item
            return next(
                (
                    result
                    for child in item.childItems()
                    if (result := walk(child)) is not None
                ),
                None,
            )

        return walk(self.popup.property('contentItem'))

    def test_similar_results_show_distinct_real_categories_and_open_them(self):
        from PySide6.QtCore import QMetaObject

        self.search.setProperty('text', 'SIM')
        self.case.settle()
        appearance = self.item('settingCategory_simple_download_ui')
        downloads = self.item('settingCategory_concurrent_downloads')
        self.assertTrue(appearance.property('visible'))
        self.assertTrue(downloads.property('visible'))
        self.assertEqual(appearance.property('text'), 'Configurações › Aparência')
        self.assertEqual(downloads.property('text'), 'Configurações › Downloads')
        QMetaObject.invokeMethod(appearance, 'clicked')
        self.case.settle()
        self.assertEqual(self.popup.property('category'), 'Aparência')
        self.assertEqual(self.search.property('text'), '')
        self.assertFalse(appearance.property('visible'))
        self.assertTrue(
            self.item('settingField_simple_download_ui').property('visible')
        )

    def test_notification_search_and_no_results_state(self):
        self.search.setProperty('text', 'notificacoes')
        self.case.settle()
        for key in [
            'notice_duration',
            'notice_animation',
            'notifications_enabled',
            'finish_action',
        ]:
            self.assertTrue(self.item('settingField_' + key).property('visible'), key)
        self.search.setProperty('text', 'inexistente_xyz')
        self.case.settle()
        self.assertTrue(self.item('settingsSearchEmpty').property('visible'))
        self.assertEqual(self.popup.property('resultCount'), 0)
