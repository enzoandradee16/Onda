import os
from pathlib import Path
import unittest
from unittest.mock import Mock,patch


@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'),'Qt interface')
class ToolPresentationTests(unittest.TestCase):
    from test_qt_workspace import NativeDesktopTests as Fixture
    setUpClass=classmethod(Fixture.setUpClass.__func__)
    setUp=Fixture.setUp;tearDown=Fixture.tearDown;settle=Fixture.settle

    def test_compact_cards_and_details_fit_all_themes(self):
        from PySide6.QtCore import QObject,QMetaObject
        from PySide6.QtGui import QFontDatabase
        from qt_desktop_ui import create_application,close_application
        from tool_status import display
        QFontDatabase.addApplicationFont('C:/Windows/Fonts/segoeui.ttf')
        app,engine,bridge=create_application(complete=False)
        ws=engine.workspace;root=engine.rootObjects()[0];root.setWidth(1360);root.setHeight(900)
        warnings=[];engine.warnings.connect(lambda values:warnings.extend(v.toString() for v in values))
        report=display(dict(checked_at='2026-10-27T23:38:29+00:00',updated_at='2026-10-27T23:40:00+00:00',restart_required=True,update_state='Atualização concluída',tools=[
            dict(name=name,version='ffmpeg version 9.0.2-essentials_build Copyright (c) developers' if name=='ffmpeg' else '1.2.3',status='Disponível')
            for name in ('Python','yt-dlp','gallery-dl','Pillow','Mutagen','ffmpeg','ffprobe','ffplay','Node.js')]))
        def find(name):
            def walk(item):
                if item.objectName()==name:return item
                for child in item.childItems():
                    found=walk(child)
                    if found is not None:return found
            return walk(root.contentItem())
        try:
            with patch.object(ws,'run_task'):
                ws.setOption('toolReport',report)
                popup=root.findChild(QObject,'settingsPopup');self.assertIsNotNone(popup)
                popup.setProperty('category','Ferramentas');QMetaObject.invokeMethod(popup,'open')
                for _ in range(5):self.settle()
                panel=find('toolStatusReport');grid=find('toolStatusGrid');raw=find('toolRawDetails')
                self.assertIsNotNone(panel);self.assertFalse(raw.property('visible'))
                self.assertEqual(find('toolVersion_ffmpeg').property('text'),'9.0.2')
                self.assertTrue(find('restartAfterToolsCheck').property('visible'))
                with patch.object(ws,'run_task'):
                    ws.tasks['verify_tools']=Mock();ws.statusChanged.emit();self.settle()
                    self.assertFalse(find('restartAfterToolsCheck').property('enabled'))
                    ws.tasks.clear();ws.statusChanged.emit();self.settle()
                self.assertGreaterEqual(grid.property('columns'),2)
                for theme in ('Claro','Preto puro','Alto contraste'):
                    ws.setSetting('theme_mode',theme)
                    for _ in range(4):self.settle()
                    self.assertLessEqual(grid.width(),panel.width()+1)
                    self.assertGreater(panel.width(),500)
                    output=Path(__file__).resolve().parents[1]/'Testes/auditoria-tools-visual'
                    output.mkdir(parents=True,exist_ok=True)
                    root.grabWindow().save(str(output/(theme.replace(' ','-')+'.png')))
                panel.setProperty('expanded',True);self.settle();self.assertTrue(raw.property('visible'))
                self.assertIn('Copyright',raw.property('text'))
                ws.setSetting('interface_font_size','130%')
                for _ in range(4):self.settle()
                self.assertEqual(grid.property('columns'),2)
                self.assertLessEqual(grid.width(),panel.width()+1)
            self.assertFalse(warnings,'\n'.join(warnings))
        finally:close_application(engine,bridge)
