"""Read-only catalog metadata and optional Spotify-to-public-catalog resolution."""
from __future__ import annotations

import re
import time
from urllib.parse import parse_qs, urlsplit

import requests


class MetadataError(ValueError):
    pass


def is_streaming_link(value):
    if value.strip().startswith("spotify:"):
        return True
    try:
        return (urlsplit(value.strip()).hostname or "").lower().rstrip(".") in {
            "open.spotify.com", "spotify.com", "www.spotify.com", "spotify.link",
            "music.apple.com", "itunes.apple.com",
            "deezer.com", "www.deezer.com", "link.deezer.com", "deezer.page.link",
        }
    except ValueError:
        return False


def parse_link(value):
    value = value.strip()
    if value.startswith("spotify:track:"):
        value = "https://open.spotify.com/track/" + value.split(":")[-1]
    try:
        parsed = urlsplit(value)
        host = (parsed.hostname or "").lower().rstrip(".")
        if (parsed.scheme not in ("https", "http") or parsed.username or parsed.password
                or parsed.port not in (None, 80, 443) or any(c.isspace() for c in value)):
            raise MetadataError("Use um link público completo de uma música.")
    except ValueError as exc:
        raise MetadataError("Link inválido.") from exc
    parts = [part for part in parsed.path.split("/") if part]
    if host in ("deezer.com", "www.deezer.com"):
        if parts and re.fullmatch(r"[a-z]{2}", parts[0]):
            parts = parts[1:]
        if len(parts) != 2 or parts[0] != "track" or not re.fullmatch(r"\d+", parts[1]):
            raise MetadataError("Deezer: use o link de uma faixa, não de álbum, artista ou playlist.")
        return "deezer", parts[1], None, "https://www.deezer.com/track/" + parts[1]
    if host == "open.spotify.com":
        if parts and (parts[0].startswith("intl-") or parts[0] == "embed"):
            parts = parts[1:]
        if len(parts) != 2 or parts[0] != "track" or not re.fullmatch(r"[A-Za-z0-9]{22}", parts[1]):
            raise MetadataError("Spotify: use o link de uma faixa, não de álbum, artista ou playlist.")
        return "spotify", parts[1], None, "https://open.spotify.com/track/" + parts[1]
    if host in ("music.apple.com", "itunes.apple.com"):
        country = parts[0].lower() if parts else ""
        if not re.fullmatch(r"[a-z]{2}", country):
            raise MetadataError("Apple: o link deve conter a região, como /br/ ou /us/.")
        query_id = parse_qs(parsed.query).get("i", [None])[0]
        song_id = query_id
        if song_id is None and len(parts) >= 3 and parts[1] == "song":
            song_id = parts[-1].removeprefix("id")
        if not song_id or not re.fullmatch(r"\d+", song_id):
            raise MetadataError("Apple: copie o link da música (com ?i=ID), não apenas do álbum.")
        return "apple", song_id, country, f"https://music.apple.com/{country}/song/{song_id}"
    raise MetadataError("Use um link de música do Deezer, Spotify ou Apple Music/iTunes.")


def base_record(platform, track_id, source_url, method):
    return dict(platform=platform, id=track_id, source_url=source_url, method=method,
                title=None, artists=[], album=None, album_artists=[], release_date=None,
                duration_ms=None, track_number=None, disc_number=None, genre=None,
                isrc=None, explicit=None, cover_url=None, preview_url=None, notes=[])


def deezer_record(data, track_id, url):
    if str(data.get("id")) != track_id or not data.get("title"):
        raise MetadataError("Deezer retornou uma faixa diferente ou uma resposta incompleta.")
    record = base_record("Deezer", track_id, url, "Deezer API pública")
    album = data.get("album") or {}
    artists = [a["name"] for a in data.get("contributors", []) if a.get("name")]
    if not artists and (data.get("artist") or {}).get("name"):
        artists = [data["artist"]["name"]]
    duration = data.get("duration")
    record.update(title=data["title"], artists=artists, album=album.get("title"),
                  release_date=data.get("release_date"),
                  duration_ms=duration * 1000 if isinstance(duration, (int, float)) else None,
                  track_number=data.get("track_position"), disc_number=data.get("disk_number"),
                  isrc=data.get("isrc"), explicit=data.get("explicit_lyrics"),
                  cover_url=album.get("cover_xl") or album.get("cover_medium"), preview_url=data.get("preview"))
    return record


def spotify_record(data, track_id, url):
    if data.get("id") != track_id or not data.get("name"):
        raise MetadataError("Spotify retornou uma faixa diferente ou uma resposta incompleta.")
    record = base_record("Spotify", track_id, url, "Spotify Web API")
    album = data.get("album") or {}
    images = album.get("images") or []
    record.update(title=data["name"], artists=[a["name"] for a in data.get("artists", []) if a.get("name")],
                  album=album.get("name"), album_artists=[a["name"] for a in album.get("artists", []) if a.get("name")],
                  release_date=album.get("release_date"), duration_ms=data.get("duration_ms"),
                  track_number=data.get("track_number"), disc_number=data.get("disc_number"),
                  explicit=data.get("explicit"), isrc=(data.get("external_ids") or {}).get("isrc"),
                  cover_url=images[0].get("url") if images else None)
    return record


def apple_record(data, track_id, url):
    song = next((row for row in data.get("results", [])
                 if str(row.get("trackId")) == track_id and row.get("kind") == "song"), None)
    if not song:
        raise MetadataError("Música não encontrada no catálogo público iTunes desta região. "
                            "Nem todo item do Apple Music está disponível nessa API.")
    record = base_record("Apple / iTunes", track_id, url, "iTunes Lookup API")
    explicit = song.get("trackExplicitness")
    record.update(title=song.get("trackName"), artists=[song["artistName"]] if song.get("artistName") else [],
                  album=song.get("collectionName"), release_date=song.get("releaseDate"),
                  duration_ms=song.get("trackTimeMillis"), track_number=song.get("trackNumber"),
                  disc_number=song.get("discNumber"), genre=song.get("primaryGenreName"),
                  explicit=explicit == "explicit" if explicit is not None else None,
                  cover_url=apple_artwork(song.get("artworkUrl100") or song.get("artworkUrl60")), preview_url=song.get("previewUrl"))
    record["notes"].append("Dados do catálogo iTunes da região do link. ISRC e artistas do álbum não são fornecidos por esta consulta.")
    return record


def apple_artwork(url):
    """Request the same artwork at 1200px from Apple's image CDN."""
    host = (urlsplit(url).hostname or "").lower() if url else ""
    if host.endswith(".mzstatic.com"):
        return re.sub(r"/\d+x\d+(bb)?\.(jpg|jpeg|png)(?=\?|$)",
                      r"/1200x1200\1.\2", url, flags=re.I)
    return url


class MetadataClient:
    def __init__(self, client_id="", client_secret=""):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "Onda/1.1 (catalog metadata)"
        self.client_id, self.client_secret = client_id.strip(), client_secret.strip()
        self.token = None
        self.expires = 0

    def close(self):
        self.session.close()
        self.client_secret = self.token = None

    def request(self, url, *, method="GET", **kwargs):
        try:
            response = self.session.request(method, url, timeout=(5, 15), allow_redirects=False, **kwargs)
        except requests.RequestException:
            raise MetadataError("Falha de conexão. Verifique internet, proxy e tente novamente.") from None
        if response.status_code == 429:
            delay = response.headers.get("Retry-After", "alguns")
            response.close()
            raise MetadataError(f"Limite de consultas atingido. Tente novamente em {delay} segundos.")
        if response.status_code in (401, 403):
            response.close()
            raise MetadataError("A API recusou a autenticação ou o acesso do aplicativo. Confira as credenciais e permissões.")
        if response.status_code >= 400:
            code = response.status_code
            response.close()
            raise MetadataError(f"O serviço retornou HTTP {code}. Confira o link e a disponibilidade da faixa.")
        return response

    def get_json(self, url, **kwargs):
        with self.request(url, **kwargs) as response:
            if response.is_redirect:
                raise MetadataError("O serviço redirecionou a consulta. Tente novamente com o link completo da faixa.")
            try:
                result = response.json()
            except ValueError:
                raise MetadataError("O serviço retornou uma resposta inválida.") from None
        if not isinstance(result, dict):
            raise MetadataError("O serviço retornou um formato inesperado.")
        return result

    def resolve_short_link(self, url):
        from urllib.parse import urljoin
        for _ in range(5):
            parsed = urlsplit(url)
            host = (parsed.hostname or "").lower()
            if (parsed.scheme != "https" or parsed.username or parsed.password or parsed.port not in (None, 443)
                    or host not in ("spotify.link", "open.spotify.com")):
                raise MetadataError("O link curto não aponta para uma página Spotify válida.")
            if host == "open.spotify.com":
                return url
            with self.request(url) as response:
                location = response.headers.get("Location")
                if not response.is_redirect or not location:
                    raise MetadataError("Não foi possível resolver o link curto. Copie o link open.spotify.com da música.")
                url = urljoin(url, location)
        raise MetadataError("Muitos redirecionamentos. Use o link completo da música.")

    def spotify_token(self):
        if not self.token or time.monotonic() >= self.expires:
            response = self.get_json("https://accounts.spotify.com/api/token", method="POST",
                                     data={"grant_type": "client_credentials"},
                                     auth=(self.client_id, self.client_secret))
            self.token = response.get("access_token")
            if not self.token:
                raise MetadataError("Spotify não forneceu um token de acesso.")
            self.expires = time.monotonic() + max(0, float(response.get("expires_in", 3600)) - 60)
        return self.token

    def fetch(self, url):
        if (urlsplit(url.strip()).hostname or "").lower() in ("link.deezer.com", "deezer.page.link"):
            url = self.resolve_deezer_link(url.strip())
        if (urlsplit(url.strip()).hostname or "").lower() == "spotify.link":
            url = self.resolve_short_link(url.strip())
        service, track_id, country, canonical = parse_link(url)
        if service == "deezer":
            result = self.get_json(f"https://api.deezer.com/track/{track_id}")
            if result.get("error"):
                raise MetadataError("Faixa indisponível no catálogo Deezer.")
            return deezer_record(result, track_id, canonical)
        if service == "apple":
            result = self.get_json("https://itunes.apple.com/lookup", params={"id": track_id, "country": country})
            return apple_record(result, track_id, canonical)
        if bool(self.client_id) != bool(self.client_secret):
            raise MetadataError("Preencha Client ID e Client Secret juntos, ou deixe ambos vazios para a consulta pública.")
        if self.client_id:
            result = self.get_json(f"https://api.spotify.com/v1/tracks/{track_id}",
                                   headers={"Authorization": "Bearer " + self.spotify_token()})
            return spotify_record(result, track_id, canonical)
        result = self.get_json("https://open.spotify.com/oembed", params={"url": canonical})
        if not result.get("title"):
            raise MetadataError("Spotify não retornou o título da faixa.")
        record = base_record("Spotify", track_id, canonical, "Spotify oEmbed (público)")
        record.update(title=result["title"], cover_url=result.get("thumbnail_url"))
        record["notes"].append("Consulta pública direta limitada a título e capa. Para baixar sem API, use a pesquisa ou fila: o Onda tenta uma faixa equivalente no Deezer/Apple.")
        return record

    def resolve_deezer_link(self, url):
        from urllib.parse import urljoin
        for _ in range(6):
            parsed = urlsplit(url)
            host = (parsed.hostname or "").lower()
            if (parsed.scheme != "https" or parsed.username or parsed.password or parsed.port not in (None, 443)
                    or host not in ("link.deezer.com", "deezer.page.link", "deezer.com", "www.deezer.com")):
                raise MetadataError("Use o link completo deezer.com/track/ID da faixa.")
            if host in ("deezer.com", "www.deezer.com"):
                parse_link(url)
                return url
            with self.request(url) as response:
                location = response.headers.get("Location")
                if not response.is_redirect or not location:
                    break
                url = urljoin(url, location)
        raise MetadataError("Não foi possível resolver o link curto. Copie deezer.com/track/ID.")

    def resolve(self, url, choose=None, selected_catalog_url=None):
        """Resolve downloads; fetch() remains a direct, uncombined provider lookup."""
        if (urlsplit(url.strip()).hostname or "").lower() == "spotify.link":
            url = self.resolve_short_link(url.strip())
        if (urlsplit(url.strip()).hostname or "").lower() in ("link.deezer.com", "deezer.page.link"):
            return self.fetch(url)
        service, track_id, _, canonical = parse_link(url)
        if service != "spotify":
            return self.fetch(url)
        anchor, warning = None, None
        try:
            anchor = self.fetch(canonical)
            if anchor.get("artists") and not selected_catalog_url:
                return anchor
        except MetadataError:
            warning = "A consulta direta Spotify não ficou disponível; foi usada a identificação pública."
        try:
            from spotify_public import parse_public_track
            with self.request("https://open.spotify.com/embed/track/" + track_id) as response:
                if response.is_redirect:
                    raise MetadataError("Spotify redirecionou a página pública.")
                public_anchor = parse_public_track(response.text, track_id, canonical)
            if not anchor or not anchor.get("artists"):
                anchor = public_anchor
        except MetadataError:
            if not anchor or not anchor.get("title"):
                result = self.get_json("https://open.spotify.com/oembed", params={"url": canonical})
                if not result.get("title"):
                    raise MetadataError("Spotify não informou o título. Pesquise a música pelo nome na aba Pesquisar músicas.")
                anchor = base_record("Spotify", track_id, canonical, "Spotify oEmbed (público)")
                anchor["title"] = result["title"]
        if warning:
            anchor["notes"].append(warning)
        if selected_catalog_url:
            return self.confirm_catalog(anchor, {"source_url": selected_catalog_url}, selection="user")
        from catalog_match import rank_catalog, automatic_catalog, CatalogChoiceRequired
        query = " ".join(filter(None, [(anchor.get("artists") or [""])[0], anchor["title"]]))[:300]
        for provider in ("Deezer", "Apple / iTunes"):
            try:
                candidates = rank_catalog(anchor, self.search(query, provider))
            except MetadataError:
                continue
            if not candidates:
                continue
            selected = automatic_catalog(anchor, candidates)
            selection = "automatic"
            if selected is None:
                if choose is None:
                    raise CatalogChoiceRequired(anchor, candidates[:12])
                selected = choose(anchor, candidates[:12])
                if not any(row["source_url"] == selected.get("source_url") for row in candidates[:12]):
                    raise MetadataError("A faixa escolhida não pertence aos resultados do catálogo.")
                selection = "user"
            return self.confirm_catalog(anchor, selected, selection)
        raise MetadataError("Não encontrei uma faixa compatível no Deezer ou Apple. Pesquise pelo nome ou use o link direto da faixa nesses catálogos.")

    def confirm_catalog(self, anchor, candidate, selection="user"):
        from catalog_match import rank_catalog
        service, _, _, canonical = parse_link(candidate["source_url"])
        if service not in ("deezer", "apple"):
            raise MetadataError("Escolha metadados do Deezer ou Apple.")
        record = self.fetch(canonical)
        ranked = rank_catalog(anchor, [record])
        if not ranked:
            raise MetadataError("Os detalhes da faixa escolhida não correspondem mais ao link Spotify.")
        record["requested_source_url"] = anchor["source_url"]
        record["catalog_match"] = {"selection": selection, "score": ranked[0]["catalog_score"],
            "same_isrc": ranked[0]["same_isrc"], "spotify_identity": {k: anchor.get(k) for k in ("id", "title", "artists", "duration_ms", "isrc")}}
        record["notes"].extend(anchor.get("notes", []))
        record["notes"].append("Link de entrada Spotify; metadados e capa da faixa correspondente em " + record["platform"] + ". Correspondência de catálogo não comprova a masterização do áudio YouTube.")
        return record

    def search(self, query, provider="Deezer", country="br", limit=25, *, account=None):
        query = query.strip()
        if not 2 <= len(query) <= 300:
            raise MetadataError("Digite entre 2 e 300 caracteres para pesquisar.")
        if provider == 'Spotify':
            from spotify_search import search_tracks
            if account is not None and account.connected:
                return search_tracks(query, account.get, country, limit)
            if not self.client_id or not self.client_secret:
                raise MetadataError('Para pesquisar no Spotify, use Conectar Spotify ou configure Client ID e Client Secret em Metadados. Deezer e Apple continuam disponíveis sem conexão Spotify.')
            def get(path, params):
                return self.get_json('https://api.spotify.com/v1/' + path, params=params,
                                     headers={'Authorization': 'Bearer ' + self.spotify_token()})
            return search_tracks(query, get, country, limit)
        if provider == "Deezer":
            response = self.get_json("https://api.deezer.com/search", params={"q": query, "limit": limit})
            if response.get("error"):
                raise MetadataError("Deezer não conseguiu realizar a pesquisa. Tente novamente.")
            rows = response.get("data")
            if not isinstance(rows, list):
                raise MetadataError("Resposta de busca Deezer inválida.")
            records = []
            for row in rows[:limit]:
                if not isinstance(row, dict) or not str(row.get("id", "")).isdigit() or not row.get("title"):
                    continue
                track_id = str(row["id"])
                records.append(deezer_record(row, track_id, "https://www.deezer.com/track/" + track_id))
            return records
        if provider != "Apple / iTunes":
            raise MetadataError("Catálogo de pesquisa inválido.")
        response = self.get_json("https://itunes.apple.com/search", params={
            "term": query, "country": country, "media": "music", "entity": "song", "limit": limit})
        if not isinstance(response.get("results"), list):
            raise MetadataError("Resposta de busca Apple inválida.")
        records = []
        for row in response["results"][:limit]:
            if not isinstance(row, dict) or row.get("kind") != "song" or not str(row.get("trackId", "")).isdigit():
                continue
            track_id = str(row["trackId"])
            records.append(apple_record({"results": [row]}, track_id, f"https://music.apple.com/{country}/song/{track_id}"))
        return records
