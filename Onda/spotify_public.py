"""Read only the track entity from the public Spotify embed, never its session."""

from html.parser import HTMLParser
import json

from metadata import MetadataError, base_record


class EmbedParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.capture = False
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "script" and dict(attrs).get("id") == "__NEXT_DATA__":
            self.capture = True

    def handle_data(self, data):
        if self.capture:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == "script":
            self.capture = False


def parse_public_track(html, track_id, canonical):
    parser = EmbedParser()
    parser.feed(html)
    try:
        entity = json.loads("".join(parser.parts))["props"]["pageProps"]["state"][
            "data"
        ]["entity"]
        if (
            entity.get("type") != "track"
            or entity.get("id") != track_id
            or not entity.get("title")
        ):
            raise ValueError()
        record = base_record("Spotify", track_id, canonical, "Spotify Embed público")
        duration = entity.get("duration")
        record.update(
            title=entity["title"],
            artists=[
                a["name"]
                for a in entity.get("artists", [])
                if isinstance(a, dict) and a.get("name")
            ],
            duration_ms=(
                duration
                if isinstance(duration, (int, float)) and duration > 0
                else None
            ),
        )
        images = (entity.get("visualIdentity") or {}).get("image") or []
        images = [
            image
            for image in images
            if isinstance(image, dict)
            and isinstance(image.get("url"), str)
            and image["url"].startswith("https://")
        ]
        if images:
            record["cover_url"] = max(
                images, key=lambda image: image.get("maxHeight") or 0
            )["url"]
        if not record["artists"]:
            raise ValueError()
        return record
    except (KeyError, TypeError, ValueError, AttributeError):
        raise MetadataError(
            "Não foi possível identificar título/artista na página pública Spotify."
        ) from None
