"""Isolated desktop Instagram sign-in; no access to installed browser profiles."""

from pathlib import Path
from PySide6.QtCore import QObject, QProcess


class InstagramSession(QObject):
    def __init__(self, workspace):
        super().__init__(workspace)
        self.workspace = workspace
        self.root = workspace.store.path.parent / 'instagram-browser'
        self.cookies = self.root / 'instagram-session.dpapi'
        self.process = QProcess(self)
        self.process.finished.connect(self.finished)
        self.process.errorOccurred.connect(self.failed)
        self.action = ''

    def launch(self, disconnect=False):
        if self.process.state() != QProcess.NotRunning:
            self.workspace.notify('A janela do Instagram já está aberta.')
            return
        helper = Path(__file__).resolve().parent.parent / '_runtime/browser-session/InstagramSession.exe'
        if not helper.is_file():
            helper = Path(__file__).resolve().parent.parent / 'Portatil/_runtime/browser-session/InstagramSession.exe'
        if not helper.is_file():
            raise ValueError('O componente de conexão do Instagram não está instalado neste pacote.')
        self.root.mkdir(parents=True, exist_ok=True)
        self.action = 'disconnect' if disconnect else 'connect'
        palette = self.workspace.bridge.palette
        self.process.start(str(helper), [
            str(self.root), self.workspace.settings.get('language', 'pt-BR'),
            palette['surface'], palette['text'], palette['accent'], self.action,
        ])

    def finished(self, code, status):
        if status != QProcess.NormalExit or code != 0:
            return
        if self.action == 'disconnect':
            self.cookies.unlink(missing_ok=True)
            self.workspace.setSetting('instagram_cookies', '')
            self.workspace.notify('Instagram desconectado.')
        elif self.cookies.is_file():
            self.workspace.setSetting('instagram_cookies', str(self.cookies))
            self.workspace.notify('Sessão do Instagram salva. Tente baixar o vídeo novamente.')

    def failed(self, error):
        if error == QProcess.FailedToStart:
            self.workspace.message.emit('Instagram', 'Não foi possível abrir a janela do Instagram.')

    def close(self):
        if self.process.state() != QProcess.NotRunning:
            self.process.kill()
            self.process.waitForFinished(1000)
