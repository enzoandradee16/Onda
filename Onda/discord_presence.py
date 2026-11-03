"""Opt-in Discord IPC presence; all I/O is asynchronous and uses Qt's event loop."""

import ipaddress
import json
import math
import os
import struct
import time
import uuid
from urllib.parse import urlsplit, urlunsplit

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtNetwork import QLocalSocket

APPLICATION_ID = '1567209385833537706'
MAX_FRAME = 65536


def text(value):
    return ' '.join(str(value or '').split())[:128]


def public_cover(value):
    """Never advertise local files, embedded images or authenticated URLs."""
    try:
        parsed = urlsplit(str(value or ''))
        host = parsed.hostname or ''
        if parsed.scheme != 'https' or not host or parsed.username or parsed.password:
            return ''
        if (
            host.lower() == 'localhost'
            or host.lower().endswith(('.local', '.lan', '.internal', '.localhost'))
            or '.' not in host
        ):
            return ''
        try:
            if not ipaddress.ip_address(host).is_global:
                return ''
        except ValueError:
            pass
        clean = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, '', ''))
        return clean if len(clean) <= 256 else ''
    except ValueError:
        return ''


def number(value, default=0):
    try:
        value = float(value)
        return value if math.isfinite(value) else default
    except (TypeError, ValueError):
        return default


class DiscordPresence(QObject):
    changed = Signal()

    def __init__(self, snapshot, parent=None, *, names=None, clock=time.time):
        super().__init__(parent)
        self.snapshot = snapshot
        self.clock = clock
        self.names = names or [f'discord-ipc-{n}' for n in range(10)]
        self.client_id = APPLICATION_ID
        self.enabled = False
        self.closed = False
        self.status = 'Desativado'
        self.socket = None
        self.ready = False
        self.buffer = bytearray()
        self.index = 0
        self.last_activity = None
        self.last_sent = -math.inf
        self.anchor = None
        self.pending_nonce = None
        self.refresh = QTimer(self)
        self.refresh.setInterval(1000)
        self.refresh.timeout.connect(self.publish)
        self.retry = QTimer(self)
        self.retry.setSingleShot(True)
        self.retry.setInterval(10000)
        self.retry.timeout.connect(self.connect)
        self.timeout = QTimer(self)
        self.timeout.setSingleShot(True)
        self.timeout.setInterval(3000)
        self.timeout.timeout.connect(self.failed)

    def set_status(self, value):
        if self.status != value:
            self.status = value
            self.changed.emit()

    def configure(self, enabled, client_id=APPLICATION_ID):
        enabled = enabled is True and not self.closed
        if enabled == self.enabled and client_id == self.client_id:
            return
        self.disable()
        self.client_id = client_id
        self.enabled = enabled
        if enabled:
            if (
                not str(client_id).isascii()
                or not str(client_id).isdigit()
                or not 17 <= len(str(client_id)) <= 20
            ):
                self.set_status('ID do aplicativo Discord inválido.')
                return
            self.refresh.start()
            self.connect()

    def disable(self):
        self.enabled = False
        self.refresh.stop()
        self.retry.stop()
        self.timeout.stop()
        if self.socket:
            if self.ready:
                self.write(1, self.command(None))
                self.socket.flush()
            self.release_socket(graceful=True)
        self.anchor = None
        self.set_status('Desativado')

    def close(self):
        self.disable()
        self.closed = True

    def release_socket(self, graceful=False):
        sock, self.socket = self.socket, None
        self.ready = False
        self.pending_nonce = None
        self.buffer.clear()
        self.last_activity = None
        self.last_sent = -math.inf
        if sock:
            sock.blockSignals(True)
            if graceful:
                sock.disconnectFromServer()
            else:
                sock.abort()
            sock.deleteLater()

    def connect(self):
        if not self.enabled or self.closed or self.socket:
            return
        self.index = 0
        self.set_status('Conectando ao Discord…')
        self.next_pipe()

    def next_pipe(self):
        if not self.enabled or self.closed:
            return
        self.timeout.stop()
        self.release_socket()
        if self.index >= len(self.names):
            self.set_status('Abra o Discord neste computador para mostrar a atividade.')
            self.retry.start()
            return
        name = self.names[self.index]
        self.index += 1
        sock = QLocalSocket(self)
        self.socket = sock
        sock.setReadBufferSize(MAX_FRAME + 8)
        sock.connected.connect(lambda: self.connected(sock))
        sock.readyRead.connect(lambda: self.receive(sock))
        sock.errorOccurred.connect(lambda _: self.socket_failed(sock))
        sock.disconnected.connect(lambda: self.socket_failed(sock))
        self.timeout.start()
        sock.connectToServer(name)

    def socket_failed(self, sock):
        if sock is self.socket:
            self.failed()

    def failed(self):
        self.timeout.stop()
        if not self.enabled or self.closed:
            return
        if not self.ready:
            self.release_socket()
            QTimer.singleShot(
                0, lambda: self.next_pipe() if self.socket is None else None
            )
        else:
            self.release_socket()
            self.set_status('Reconectando ao Discord…')
            self.retry.start()

    def connected(self, sock):
        if sock is self.socket:
            self.write(0, {'v': 1, 'client_id': self.client_id})

    def write(self, opcode, payload):
        if not self.socket:
            return
        data = json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode(
            'utf-8'
        )
        self.socket.write(struct.pack('<II', opcode, len(data)) + data)

    def command(self, activity):
        return {
            'cmd': 'SET_ACTIVITY',
            'args': {'pid': os.getpid(), 'activity': activity},
            'nonce': uuid.uuid4().hex,
        }

    def receive(self, sock):
        if sock is not self.socket:
            return
        self.buffer.extend(bytes(sock.readAll()))
        while len(self.buffer) >= 8:
            opcode, length = struct.unpack('<II', self.buffer[:8])
            if length > MAX_FRAME:
                self.failed()
                return
            if len(self.buffer) < length + 8:
                return
            raw = bytes(self.buffer[8 : 8 + length])
            del self.buffer[: 8 + length]
            try:
                payload = json.loads(raw.decode('utf-8'))
                if not isinstance(payload, dict):
                    raise ValueError('Invalid IPC frame')
            except (ValueError, UnicodeError):
                self.failed()
                return
            if opcode == 3:
                self.write(4, payload)
            elif opcode == 2 or payload.get('evt') == 'ERROR':
                self.release_socket()
                self.timeout.stop()
                self.set_status(
                    'Discord recusou a atividade. Verifique o ID do aplicativo.'
                )
                self.retry.start()
                return
            elif opcode == 1 and payload.get('evt') == 'READY':
                self.ready = True
                self.timeout.stop()
                self.set_status('Conectado ao Discord')
                self.publish()
            elif opcode == 1 and payload.get('nonce') == self.pending_nonce:
                self.pending_nonce = None
                self.timeout.stop()

    def activity(self):
        state = self.snapshot()
        if not state.get('playing') or not text(state.get('title')):
            self.anchor = None
            return None
        now = self.clock()
        duration = max(0, number(state.get('duration')))
        position = max(0, number(state.get('position')))
        if duration:
            position = min(position, duration)
        rate = min(4, max(0.1, number(state.get('speed'), 1)))
        identity = (
            state.get('track_id'),
            text(state.get('title')),
            text(state.get('artist')),
            duration,
            rate,
        )
        activity = {'type': 2, 'details': text(state['title'])}
        artist = text(state.get('artist'))
        if artist:
            activity['state'] = artist
        cover = public_cover(state.get('cover_url'))
        if cover:
            activity['assets'] = {
                'large_image': cover,
                'large_text': text(state.get('album')) or activity['details'],
            }
        if state.get('paused'):
            self.anchor = None
            activity['state'] = text(state.get('paused_label') or 'Pausado') + (
                f' · {artist}' if artist else ''
            )
            activity['state'] = text(activity['state'])
        elif duration:
            old = self.anchor
            if (
                old is None
                or old[0] != identity
                or abs(position - (old[1] + (now - old[2]) * rate)) > 2
            ):
                self.anchor = (identity, position, now)
            _, start_position, start_time = self.anchor
            start = int(start_time - start_position / rate)
            activity['timestamps'] = {
                'start': start,
                'end': start + max(1, int(duration / rate)),
            }
        return activity

    def publish(self):
        if not self.enabled or self.closed or not self.ready:
            return
        activity = self.activity()
        if self.pending_nonce and activity is not None:
            return
        now = time.monotonic()
        if activity == self.last_activity:
            return
        # A stop/opt-out clears immediately. Other changes coalesce to one per 5s.
        if activity is not None and now - self.last_sent < 5:
            return
        command = self.command(activity)
        self.pending_nonce = command['nonce']
        self.write(1, command)
        self.last_activity = activity
        self.last_sent = now
        self.timeout.start()
