"""Small, opt-in LAN discovery responder. Pairing still requires the PC code."""

import ipaddress
import json
import re
import socket
import threading
import time

DISCOVERY_PORT = 45847


def discovery_reply(data, address, port, name):
    try:
        ip = ipaddress.ip_address(address)
        if ip.version != 4 or not ip.is_private or ip.is_loopback:
            return None
        request = json.loads(data)
        nonce = request.get('nonce', '')
        if request.get('type') != 'onda-discover' or not re.fullmatch(
            '[a-f0-9]{32}', nonce
        ):
            return None
        return json.dumps(
            dict(type='onda-device', nonce=nonce, port=port, name=name, protocol=1)
        ).encode()
    except (ValueError, TypeError, AttributeError):
        return None


class DiscoveryResponder:
    def __init__(self, port, name):
        self.port = port
        self.name = name
        self.stopped = threading.Event()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.socket.bind(('0.0.0.0', DISCOVERY_PORT))
            self.socket.settimeout(0.5)
        except OSError:
            self.socket.close()
            raise
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        recent = {}
        while not self.stopped.is_set():
            try:
                data, peer = self.socket.recvfrom(513)
                now = time.monotonic()
                if len(data) > 512 or now - recent.get(peer[0], -10) < 0.5:
                    continue
                recent = {ip: t for ip, t in recent.items() if now - t < 10}
                if len(recent) >= 128:
                    continue
                recent[peer[0]] = now
                reply = discovery_reply(data, peer[0], self.port, self.name)
                if reply:
                    self.socket.sendto(reply, peer)
            except socket.timeout:
                continue
            except OSError:
                break

    def close(self):
        self.stopped.set()
        self.socket.close()
        self.thread.join(timeout=1)
