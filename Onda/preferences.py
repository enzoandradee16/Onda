"""Non-secret, opt-in preferences. Only explicit UI fields are persisted."""
import json
import os
from pathlib import Path
import tempfile

from engine import MODES, HEIGHTS, MP3_QUALITIES, M4A_QUALITIES, FPS_OPTIONS


class PreferenceStore:
    def __init__(self, path=None):
        root = Path(os.environ["LOCALAPPDATA"]) if os.environ.get("LOCALAPPDATA") else Path.home() / ".config"
        self.path = Path(path) if path is not None else root / "Onda" / "settings.json"

    @staticmethod
    def clean(data):
        if not isinstance(data, dict):
            return {}
        result = {}
        if data.get("mode") in MODES:
            result["mode"] = data["mode"]
        if data.get("height") in HEIGHTS:
            result["height"] = data["height"]
        if data.get("fps") in FPS_OPTIONS:
            result["fps"] = data["fps"]
        if data.get("catalog_provider") in ("Deezer", "Apple / iTunes"):
            result["catalog_provider"] = data["catalog_provider"]
        from file_output import ORGANIZATIONS, DUPLICATES
        if data.get("organization") in ORGANIZATIONS:
            result["organization"] = data["organization"]
        if data.get("duplicates") in DUPLICATES:
            result["duplicates"] = data["duplicates"]
        if type(data.get("review_metadata")) is bool:
            result["review_metadata"] = data["review_metadata"]
        if type(data.get("background_preview")) is bool:
            result["background_preview"] = data["background_preview"]
        from preview_options import PREVIEW_DURATIONS
        for name in ("effects_preview_duration", "search_preview_duration"):
            if data.get(name) in PREVIEW_DURATIONS:
                result[name] = data[name]
        for name in ("folder", "ffmpeg"):
            if isinstance(data.get(name), str) and len(data[name]) <= 32768 and "\x00" not in data[name]:
                if data[name].strip() or name == "ffmpeg":
                    result[name] = data[name]
        from playlist_options import PLAYLIST_LIMITS
        if data.get("playlist_limit") in PLAYLIST_LIMITS:
            result["playlist_limit"] = data["playlist_limit"]
        if type(data.get("playlist")) is bool:
            result["playlist"] = data["playlist"]
        for name, choices in (("mp3_quality", MP3_QUALITIES), ("m4a_quality", M4A_QUALITIES)):
            if data.get(name) in choices:
                result[name] = data[name]
        return result

    def load(self):
        if not self.path.exists():
            return None
        try:
            if self.path.stat().st_size > 131072:
                raise ValueError()
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or data.get("version") != 1 or data.get("remember") is not True:
                raise ValueError()
            return self.clean(data)
        except (OSError, ValueError, TypeError):
            raise ValueError("Não foi possível carregar as configurações. Os padrões foram usados.") from None

    def save(self, values):
        data = {"version": 1, "remember": True, **self.clean(values)}
        temporary = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.path.parent, prefix="settings-", suffix=".tmp", delete=False) as output:
                temporary = Path(output.name)
                json.dump(data, output, ensure_ascii=False, indent=2)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, self.path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def forget(self):
        self.path.unlink(missing_ok=True)
