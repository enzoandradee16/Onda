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

    def remember_enabled(self):
        if self.path.exists():
            return True
        try:
            return json.loads(self.path.with_name("remember.json").read_text(encoding="utf-8")) is not False
        except (OSError, ValueError, TypeError):
            return True

    def load_language(self):
        try:
            value = json.loads(self.path.with_name("language.json").read_text(encoding="utf-8"))
            return value if value in ("pt-BR", "es", "en") else "pt-BR"
        except (OSError, ValueError, TypeError):
            return "pt-BR"

    def save_language(self, value):
        if value not in ("pt-BR", "es", "en"):
            raise ValueError("Idioma inválido.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name("language.json.tmp")
        try:
            temporary.write_text(json.dumps(value), encoding="utf-8")
            temporary.replace(self.path.with_name("language.json"))
        finally:
            temporary.unlink(missing_ok=True)

    DISPLAY_FIELDS = ("queue_view", "queue_card_size", "history_view", "history_card_size", "catalog_card_size", "playlist_card_size")

    def load_display(self):
        try:
            data = self.clean(json.loads(self.path.with_name("display.json").read_text(encoding="utf-8")))
            return {key: data[key] for key in self.DISPLAY_FIELDS if key in data}
        except (OSError, ValueError, TypeError):
            return {}

    def save_display(self, values):
        data = self.clean(values)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        target = self.path.with_name("display.json")
        temporary = target.with_suffix(".json.tmp")
        try:
            temporary.write_text(json.dumps({key: data[key] for key in self.DISPLAY_FIELDS if key in data}), encoding="utf-8")
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)

    @staticmethod
    def clean(data):
        if not isinstance(data, dict):
            return {}
        extras={}
        if type(data.get("minimize_on_miniplayer")) is bool:extras["minimize_on_miniplayer"]=data["minimize_on_miniplayer"]
        if data.get('lyrics_animation') in ('Desativada','Suave','Deslizar','Zoom'):extras['lyrics_animation']=data['lyrics_animation']
        if type(data.get('sidebar_width')) in (int,float):
            try:extras['sidebar_width']=max(160,min(420,int(data['sidebar_width'])))
            except (ValueError,OverflowError):pass
        if type(data.get('playback_queue_width')) in (int,float):
            try:extras['playback_queue_width']=max(360,min(900,int(data['playback_queue_width'])))
            except (ValueError,OverflowError):pass
        from jukebox_equalizer import clean as clean_equalizer
        from shortcut_options import load_overrides
        result_shortcuts=json.dumps(load_overrides(data.get("shortcut_keys","{}")))
        client_id=data.get("spotify_client_id")
        from advanced_options import clean_advanced,PC_DEFAULTS
        result = {key:value for key,value in clean_advanced(data).items() if key in PC_DEFAULTS}
        result.update(extras)
        if isinstance(client_id,str) and len(client_id)<=4096:result["spotify_client_id"]=client_id.strip()
        result["confirm_version"]=False
        from performance import clean as clean_performance
        result.update(clean_performance(data))
        if "jukebox_equalizer" in data:result["jukebox_equalizer"]=json.dumps(clean_equalizer(data["jukebox_equalizer"]))
        if "shortcut_keys" in data:result["shortcut_keys"]=result_shortcuts
        if data.get("language") in ("pt-BR", "es", "en"):
            result["language"] = data["language"]
        from interface_spacing import SPACING_MODES
        if data.get("interface_spacing") in SPACING_MODES:
            result["interface_spacing"] = data["interface_spacing"]
        from appearance import THEME_MODES, ACCENTS
        for name, choices in (('theme_mode', THEME_MODES), ('theme_accent', ACCENTS)):
            value = data.get(name)
            if name == 'theme_accent' and value == 'Verde-água':
                value = 'Verde-Água'
            if isinstance(value, str) and value in choices:
                result[name] = value
        if type(data.get("pure_black_separators")) is bool:
            result["pure_black_separators"] = data["pure_black_separators"]
        for name in ("catalog_card_size","playlist_card_size"):
            if data.get(name) in ("Pequeno","Médio","Grande"):result[name]=data[name]
        if data.get("queue_card_size") in ("Pequeno","Médio","Grande"):
            result["queue_card_size"] = data["queue_card_size"]
        if data.get("queue_view") in ("Compacto","Completa"):
            result["queue_view"] = data["queue_view"]
        if data.get("history_card_size") in ("Pequeno","Médio","Grande"):
            result["history_card_size"] = data["history_card_size"]
        if data.get("history_view") in ("Compacto", "Completa"):
            result["history_view"] = data["history_view"]
        from status_notice import NOTICE_DURATIONS
        if isinstance(data.get("notice_duration"),str) and data["notice_duration"] in NOTICE_DURATIONS:
            result["notice_duration"]=data["notice_duration"]
        from interface_fonts import valid_font, FONT_SIZES
        if data.get("interface_font_size") in FONT_SIZES:
            result["interface_font_size"] = data["interface_font_size"]
        if valid_font(data.get('interface_font')):
            result['interface_font'] = 'ONDA Modern' if data['interface_font']=='Padrão do sistema' else data['interface_font']
        if type(data.get('notifications_enabled')) is bool:result['notifications_enabled']=data['notifications_enabled']
        if data.get('playback_tab_order') in ('Efeitos primeiro','Jukebox infinito primeiro'):result['playback_tab_order']=data['playback_tab_order']
        if 'jukebox_transition_seconds' in data:
            try:result['jukebox_transition_seconds']=max(1,min(10,int(data['jukebox_transition_seconds'])))
            except (TypeError,ValueError,OverflowError):pass
        if type(data.get('jukebox_gradual_transition')) is bool:result['jukebox_gradual_transition']=data['jukebox_gradual_transition']
        if 'playback_prepare_ahead' in data:
            from playback_preparation import preparation_ahead
            result['playback_prepare_ahead']=preparation_ahead(data['playback_prepare_ahead'])
        if type(data.get('qt_animations')) is bool:result['qt_animations']=data['qt_animations']
        if type(data.get('translucent_effects')) is bool:result['translucent_effects']=data['translucent_effects']
        if type(data.get('effects_keep_pitch')) is bool:
            result['effects_keep_pitch'] = data['effects_keep_pitch']
        from image_output import FORMATS, IMAGE_SIZES
        for name, choices in (('image_format', FORMATS), ('image_size', IMAGE_SIZES)):
            value = data.get(name)
            if isinstance(value, str) and value in choices:
                result[name] = value
        for name in ('image_width', 'image_height'):
            value = data.get(name)
            if isinstance(value, str) and value.isascii() and value.isdecimal() and len(value) <= 5 and 1 <= int(value) <= 16384:
                result[name] = str(int(value))
        if type(data.get('image_keep_ratio')) is bool:
            result['image_keep_ratio'] = data['image_keep_ratio']
        if isinstance(data.get('hidden_tabs'), (list, tuple)):
            from tab_order import normalize_hidden
            result['hidden_tabs'] = normalize_hidden(data['hidden_tabs'])
        if isinstance(data.get('tab_order'), (list, tuple)):
            from tab_order import normalize_order
            result['tab_order'] = normalize_order(data['tab_order'])
        if isinstance(data.get('tab_group_order'), (list, tuple)):
            from tab_order import normalize_group_order
            result['tab_group_order'] = normalize_group_order(data['tab_group_order'])
        for name, choices in (("playlist_mode", {key for key, value in MODES.items() if value not in ("photos", "social")}),
                              ("playlist_height", HEIGHTS), ("playlist_fps", FPS_OPTIONS),
                              ("playlist_mp3_quality", MP3_QUALITIES), ("playlist_m4a_quality", M4A_QUALITIES)):
            if data.get(name) in choices:
                result[name] = data[name]
        if data.get("mode") in MODES:
            result["mode"] = data["mode"]
        if data.get("height") in HEIGHTS:
            result["height"] = data["height"]
        if data.get("fps") in FPS_OPTIONS:
            result["fps"] = data["fps"]
        if data.get("catalog_provider") in ("Todos", "Deezer", "Apple / iTunes", "Spotify"):
            result["catalog_provider"] = data["catalog_provider"]
        from file_output import ORGANIZATIONS, DUPLICATES
        if data.get("organization") in ORGANIZATIONS:
            result["organization"] = data["organization"]
        from output_rules import FILENAME_TEMPLATES
        if data.get("filename_template") in FILENAME_TEMPLATES:
            result["filename_template"] = data["filename_template"]
        if data.get("duplicates") in DUPLICATES:
            result["duplicates"] = data["duplicates"]
        if type(data.get("review_metadata")) is bool:
            result["review_metadata"] = data["review_metadata"]
        if type(data.get("auto_match")) is bool:
            result["auto_match"] = data["auto_match"]
        if type(data.get("jukebox_background")) is bool:
            result["jukebox_background"]=data["jukebox_background"]
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
        from playlist_options import playlist_limit
        try:result["playlist_limit"]=str(playlist_limit(data.get("playlist_limit")))
        except ValueError:pass
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
        self.path.parent.mkdir(parents=True, exist_ok=True)
        target = self.path.with_name("remember.json")
        temporary = target.with_suffix(".json.tmp")
        try:
            temporary.write_text("false", encoding="utf-8")
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
        self.path.unlink(missing_ok=True)
