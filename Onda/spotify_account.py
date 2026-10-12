"""User-authorized, read-only playlist access via OAuth PKCE and loopback."""
import base64
import hashlib
import html
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import re
import secrets
import time
from urllib.parse import parse_qs, urlencode, urlsplit
import webbrowser

import requests

from credentials import CredentialStore, CredentialError
from metadata import MetadataError
from playlist_options import DEFAULT_PLAYLIST_LIMIT, playlist_limit

REDIRECT_URI = "http://127.0.0.1:8765/callback"
SCOPES = "playlist-read-private playlist-read-collaborative"


def token_request(data):
    try:
        with requests.post("https://accounts.spotify.com/api/token", data=data, timeout=(10, 25), allow_redirects=False) as response:
            if response.status_code != 200:
                raise MetadataError("O Spotify recusou a conexão. Confira o Client ID, o endereço de retorno e autorize novamente.")
            result = response.json()
        if not isinstance(result, dict) or not isinstance(result.get("access_token"), str) or not result["access_token"]:
            raise ValueError()
        return result
    except (requests.RequestException, ValueError) as exc:
        if isinstance(exc, MetadataError):
            raise
        raise MetadataError("Não foi possível obter a autorização Spotify. Tente novamente.") from None


def callback_page(valid, granted, return_url=None):
    """Static page: never reflect OAuth codes, state or errors into HTML."""
    if return_url not in (None, "onda://spotify-return"):
        raise ValueError("Endereço de retorno não permitido.")
    message = ("Autorização recebida. Volte para o ONDA." if granted else
               "Autorização não concedida. Volte para o ONDA." if valid else
               "Retorno inválido. Volte para o ONDA e tente novamente.")
    action = ('<a href="onda://spotify-return">Voltar para o ONDA</a>' if return_url else
              '<button onclick="window.close()">Fechar esta aba</button>') if valid else ""
    script = "history.replaceState(null, '', location.pathname);"
    if valid:
        script += """
let seconds = 3;
const message = document.getElementById('status');
const tick = setInterval(() => {
  seconds -= 1;
  message.textContent = seconds > 0 ? `Voltando em ${seconds} segundos…` : 'Voltando para o ONDA…';
  if (seconds <= 0) clearInterval(tick);
}, 1000);
setTimeout(() => {
  RETURN_ACTION
  window.close();
  setTimeout(() => { message.textContent = 'Se a aba continuar aberta, você pode fechá-la e voltar para o ONDA.'; }, 500);
}, 3000);
""".replace("RETURN_ACTION", "location.href = " + json.dumps(return_url) + ";" if return_url else "")
    return ("<!doctype html><html lang='pt-BR'><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>ONDA · Spotify</title><style>"
            "body{font:17px system-ui;background:#101419;color:#eef3fa;display:grid;"
            "place-content:center;min-height:90vh;margin:24px;text-align:center}"
            "h1{color:#64ddc0}a,button{display:inline-block;background:#64ddc0;color:#101419;"
            "border:0;border-radius:10px;padding:12px 20px;text-decoration:none;font:inherit}"
            "</style><h1>ONDA</h1><p>" + html.escape(message) + "</p>"
            "<p id='status'>" + ("Voltando em 3 segundos…" if valid else "Feche esta aba e tente conectar novamente.") +
            "</p>" + action + "<script>" + script + "</script></html>").encode("utf-8")


def authorize(client_id, cancel, *, opener=webbrowser.open, port=8765, timeout=180, return_url=None):
    client_id = client_id.strip()
    if not re.fullmatch(r"[A-Fa-f0-9]{32}", client_id):
        raise MetadataError("Cole o Client ID de 32 caracteres do aplicativo no Spotify Developers.")
    verifier, state = secrets.token_urlsafe(64), secrets.token_urlsafe(32)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).decode("ascii").rstrip("=")
    result = {}
    class Callback(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass  # Callback query contains a one-time code; never log it.
        def do_GET(self):
            parsed = urlsplit(self.path)
            query = parse_qs(parsed.query)
            valid = parsed.path == "/callback" and secrets.compare_digest(query.get("state", [""])[0], state)
            if valid:
                result.update(code=query.get("code", [None])[0], error=query.get("error", [None])[0])
            body = callback_page(valid, valid and bool(result.get("code")) and not result.get("error"), return_url)
            self.send_response(200 if valid else 400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            try:
                self.wfile.write(body)
            except OSError:
                pass
    class LocalServer(HTTPServer):
        def get_request(self):
            connection, address = super().get_request()
            connection.settimeout(1)
            return connection, address
    try:
        server = LocalServer(("127.0.0.1", port), Callback)
    except OSError:
        raise MetadataError("A porta local 8765 está ocupada. Feche outra conexão Spotify do Onda e tente novamente.") from None
    with server:
        server.timeout = 0.25
        redirect = f"http://127.0.0.1:{server.server_port}/callback"
        url = "https://accounts.spotify.com/authorize?" + urlencode({"client_id": client_id,
              "response_type": "code", "redirect_uri": redirect, "scope": SCOPES, "state": state,
              "code_challenge_method": "S256", "code_challenge": challenge})
        if not opener(url):
            raise MetadataError("Não foi possível abrir o navegador padrão. Confira o navegador e tente novamente.")
        deadline = time.monotonic() + timeout
        while not result and not cancel.is_set() and time.monotonic() < deadline:
            server.handle_request()
    if cancel.is_set():
        raise MetadataError("Conexão Spotify cancelada.")
    if not result:
        raise MetadataError("O tempo de autorização expirou. Clique em Conectar novamente.")
    if result.get("error") or not result.get("code"):
        raise MetadataError("A autorização Spotify não foi concedida.")
    tokens = token_request({"grant_type": "authorization_code", "client_id": client_id,
                            "code": result["code"], "redirect_uri": redirect, "code_verifier": verifier})
    if cancel.is_set():
        raise MetadataError("Conexão Spotify cancelada.")
    return client_id, tokens


class SpotifyAccount:
    def __init__(self, path):
        self.store = CredentialStore(path)
        self.client_id = self.refresh_token = self.access_token = ""
        self.expires_at = 0
        self.remember = False
        self.warning = ""
        try:
            saved = self.store.load()
            if saved:
                self.client_id, self.refresh_token = saved
                self.remember = True
        except (CredentialError, OSError):
            self.warning = "Não foi possível ler a conexão salva. Conecte novamente."

    @property
    def connected(self):
        return bool(self.client_id and (self.refresh_token or self.access_token))

    def accept(self, client_id, tokens, remember=False):
        if not tokens.get("refresh_token"):
            raise MetadataError("O Spotify não retornou uma conexão renovável. Autorize novamente.")
        if remember:
            self.store.save(client_id, tokens["refresh_token"])
        else:
            self.store.forget()
        self.client_id, self.refresh_token = client_id, tokens["refresh_token"]
        self.access_token = tokens["access_token"]
        self.expires_at = time.monotonic() + float(tokens.get("expires_in", 3600)) - 30
        self.remember = remember
        self.warning = ""

    def disconnect(self):
        self.store.forget()
        self.client_id = self.refresh_token = self.access_token = ""
        self.expires_at = 0
        self.remember = False

    def token(self, force=False):
        if not self.connected:
            raise MetadataError("Conecte sua conta Spotify primeiro.")
        if force or time.monotonic() >= self.expires_at:
            tokens = token_request({"grant_type": "refresh_token", "client_id": self.client_id, "refresh_token": self.refresh_token})
            refresh = tokens.get("refresh_token") or self.refresh_token
            if self.remember and refresh != self.refresh_token:
                self.store.save(self.client_id, refresh)
            self.refresh_token = refresh
            self.access_token = tokens["access_token"]
            self.expires_at = time.monotonic() + float(tokens.get("expires_in", 3600)) - 30
        return self.access_token

    def get(self, path, params=None):
        searching = path == "search"
        for attempt in range(2):
            token = self.token(force=bool(attempt))
            try:
                with requests.get("https://api.spotify.com/v1/" + path, params=params,
                                  headers={"Authorization": "Bearer " + token}, timeout=(10, 25), allow_redirects=False) as response:
                    if response.status_code == 401 and not attempt:
                        continue
                    if response.status_code == 403:
                        if searching:
                            raise MetadataError('Spotify negou acesso à pesquisa. Confira o aplicativo no Spotify Developers e o usuário autorizado, ou reconecte sua conta.')
                        raise MetadataError("Spotify negou acesso: a playlist deve ser sua ou colaborativa. Confira também o usuário autorizado no Spotify Developers e o Premium do dono do app em modo de desenvolvimento. Você ainda pode importar um CSV.")
                    if response.status_code == 429:
                        delay = response.headers.get("Retry-After", "alguns")
                        delay = delay if str(delay).isdigit() else "alguns"
                        raise MetadataError(f"Limite temporário do Spotify. Aguarde {delay} segundos e tente novamente.")
                    if response.status_code != 200:
                        raise MetadataError('Não foi possível pesquisar no Spotify. Reconecte sua conta e tente novamente.' if searching else "Não foi possível ler a playlist Spotify. Confira o link e reconecte sua conta.")
                    data = response.json()
                    if not isinstance(data, dict):
                        raise ValueError()
                    return data
            except requests.RequestException:
                raise MetadataError("Falha de conexão com o Spotify. Tente novamente.") from None

    def playlist(self, playlist_id, limit=DEFAULT_PLAYLIST_LIMIT, cancelled=lambda: False):
        limit = playlist_limit(limit)
        if not re.fullmatch(r"[A-Za-z0-9]{22}", playlist_id):
            raise MetadataError("ID de playlist Spotify inválido.")
        meta = self.get("playlists/" + playlist_id)
        records, offset, skipped, total = [], 0, 0, None
        while offset < limit:
            if cancelled():
                raise MetadataError("Carregamento cancelado.")
            data = self.get(f"playlists/{playlist_id}/items", {"offset": offset, "limit": min(50, limit - offset)})
            page = data.get("items") or []
            total = data.get("total", total)
            for row in page:
                track = (row.get("item") or row.get("track") or {}) if isinstance(row, dict) else {}
                if not isinstance(track, dict) or track.get("type") != "track" or track.get("is_local") or (isinstance(row, dict) and row.get("is_local")) or not re.fullmatch(r"[A-Za-z0-9]{22}", str(track.get("id", ""))):
                    skipped += 1
                    continue
                records.append({"title": track.get("name") or "Faixa Spotify",
                                "artists": [a["name"] for a in track.get("artists", []) if a.get("name")],
                                "duration_ms": track.get("duration_ms"), "source_url": "https://open.spotify.com/track/" + track["id"]})
            offset += len(page)
            if not page or not data.get("next"):
                break
        note = f"Spotify conectado: {len(records)} músicas; {skipped} itens locais/indisponíveis/episódios ignorados."
        if isinstance(total, int) and offset < total:
            note += f" Limite de {limit} atingido (playlist: {total} itens). Aumente em Configurações para carregar mais."
        return {"title": meta.get("name") or "Playlist Spotify", "tracks": records, "note": note}
