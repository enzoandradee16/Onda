"""Read-only catalog metadata and optional Spotify-to-public-catalog resolution."""
from __future__ import annotations

import re
import time
from urllib.parse import parse_qs, urlsplit

import requests
from edition_evidence import finite_positive


class MetadataError(ValueError):
    pass


def _names(values):
    return list(dict.fromkeys(row['name'].strip() for row in values if isinstance(row,dict)
                             and isinstance(row.get('name'),str) and row['name'].strip())) if isinstance(values,list) else []


def _rows(values):
    return values if isinstance(values,list) else []


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
                isrc=None, explicit=None, cover_url=None, preview_url=None, spotify_artist_ids=[], notes=[])


def deezer_record(data, track_id, url):
    if str(data.get("id")) != track_id or not isinstance(data.get("title"),str) or not data['title'].strip():
        raise MetadataError("Deezer retornou uma faixa diferente ou uma resposta incompleta.")
    record = base_record("Deezer", track_id, url, "Deezer API pública")
    album = data.get("album") if isinstance(data.get('album'),dict) else {}
    artists = _names(data.get('contributors')) or _names([data.get('artist')])
    duration = data.get("duration")
    record.update(title=data["title"], title_version=data.get('title_version'), artists=artists, album=album.get("title"),
                  release_date=data.get("release_date"),
                  duration_ms=duration * 1000 if finite_positive(duration) else None,
                  track_number=data.get("track_position"), disc_number=data.get("disk_number"),
                  isrc=data.get("isrc"), explicit=data.get("explicit_lyrics"),
                  cover_url=album.get("cover_xl") or album.get("cover_medium"), preview_url=data.get("preview"))
    return record


def spotify_record(data, track_id, url):
    if data.get("id") != track_id or not isinstance(data.get("name"),str) or not data['name'].strip():
        raise MetadataError("Spotify retornou uma faixa diferente ou uma resposta incompleta.")
    record = base_record("Spotify", track_id, url, "Spotify Web API")
    album = data.get("album") if isinstance(data.get('album'),dict) else {}
    images = [row for row in _rows(album.get('images')) if isinstance(row,dict)]
    record["spotify_artist_ids"]=[artist["id"] for artist in _rows(data.get("artists")) if isinstance(artist,dict) and re.fullmatch(r"[A-Za-z0-9]{22}",str(artist.get("id","")))]
    record.update(title=data["name"], artists=_names(data.get('artists')),
                  album=album.get("name"), album_artists=_names(album.get('artists')),
                  release_date=album.get("release_date"), duration_ms=data.get("duration_ms"),
                  track_number=data.get("track_number"), disc_number=data.get("disc_number"),
                  explicit=data.get("explicit"), isrc=(data.get("external_ids") or {}).get("isrc"),
                  cover_url=images[0].get("url") if images else None)
    return record


def apple_record(data, track_id, url):
    song = next((row for row in _rows(data.get("results"))
                 if isinstance(row,dict) and str(row.get("trackId")) == track_id and row.get("kind") == "song" and isinstance(row.get('trackName'),str)), None)
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
        self.spotify_get = None
        self.cancelled = lambda: False
        self.deadline = None

    def close(self):
        self.session.close()
        self.client_secret = self.token = None

    def request(self, url, *, method="GET", **kwargs):
        def check():
            if self.cancelled():
                from music_search import SearchCancelled
                raise SearchCancelled('Pesquisa cancelada.')
            if self.deadline is not None and time.monotonic() >= self.deadline:
                from music_search import SearchCancelled
                raise SearchCancelled('Tempo de pesquisa esgotado.')
        for attempt in range(3 if method == 'GET' else 1):
            check()
            remaining = max(.1,self.deadline-time.monotonic()) if self.deadline is not None else 20
            try:
                response = self.session.request(method, url, timeout=(min(5,remaining), min(15,remaining)), allow_redirects=False, **kwargs)
            except requests.RequestException:
                if attempt == 2 or method != 'GET':
                    raise MetadataError("Falha de conexão. Verifique internet, proxy e tente novamente.") from None
                response = None
            check()
            if response is not None and (response.status_code not in (429,500,502,503,504) or attempt == 2 or method != 'GET'):
                break
            delay = .25 * 2**attempt
            if response is not None:
                if response.status_code == 429:
                    try:
                        delay = float(response.headers.get('Retry-After','1'))
                    except (ValueError,TypeError):
                        break
                    if not 0 <= delay <= 2:
                        break
                response.close()
            until = time.monotonic()+delay
            while time.monotonic()<until:
                check()
                time.sleep(min(.05,max(0,until-time.monotonic())))
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
        if self.spotify_get is not None:
            try:
                return spotify_record(self.spotify_get("tracks/"+track_id),track_id,canonical)
            except MetadataError:pass
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

    def resolve(self, url, choose=None, selected_catalog_url=None, automatic=False):
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
                return self.complete_spotify(anchor,choose,selected_catalog_url,automatic)
        except MetadataError:
            warning = "A consulta direta Spotify não ficou disponível; foi usada a identificação pública."
        try:
            from spotify_public import parse_public_track
            with self.request("https://open.spotify.com/embed/track/" + track_id) as response:
                if response.is_redirect:
                    raise MetadataError("Spotify redirecionou a página pública.")
                public_anchor = parse_public_track(response.text, track_id, canonical)
            if not anchor or not anchor.get("artists"):
                anchor = {**public_anchor,**{key:value for key,value in (anchor or {}).items() if value not in (None,"",[],{}) and key not in ("method","notes")}}
        except MetadataError:
            if not anchor or not anchor.get("title"):
                result = self.get_json("https://open.spotify.com/oembed", params={"url": canonical})
                if not result.get("title"):
                    raise MetadataError("Spotify não informou o título. Pesquise a música pelo nome na aba Pesquisar músicas.")
                anchor = base_record("Spotify", track_id, canonical, "Spotify oEmbed (público)")
                anchor["title"] = result["title"]
        if warning:
            anchor["notes"].append(warning)
        return self.complete_spotify(anchor,choose,selected_catalog_url,automatic)

    def complete_spotify(self,anchor,choose=None,selected_catalog_url=None,automatic=False):
        from spotify_metadata import spotify_track,original_metadata,FIELDS,missing
        if anchor.get("platform")!="Spotify" or not spotify_track(anchor.get("source_url")):
            return anchor
        if selected_catalog_url:
            return self.confirm_catalog(anchor, {"source_url": selected_catalog_url}, selection="user")
        from catalog_match import rank_catalog, automatic_catalog, CatalogChoiceRequired
        missing_fields=[key for key in FIELDS if key!="preview_url" and missing(anchor.get(key))]
        if not missing_fields or missing_fields==["genre"]:return original_metadata(anchor)
        from record_identity import normalized_isrc
        isrc=normalized_isrc(anchor.get("isrc"))
        if isrc and missing_fields!=["genre"]:
            try:
                data=self.get_json("https://api.deezer.com/track/isrc:"+isrc)
                if str(data.get("id","")).isdigit() and data.get("title"):
                    candidate=deezer_record(data,str(data["id"]),"https://www.deezer.com/track/"+str(data["id"]))
                    if rank_catalog(anchor,[candidate]) and any(not missing(candidate.get(key)) for key in missing_fields):return self.confirm_catalog(anchor,candidate,"automatic",record=candidate)
            except MetadataError:pass
        query = " ".join(filter(None, [(anchor.get("artists") or [""])[0], anchor["title"]]))[:300]
        alias_fallback_used=False
        providers=("Apple / iTunes",) if missing_fields==["genre"] else ("Deezer", "Apple / iTunes")
        for provider in providers:
            try:
                candidates = rank_catalog(anchor, self.search(query, provider))
            except MetadataError:
                continue
            if not candidates and not alias_fallback_used:
                from catalog_aliases import alternate_records
                candidates=rank_catalog(anchor,alternate_records(anchor,self))
                alias_fallback_used=True
            candidates=[row for row in candidates if any(not missing(row.get(key)) for key in missing_fields)]
            if not candidates:
                continue
            from search_evidence import album_core
            if anchor.get("album"):
                candidates=[row for row in candidates if row.get('same_isrc') or album_core(row.get('album'))==album_core(anchor['album'])]
                if not candidates:continue
            selected = automatic_catalog(anchor, candidates,prefer_best=automatic)
            selection = "automatic"
            if selected is None:
                if anchor.get("artists") and anchor.get("duration_ms"):
                    return original_metadata(anchor)
                if automatic:
                    raise MetadataError("Não encontrei metadados suficientemente compatíveis para seleção automática. Pesquise a faixa na lista de falhas.")
                if choose is None:
                    raise CatalogChoiceRequired(anchor, candidates[:12])
                selected = choose(anchor, candidates[:12])
                if not any(row["source_url"] == selected.get("source_url") for row in candidates[:12]):
                    raise MetadataError("A faixa escolhida não pertence aos resultados do catálogo.")
                selection = "user"
            try:return self.confirm_catalog(anchor, selected, selection)
            except MetadataError:
                if not anchor.get("artists"):raise
        if anchor.get("artists"):
            return original_metadata(anchor)
        raise MetadataError("Não encontrei uma faixa compatível no Deezer ou Apple. Pesquise pelo nome ou use o link direto da faixa nesses catálogos.")

    def confirm_catalog(self, anchor, candidate, selection="user",record=None):
        from catalog_match import rank_catalog
        service, _, _, canonical = parse_link(candidate["source_url"])
        if service not in ("deezer", "apple"):
            raise MetadataError("Escolha metadados do Deezer ou Apple.")
        record = self.fetch(canonical) if record is None else record
        ranked = rank_catalog(anchor, [record])
        if not ranked:
            raise MetadataError("Os detalhes da faixa escolhida não correspondem mais ao link Spotify.")
        from spotify_metadata import spotify_track,supplement_metadata
        if anchor.get("platform")=="Spotify" and spotify_track(anchor.get("source_url")):
            result=supplement_metadata(anchor,record,{"selection":selection,"score":ranked[0]["catalog_score"],"same_isrc":ranked[0]["same_isrc"]})
            result["notes"].append("Metadados do Spotify preservados; outros catálogos completam somente os campos ausentes.")
            return result
        record["requested_source_url"] = anchor["source_url"]
        record["catalog_match"] = {"selection": selection, "score": ranked[0]["catalog_score"],
            "same_isrc": ranked[0]["same_isrc"], "spotify_identity": {k: anchor.get(k) for k in ("id", "title", "artists", "duration_ms", "isrc")}}
        record["notes"].extend(anchor.get("notes", []))
        record["notes"].append("Link de entrada Spotify; metadados e capa da faixa correspondente em " + record["platform"] + ". Correspondência de catálogo não comprova a masterização do áudio YouTube.")
        return record

    def search(self, query, provider="Deezer", country="br", limit=25, *, account=None):
        query = query.strip()
        if not 1 <= len(query) <= 300:
            raise MetadataError("Digite entre 1 e 300 caracteres para pesquisar.")
        if type(limit) is not int or not 1 <= limit <= 50:
            raise MetadataError('Use um limite de busca entre 1 e 50 músicas.')
        if not isinstance(country,str) or not re.fullmatch(r'[a-zA-Z]{2}',country):
            raise MetadataError('Região de catálogo inválida.')
        country=country.lower()
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
            records,seen,offset = [],set(),0
            for page in range(3):
                params={"q":query,"limit":limit-len(records)}
                if offset:params['index']=offset
                response = self.get_json("https://api.deezer.com/search", params=params)
                if response.get("error"):
                    raise MetadataError("Deezer não conseguiu realizar a pesquisa. Tente novamente.")
                rows = response.get("data")
                if not isinstance(rows, list):
                    raise MetadataError("Resposta de busca Deezer inválida.")
                previous=len(records)
                for row in rows[:limit-len(records)]:
                    if not isinstance(row, dict) or not str(row.get("id", "")).isdigit() or not row.get("title"):
                        continue
                    track_id = str(row["id"])
                    if track_id in seen:continue
                    seen.add(track_id)
                    records.append(deezer_record(row, track_id, "https://www.deezer.com/track/" + track_id))
                offset+=len(rows)
                if len(records)>=limit or not rows or not response.get('next') or len(records)==previous:break
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
