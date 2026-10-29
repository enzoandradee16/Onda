"""Qt desktop shell, native workspaces and the QML Jukebox."""

from pathlib import Path
import os
import sys

if os.name == 'nt':
    os.environ.setdefault(
        'QT_QUICK_BACKEND', os.environ.get('ONDA_QT_BACKEND', 'software')
    )
_style_initialized = False
ROOT = Path(__file__).resolve().parent
for packages in (ROOT.parent / '_runtime/qt', ROOT.parent / '.venv/qt-packages'):
    if packages.is_dir():
        sys.path.insert(0, str(packages))
        break


def create_application(*, complete=True):
    global _style_initialized
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QGuiApplication, QIcon, QImage, QPixmap
    from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType
    from PySide6.QtQuickControls2 import QQuickStyle
    from qt_graph_ui import BeatGraph
    from qt_jukebox_ui import JukeboxBridge

    os.environ.setdefault('ONDA_DOWNLOADS', str(Path.home() / 'Downloads/Onda'))
    from ffmpeg_runtime import existing_folder

    folder = existing_folder()
    os.environ['PATH'] = os.pathsep.join(
        filter(
            None,
            [
                str(folder) if folder else '',
                str(
                    next(
                        (
                            p
                            for p in (
                                ROOT.parent / '_runtime/node',
                                ROOT.parent / 'Portatil/_runtime/node',
                            )
                            if p.is_dir()
                        ),
                        ROOT.parent / '_runtime/node',
                    )
                ),
                os.environ.get('PATH', ''),
            ],
        )
    )
    if os.name == 'nt':
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('Onda.Desktop')
    from PySide6.QtWidgets import QApplication

    if not _style_initialized:
        QQuickStyle.setStyle('Basic')
        _style_initialized = True
    app = QGuiApplication.instance() or QApplication(sys.argv[:1])
    app.setApplicationName('ONDA · Qt')
    app.setOrganizationName('ONDA')
    from interface_fonts import register_qt_fonts

    register_qt_fonts()
    qmlRegisterType(BeatGraph, 'Onda', 1, 0, 'BeatGraph')
    from qt_workspace_ui import DesktopWorkspace
    from PySide6.QtCore import QTimer

    engine = QQmlApplicationEngine(parent=app)
    from qt_platform_icons_ui import PlatformIcons

    engine.addImageProvider("platform", PlatformIcons())
    from qt_backdrop_ui import PlaybackBackdrop

    engine.addImageProvider("backdrop", PlaybackBackdrop())
    bridge = JukeboxBridge(parent=engine)
    workspace = DesktopWorkspace(bridge, parent=engine)
    engine.workspace = workspace
    engine.rootContext().setContextProperty('bridge', bridge)
    engine.rootContext().setContextProperty('workspace', workspace)

    def refresh_icon():
        from window_icons import draw_icon
        from PySide6.QtGui import QFont
        from interface_fonts import qt_font_family, DEFAULT_FONT

        font = QFont(
            qt_font_family(bridge.preferences.get('interface_font', DEFAULT_FONT))
        )
        if font.family() == 'Inter':
            font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        app.setFont(font)
        picture = draw_icon('onda', 64, bridge.palette)
        qimage = QImage(
            picture.tobytes('raw', 'RGBA'), 64, 64, QImage.Format.Format_RGBA8888
        ).copy()
        icon = QIcon(QPixmap.fromImage(qimage))
        app.setWindowIcon(icon)
        for window in engine.rootObjects():
            window.setIcon(icon)
        if workspace.tray:
            workspace.tray.setIcon(icon)

    refresh_icon()
    bridge.appearanceChanged.connect(refresh_icon)
    warnings = []
    engine.warnings.connect(
        lambda rows: warnings.extend(row.toString() for row in rows)
    )
    engine.load(QUrl.fromLocalFile(str(ROOT / 'qml/Main.qml')))
    if not engine.rootObjects():
        raise RuntimeError('\n'.join(warnings))
    bridge.window = engine.rootObjects()[0]
    workspace.attach(bridge.window)
    if complete:
        QTimer.singleShot(0, workspace.start)
    app.aboutToQuit.connect(workspace.shutdown)
    app.aboutToQuit.connect(bridge.shutdown)
    return app, engine, bridge


def close_application(engine, bridge):
    from PySide6.QtCore import QCoreApplication, QEvent

    engine.workspace.shutdown()
    bridge.shutdown()
    for window in engine.rootObjects():
        window.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    engine.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def packaged_self_test(target):
    """Exercise the actual launcher/runtime without network or personal settings."""
    import json, tempfile
    from PySide6.QtCore import QTimer

    report = {'ok': False, 'backend': os.environ.get('QT_QUICK_BACKEND', 'default')}
    with tempfile.TemporaryDirectory(prefix='onda-qt-test-') as temporary:
        previous = {
            key: os.environ.get(key)
            for key in ('LOCALAPPDATA', 'ONDA_ALIAS_CACHE_ROOT')
        }
        os.environ['LOCALAPPDATA'] = temporary
        os.environ['ONDA_ALIAS_CACHE_ROOT'] = temporary
        try:
            app, engine, bridge = create_application(complete=False)
            try:
                QTimer.singleShot(0, engine.workspace.restore)
                QTimer.singleShot(400, app.quit)
                code = app.exec()
                window = engine.rootObjects()[0]
                report.update(
                    ok=code == 0 and window.isVisible(),
                    width=window.width(),
                    height=window.height(),
                )
            finally:
                close_application(engine, bridge)
        except Exception as error:
            report['error'] = str(error)
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
    Path(target).write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8'
    )
    return 0 if report['ok'] else 1


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--qt-self-test":
        return packaged_self_test(sys.argv[2])
    from single_instance import SingleInstance
    from PySide6.QtCore import QTimer

    with SingleInstance() as guard:
        if not guard.primary:
            guard.notify()
            return 0
        while True:
            app, engine, bridge = create_application()
            workspace = engine.workspace
            workspace.prepare_tools = True
            QTimer.singleShot(0, workspace.restore)
            activation = QTimer()
            activation.setInterval(150)
            activation.timeout.connect(
                lambda: workspace.restore() if guard.activation_requested() else None
            )
            activation.start()
            try:
                code = app.exec()
            finally:
                activation.stop()
                restart = workspace.restart_requested
                close_application(engine, bridge)
            if not restart:
                return code


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception:
        import traceback

        log = (
            Path(os.environ.get('LOCALAPPDATA', str(ROOT)))
            / 'Onda/qt-startup-error.log'
        )
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(traceback.format_exc(), encoding='utf-8')
        if os.name == 'nt':
            import ctypes

            ctypes.windll.user32.MessageBoxW(
                None,
                'Não foi possível abrir o ONDA. Detalhes: ' + str(log),
                'ONDA',
                0x10,
            )
        raise
