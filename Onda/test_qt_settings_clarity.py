"""Targeted settings checks; no network search or personal profile."""

import os
import unittest


@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'), 'Optional Qt desktop tests')
class SettingsClarityTests(unittest.TestCase):
    def setUp(self):
        from test_qt_playback_queue import PlaybackQueueDrawerTests
        self.case = PlaybackQueueDrawerTests()
        self.case.setUp()
        self.workspace = self.case.ws

    def tearDown(self):
        self.case.tearDown()

    def test_pure_light_and_metadata_choices_are_independent(self):
        fields = {field['key']: field for field in self.workspace.settingsFields}
        self.assertIn('Claro puro', fields['theme_mode']['choices'])
        self.workspace.setSetting('theme_mode', 'Claro puro')
        self.assertEqual(self.workspace.preferences['theme_mode'], 'Claro puro')
        self.workspace.setSetting('auto_metadata', True)
        self.workspace.setSetting('review_metadata', True)
        self.workspace.setSetting('auto_match', False)
        self.assertTrue(self.workspace.preferences['auto_metadata'])
        self.assertTrue(self.workspace.preferences['review_metadata'])
        self.assertFalse(self.workspace.preferences['auto_match'])
        for key in ('auto_metadata', 'auto_match', 'review_metadata', 'resume_downloads', 'resume_queue', 'duplicates', 'detect_duplicates'):
            self.assertTrue(fields[key]['hint'], key)

    def test_action_groups_fit_and_cache_has_one_location(self):
        from PySide6.QtCore import QObject, QMetaObject
        root = self.case.window
        root.setWidth(1100)
        root.setHeight(900)
        popup = root.findChild(QObject, 'settingsPopup')
        QMetaObject.invokeMethod(popup, 'open')
        popup.setProperty('category', 'Ferramentas')
        self.case.settle()
        group = root.findChild(QObject, 'settingsToolActions')
        actions = {item.property('operation'): item for item in group.childItems()
                   if item.metaObject().indexOfProperty('operation') >= 0}
        verify = actions['verify_tools']
        update = actions['update_tools']
        self.assertTrue(verify.property('visible'))
        self.assertAlmostEqual(verify.property('width'), update.property('width'), delta=1)
        self.assertFalse(root.findChild(QObject, 'cache_clear').property('visible'))
        popup.setProperty('category', 'Desempenho')
        self.case.settle()
        self.assertTrue(root.findChild(QObject, 'cache_clear').property('visible'))
        self.assertFalse(verify.property('visible'))
        popup.setProperty('category', 'Geral')
        self.case.settle()
        self.assertEqual(len(root.findChildren(QObject, 'settingsRestoreButton')), 1)
        self.assertIsNone(root.findChild(QObject, 'restore_settings'))
        popup.setProperty('category', 'Contas')
        self.case.settle()
        accounts = root.findChild(QObject, 'settingsAccountActions')
        widths = [item.property('width') for item in accounts.childItems()
                  if item.metaObject().indexOfProperty('text') >= 0 and item.property('visible')]
        self.assertGreaterEqual(len(widths), 4)
        self.assertAlmostEqual(max(widths), min(widths), delta=1)

    def test_language_choice_shows_restart_only_for_unapplied_language(self):
        from PySide6.QtCore import QObject, QMetaObject, Q_ARG
        popup = self.case.window.findChild(QObject, 'settingsPopup')
        QMetaObject.invokeMethod(popup, 'open')
        self.case.settle()
        def find(item, name):
            if item.objectName() == name:
                return item
            for child in item.childItems():
                result = find(child, name)
                if result is not None:
                    return result
        field = find(popup.property('contentItem'), 'settingField_language')
        choice = find(field, 'settingsLanguageChoice')
        button = find(field, 'restartAfterLanguageChange')
        self.assertFalse(button.property('visible'))
        QMetaObject.invokeMethod(choice, 'activated', Q_ARG(int, 2))
        self.case.settle()
        self.assertEqual(self.workspace.settings['language'], 'en')
        self.assertTrue(button.property('visible'))
        self.assertEqual(button.property('text'), 'Reiniciar ONDA')
        self.assertGreaterEqual(button.property('y'), choice.property('y') + choice.property('height'))
        QMetaObject.invokeMethod(choice, 'activated', Q_ARG(int, 0))
        self.case.settle()
        self.assertFalse(button.property('visible'))
        self.assertFalse(self.workspace.languageRestartRequired)
        self.assertNotEqual(self.workspace._status, 'Reinicie o ONDA para aplicar o idioma.')
