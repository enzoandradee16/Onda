"""Opt-in LAN remote control. HTTP workers never access the player or Qt."""

import copy
import hmac
import ipaddress
import json
import math
import queue
import secrets
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

NETWORKS = tuple(
    ipaddress.ip_network(value)
    for value in ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16', '127.0.0.0/8')
)


class LocalHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, *args):
        self.slots = threading.BoundedSemaphore(8)
        super().__init__(*args)

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()


def local_address(value):
    try:
        address = ipaddress.ip_address(value)
        return any(address in network for network in NETWORKS)
    except ValueError:
        return False


def lan_addresses():
    addresses = set()
    try:
        addresses.update(socket.gethostbyname_ex(socket.gethostname())[2])
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(('192.0.2.1', 9))
            addresses.add(probe.getsockname()[0])
    except OSError:
        pass
    return sorted(a for a in addresses if local_address(a) and not a.startswith('127.'))


class RemoteServer:
    def __init__(self, host='0.0.0.0', port=0):
        self.code = f'{secrets.randbelow(1000000):06d}'
        self.token = secrets.token_urlsafe(32)
        self.commands = queue.Queue(maxsize=32)
        self.lock = threading.Lock()
        self.snapshot = {'ready': False, 'playing': False, 'title': '', 'volume': 80}
        self.attempts = []
        self.paired = False
        self.name = socket.gethostname()[:80] or 'ONDA PC'
        self.discovery = None
        self.discoverable = host == '0.0.0.0'
        self.queue_rows = []
        self.queue_revision = 0
        self.artwork = b''
        self.artwork_id = ''
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def setup(self):
                super().setup()
                self.connection.settimeout(3)

            def log_message(self, *args):
                pass  # Never log pairing codes or credentials.

            def reply(self, code, value):
                data = json.dumps(value, ensure_ascii=False, allow_nan=False).encode()
                self.send_response(code)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(data)))
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Connection', 'close')
                self.end_headers()
                self.wfile.write(data)
                self.close_connection = True

            def allowed(self):
                if not local_address(self.client_address[0]) or self.headers.get(
                    'Origin'
                ):
                    self.reply(
                        403,
                        {
                            'error': 'Acesso permitido apenas pelo aplicativo na rede local.'
                        },
                    )
                    return False
                return True

            def authorized(self):
                if not self.allowed():
                    return False
                value = self.headers.get('Authorization', '')
                if not owner.paired or not hmac.compare_digest(
                    value.encode(), ('Bearer ' + owner.token).encode()
                ):
                    self.reply(
                        401, {'error': 'Conecte novamente com o código exibido no PC.'}
                    )
                    return False
                return True

            def do_GET(self):
                if not self.authorized():
                    return
                url = urlsplit(self.path)
                query = parse_qs(url.query)
                if url.path == '/v1/queue':
                    try:
                        offset = int(query.get('offset', ['0'])[0])
                        if not 0 <= offset <= 5000:
                            raise ValueError()
                    except ValueError:
                        self.reply(400, {'error': 'Pedido inválido.'})
                        return
                    with owner.lock:
                        page = dict(
                            rows=copy.deepcopy(owner.queue_rows[offset : offset + 100]),
                            total=len(owner.queue_rows),
                            revision=owner.queue_revision,
                            offset=offset,
                        )
                    self.reply(200, page)
                    return
                if url.path == '/v1/artwork':
                    with owner.lock:
                        data = (
                            owner.artwork
                            if query.get('id', [''])[0] == owner.artwork_id
                            else b''
                        )
                    if not data:
                        self.reply(404, {'error': 'Recurso indisponível.'})
                        return
                    self.send_response(200)
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', str(len(data)))
                    self.send_header('Cache-Control', 'no-store')
                    self.send_header('Connection', 'close')
                    self.end_headers()
                    self.wfile.write(data)
                    return
                if url.path != '/v1/state':
                    self.reply(404, {'error': 'Recurso indisponível.'})
                    return
                with owner.lock:
                    state = copy.deepcopy(owner.snapshot)
                self.reply(200, state)

            def do_POST(self):
                if self.path == '/v1/pair':
                    if not self.allowed():
                        return
                elif not self.authorized():
                    return
                try:
                    length = int(self.headers.get('Content-Length', '0'))
                    if not 0 < length <= 4096:
                        raise ValueError()
                    if self.headers.get_content_type() != 'application/json':
                        raise ValueError()
                    value = json.loads(self.rfile.read(length))
                    if not isinstance(value, dict):
                        raise ValueError()
                except (ValueError, OSError):
                    self.reply(400, {'error': 'Pedido inválido.'})
                    return
                if self.path == '/v1/pair':
                    with owner.lock:
                        now = time.monotonic()
                        owner.attempts = [t for t in owner.attempts if now - t < 60]
                        if len(owner.attempts) >= 5:
                            self.reply(
                                429,
                                {
                                    'error': 'Aguarde um minuto antes de tentar novamente.'
                                },
                            )
                            return
                        owner.attempts.append(now)
                        supplied = value.get('code', '')
                        if not isinstance(supplied, str) or not hmac.compare_digest(
                            supplied.encode(), owner.code.encode()
                        ):
                            self.reply(401, {'error': 'Código incorreto.'})
                            return
                        owner.paired = True
                    self.reply(
                        200,
                        {
                            'token': owner.token,
                            'name': owner.name,
                            'protocol': 1,
                            'features': 3,
                        },
                    )
                    return
                if self.path != '/v1/command':
                    self.reply(404, {'error': 'Recurso indisponível.'})
                    return
                command = value.get('command')
                if command not in (
                    'toggle',
                    'play',
                    'pause',
                    'next',
                    'previous',
                    'volume',
                    'seek',
                    'queue_play',
                    'queue_remove',
                    'queue_move',
                    'shuffle',
                    'repeat',
                    'effects',
                    'jukebox',
                    'search',
                    'search_cancel',
                    'search_add',
                    'queue_clear',
                    'queue_move_to',
                ):
                    self.reply(400, {'error': 'Comando indisponível.'})
                    return
                if command == 'volume':
                    volume = value.get('value')
                    if type(volume) is not int or not 0 <= volume <= 100:
                        self.reply(400, {'error': 'Volume inválido.'})
                        return
                payload = value.get('value')
                if command in ('effects', 'jukebox'):
                    fields = (
                        {
                            'enabled': bool,
                            'speed': (50, 150),
                            'reverb': (0, 100),
                            'keep_pitch': bool,
                        }
                        if command == 'effects'
                        else {'variation': (0, 100), 'smooth': (0, 100), 'normal': bool}
                    )
                    if not valid_adjustments(payload, fields):
                        self.reply(400, {'error': 'Pedido inválido.'})
                        return
                if command in ('search', 'search_add') and (
                    not isinstance(payload, str)
                    or not payload.strip()
                    or len(payload) > (500 if command == 'search' else 128)
                ):
                    self.reply(400, {'error': 'Pedido inválido.'})
                    return
                if (command == 'shuffle' and type(payload) is not bool) or (
                    command == 'repeat'
                    and payload not in ('Desativada', 'Todas', 'Uma')
                ):
                    self.reply(400, {'error': 'Pedido inválido.'})
                    return
                if command in (
                    'seek',
                    'queue_play',
                    'queue_remove',
                    'queue_move',
                    'queue_move_to',
                ):
                    identity = value.get('track_id')
                    if not isinstance(identity, str) or not 0 < len(identity) <= 128:
                        self.reply(400, {'error': 'Pedido inválido.'})
                        return
                    if command == 'seek' and (
                        type(payload) not in (int, float)
                        or not math.isfinite(payload)
                        or not 0 <= payload <= 86400
                    ):
                        self.reply(400, {'error': 'Pedido inválido.'})
                        return
                    if command == 'queue_move' and (
                        type(payload) is not int or payload not in (-1, 1)
                    ):
                        self.reply(400, {'error': 'Pedido inválido.'})
                        return
                    if command == 'queue_move_to' and (
                        not isinstance(payload, str) or not 0 < len(payload) <= 128
                    ):
                        self.reply(400, {'error': 'Pedido inválido.'})
                        return
                    payload = dict(track_id=identity, value=payload)
                try:
                    owner.commands.put_nowait((command, payload))
                except queue.Full:
                    self.reply(429, {'error': 'Aguarde o comando anterior.'})
                    return
                self.reply(202, {'accepted': True})

        self.http = LocalHTTPServer((host, port), Handler)
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)

    @property
    def port(self):
        return self.http.server_port

    def start(self):
        self.thread.start()
        if self.discoverable:
            from remote_discovery import DiscoveryResponder

            try:
                self.discovery = DiscoveryResponder(self.port, self.name)
            except OSError:
                pass  # Manual pairing remains available if discovery is blocked.

    def update(self, snapshot):
        with self.lock:
            self.snapshot = copy.deepcopy(snapshot)

    def update_queue(self, rows):
        with self.lock:
            self.queue_rows = copy.deepcopy(rows)
            self.queue_revision += 1

    def update_artwork(self, identity, data):
        with self.lock:
            self.artwork_id = identity
            self.artwork = data

    def close(self):
        if self.discovery:
            self.discovery.close()
            self.discovery = None
        self.http.shutdown()
        self.http.server_close()
        self.thread.join(timeout=2)


def valid_adjustments(value, fields):
    if not isinstance(value, dict) or not value or not value.keys() <= fields.keys():
        return False
    for key, item in value.items():
        rule = fields[key]
        if rule is bool:
            if type(item) is not bool:
                return False
        elif (
            type(item) not in (int, float)
            or not math.isfinite(item)
            or not rule[0] <= item <= rule[1]
        ):
            return False
    return True
