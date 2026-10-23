import ast, json, re, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from i18n import catalog, tr, set_language

class CatalogCompletenessTests(unittest.TestCase):
    def tearDown(self): set_language("pt-BR")
    def test_catalog_parity_placeholders_and_brand(self):
        self.assertEqual(set(catalog("en")),set(catalog("es")))
        for lang in ("en","es"):
            for key,value in catalog(lang).items():
                self.assertTrue(value.strip(),(lang,key))
                self.assertEqual(set(re.findall(r"\{\w+\}",key)),set(re.findall(r"\{\w+\}",value)),(lang,key))
            self.assertEqual(tr("ONDA",lang),"ONDA")
    def test_every_literal_translated_ui_call_is_covered(self):
        unchanged={"Zoom","Slowed · Sped Up · Reverb","Preset","Cards","Client ID","Client Secret","TXT (links)","Slowed / Sped Up","ONDA","LINKS"}
        missing=[]
        for path in Path(__file__).parent.glob("*.py"):
            if path.name.startswith("test_"): continue
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8-sig"))):
                if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=="tr" and node.args and isinstance(node.args[0],ast.Constant) and isinstance(node.args[0].value,str):
                    text=node.args[0].value
                    if len(text)>3 and re.search("[A-Za-z]",text) and text not in unchanged:
                        for lang in ("en","es"):
                            if text not in catalog(lang):missing.append((path.name,node.lineno,lang,text))
        self.assertFalse(missing,"Missing translations: "+repr(missing))
    def test_reset_labels_and_live_backend_messages(self):
        from reset_settings import GROUPS
        for lang in ("en","es"):
            for group,fields in GROUPS.items():
                self.assertIn(group,catalog(lang))
                for label in fields.values(): self.assertTrue(label in catalog(lang),(lang,label))
            for message in ("Discovery · 14 itens. Álbum Spotify via API; ordem e edição originais.","12 itens adicionados à fila","5 itens","Lista da playlist · Discovery · 14 itens","Não foi possível baixar o FLAC do Monochrome (HTTP 503). Tente mais tarde."):
                self.assertNotEqual(tr(message,lang),message,(lang,message))
            self.assertEqual(tr("Artist · Song · Original Album",lang),"Artist · Song · Original Album")
    def test_metadata_notes_are_translated_without_changing_track_names(self):
        from metadata_ui import MetadataWindow
        for lang in ("en","es"):
            set_language(lang)
            record={"title":"Minha música","artists":["Meu artista"],"method":"Deezer API pública","notes":["Álbum Spotify via API; ordem e edição originais."]}
            output=[]
            fake=SimpleNamespace(selected_record=lambda:record,source_button=MagicMock(),cover_button=MagicMock(),set_details=output.append)
            MetadataWindow.select(fake)
            self.assertIn("Minha música",output[0]);self.assertIn("Meu artista",output[0])
            self.assertIn(tr(record["notes"][0]),output[0]);self.assertNotIn(record["notes"][0],output[0])

    def test_static_errors_and_android_ui_literals_are_covered(self):
        from i18n import patterns
        root=Path(__file__).resolve().parents[1]
        def covered(text,language):
            return text in catalog(language) or any(pattern.fullmatch(text) for pattern,_,_ in patterns(language))
        missing=[]
        for path in list((root/"Onda").glob("*.py"))+list((root/"Android/app/src/main/python").glob("*.py")):
            if path.name.startswith("test_"): continue
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8-sig"))):
                if not (isinstance(node,ast.Raise) and isinstance(node.exc,ast.Call) and node.exc.args): continue
                value=node.exc.args[0]
                if isinstance(value,ast.Constant) and isinstance(value.value,str): text=value.value
                elif isinstance(value,ast.JoinedStr): text="".join(part.value if isinstance(part,ast.Constant) else "{argument}" for part in value.values)
                else: continue
                if len(text)>3:
                    for language in ("en","es"):
                        if not covered(text,language):missing.append((path.name,node.lineno,language,text))
        for path in (root/"Android/app/src/main/java").rglob("*.kt"):
            for match in re.finditer(r'UiText\("([^"$]*)"',path.read_text(encoding="utf8")):
                text=match.group(1)
                if len(text)>3 and text not in {"Zoom","ONDA","Client ID"}:
                    for language in ("en","es"):
                        if not covered(text,language):missing.append((path.name,language,text))
        self.assertFalse(missing,"Missing translations: "+repr(missing))

    def test_qml_literal_translations_are_covered(self):
        from i18n import patterns
        missing=[]
        for path in (Path(__file__).parent/'qml').glob('*.qml'):
            for match in re.finditer(r'bridge\.translate\("((?:[^"\\]|\\.)*)"\)',path.read_text(encoding='utf-8')):
                text=json.loads('"'+match[1]+'"')
                if len(text)<=3:continue
                for language in ('en','es'):
                    if text not in catalog(language) and not any(pattern.fullmatch(text) for pattern,_,_ in patterns(language)):
                        missing.append((path.name,language,text))
        self.assertFalse(missing,'Missing QML translations: '+repr(missing))

    def test_update_confirmation_translates_question_and_preserves_asset_name(self):
        import queue
        from app import App
        from unittest.mock import patch
        for language,expected in (("en","Open the official download?"),("es","¿Abrir la descarga oficial?")):
            set_language(language)
            events=queue.Queue()
            filename="ONDA-Configurações-1.1.1.exe"
            events.put((None,{"type":"app_update","result":{"available":True,"message":"Nova versão disponível: "+filename,"url":"https://example.com/update"}}))
            fake=SimpleNamespace(events=events,after=MagicMock(),poll_events=MagicMock(),refresh_queue_timing=MagicMock())
            with patch("app.messagebox.askyesno",return_value=False) as ask:
                App.poll_events(fake)
            message=ask.call_args.args[1]
            self.assertTrue(message.endswith("\n"+expected),message)
            self.assertIn(filename,message)
            self.assertNotIn("Abrir o download oficial?",message)
