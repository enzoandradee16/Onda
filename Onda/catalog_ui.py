"""Search → catalog result → preview and format → existing download queue."""
from i18n import tr
from i18n_tk import TranslatedCombobox, display_var
import base64
from functools import lru_cache
import io
import os
from pathlib import Path
import queue
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import ttk
from urllib.parse import urlsplit
import webbrowser

from engine import MP3_QUALITIES, M4A_QUALITIES
from metadata import MetadataClient, is_streaming_link
from catalog_match import CatalogChoiceRequired
from size_estimate import estimate_size


def executable(name, folder=""):
    candidate = Path(folder) / (name + ".exe" if os.name == "nt" else name)
    return str(candidate) if folder and candidate.is_file() else shutil.which(name)


def media_args():
    return {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}


def cover_png(url, folder=""):
    # Folder remains accepted for callers; thumbnail rendering needs no FFmpeg.
    return cached_cover_png(url)


@lru_cache(maxsize=48)
def cached_cover_png(url):
    from PIL import Image
    from tagging import fetch_cover
    cover = fetch_cover(url)
    if not cover:
        return None
    with Image.open(io.BytesIO(cover[0])) as image:
        image.thumbnail((124, 124), Image.Resampling.LANCZOS)
        output = io.BytesIO()
        image.convert("RGBA").save(output, format="PNG")
        return output.getvalue()


class CatalogPane(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=(0, 18, 0, 0))
        self.app = app
        self.records = []
        self.messages = queue.Queue()
        self.generation = 0
        self.search_cancel = threading.Event()
        self.cover_generation = 0
        self.closed = False
        self.player = None
        self.photo = None
        self.dialog = None
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)
        ttk.Label(self, text=tr("Encontre sua próxima música."), font=("Segoe UI", 22, "bold"), anchor="center").grid(row=0, column=0, sticky="ew")
        ttk.Label(self, text=tr("Pesquise artista ou música, ou cole um link de faixa."), style="Muted.TLabel", anchor="center").grid(row=1, column=0, sticky="ew", pady=(5, 18))
        search = ttk.Frame(self)
        search.grid(row=2, column=0, sticky="ew", pady=(0, 14))
        search.columnconfigure(0, weight=1)
        self.query = tk.StringVar()
        self.entry = ttk.Entry(search, textvariable=self.query)
        self.entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.entry.bind("<Return>", self.enter_search)
        self.entry.bind("<KP_Enter>", self.enter_search)
        self.provider = app.catalog_provider
        TranslatedCombobox(search, textvariable=self.provider, values=("Todos", "Deezer", "Apple / iTunes", "Spotify"), state="readonly", width=15).grid(row=0, column=1, padx=(0, 10))
        self.search_button = ttk.Button(search, text=tr("Pesquisar"), style="Accent.TButton", command=self.search)
        self.search_button.grid(row=0, column=2)
        ttk.Button(search,text=tr('Filtros'),command=self.search_filters).grid(row=0,column=3,padx=(8,0))
        ttk.Button(search,text=tr('Atualizar busca'),command=self.refresh_search).grid(row=1,column=3,pady=(8,0))
        self.spotify_connect_button = ttk.Button(search, text=tr('Conectar Spotify'), command=lambda: self.app.playlist_page.connect_spotify())
        self.spotify_connect_button.grid(row=1, column=0, columnspan=3, sticky='e', pady=(8, 0))
        def provider_changed(*_):
            if self.provider.get() == 'Spotify':
                self.spotify_connect_button.grid()
            else:
                self.spotify_connect_button.grid_remove()
        self.provider_trace = self.provider.trace_add('write', provider_changed)
        provider_changed()


        panel = ttk.Frame(self)
        panel.grid(row=3, column=0, sticky="nsew")
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(0, weight=1)
        self.table = ttk.Treeview(panel, columns=("title", "artist", "album", "duration"), show="headings", selectmode="browse", height=6)
        from list_context import bind_catalog
        bind_catalog(self)
        for key, label, width in (("title", "MÚSICA / VERSÃO", 260), ("artist", "ARTISTA", 150), ("album", "ÁLBUM", 220), ("duration", "DURAÇÃO", 90)):
            self.table.heading(key, text=tr(label), anchor="w")
            self.table.column(key, width=width, minwidth=70, stretch=key != "duration")
        self.table.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(panel, command=self.table.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.table.configure(yscrollcommand=scroll.set)
        self.table.bind("<<TreeviewSelect>>", self.selected)
        self.table.bind("<Double-1>", self.open_clicked)
        self.table.bind("<Return>", lambda _: self.open_track())
        self.empty = ttk.Frame(panel, style="Card.TFrame")
        ttk.Label(self.empty, text=tr("Sua biblioteca começa com uma busca"), style="Card.TLabel", font=("Segoe UI", 12, "bold")).pack()
        ttk.Label(self.empty, text=tr("Encontre a música e escolha a versão que você quer."), style="CardMuted.TLabel").pack(pady=(5, 0))
        self.empty.place(relx=.5, rely=.55, anchor="center")

        card = ttk.Frame(self, style="Card.TFrame", padding=14)
        card.grid(row=4, column=0, sticky="ew", pady=(14, 10))
        card.columnconfigure(1, weight=1)
        self.art = ttk.Label(card, text=tr("♪"), style="CardMuted.TLabel", font=("Segoe UI", 38), anchor="center", width=4)
        self.art.grid(row=0, column=0, rowspan=4, sticky="ns", padx=(0, 16))
        self.track_title = tk.StringVar(value=tr("Escolha uma música nos resultados"))
        self.track_info = tk.StringVar(value=tr("Capa, álbum e metadados acompanham o arquivo."))
        self.title_label = ttk.Label(card, textvariable=self.track_title, style="Card.TLabel", font=("Segoe UI", 12, "bold"), wraplength=560)
        self.title_label.grid(row=0, column=1, sticky="w")
        self.platform_label=ttk.Label(card,style="CardMuted.TLabel",padding=(0,0,6,0))
        self.platform_label.grid(row=2,column=1,sticky="w",pady=(4,10))
        self.info_label = ttk.Label(card, textvariable=self.track_info, style="CardMuted.TLabel", wraplength=560)
        self.info_label.grid(row=1, column=1, sticky="w", pady=(4, 0))
        actions = ttk.Frame(card, style="Card.TFrame")
        actions.grid(row=3, column=1, sticky="ew")
        self.preview_button = ttk.Button(actions, text=tr("Ouvir prévia"), command=self.preview, state="disabled")
        self.preview_button.pack(side="left")
        self.source_button = ttk.Button(actions, text=tr("Ver no catálogo"), command=self.open_source, state="disabled")
        self.source_button.pack(side="left", padx=8)
        ttk.Button(actions,text=tr('Comparar resultados'),command=self.compare_results).pack(side='left')
        self.download_button = ttk.Button(actions, text=tr("Baixar…"), style="Accent.TButton", command=self.open_track, state="disabled")
        self.download_button.pack(side="right")
        self.status = tk.StringVar(value="Busque pelo nome. Exemplo: Stardust Music Sounds Better With You")
        self.status_label = ttk.Label(self, textvariable=display_var(self.status), style="Muted.TLabel", wraplength=760)
        self.status_label.grid(row=5, column=0, sticky="w")
        ttk.Label(self, text=tr("Catálogo e capa: plataforma selecionada  •  Áudio: YouTube / FLAC: Monochrome"), style="Muted.TLabel").grid(row=6, column=0, sticky="w", pady=(8, 0))
        self.bind("<Configure>", self.resize)
        self.poll_id = self.after(100, self.poll)

    def resize(self, event):
        width = max(300, event.width - 210)
        self.title_label.configure(wraplength=width)
        self.info_label.configure(wraplength=width)
        self.status_label.configure(wraplength=max(300, event.width - 20))

    def enter_search(self, _event=None):
        # Holding Enter must not toggle the running search into cancellation.
        if self.search_button.cget("text") != tr("Cancelar"):
            self.query.set(self.query.get().replace("\r", " ").replace("\n", " ").strip())
            self.search()
        return "break"

    def search(self):
        if self.search_button.cget("text") == tr("Cancelar"):
            self.generation += 1
            self.search_cancel.set()
            self.search_button.configure(text=tr("Pesquisar"))
            self.status.set("Pesquisa cancelada.")
            return
        query = self.query.get().strip()
        if not query:
            self.status.set("Digite o nome de uma música, artista ou um link de faixa.")
            self.entry.focus_set()
            return
        if not is_streaming_link(query) and (query.startswith("http:") or query.startswith("https:")):
            self.app.pages.select(self.app.download_page)
            self.app.urls.insert("end", query + "\n")
            self.app.refresh_placeholder()
            return
        self.stop_preview()
        self.generation += 1
        self.search_cancel.set()
        self.search_cancel = threading.Event()
        cancel = self.search_cancel
        generation = self.generation
        provider = self.provider.get()
        account = self.app.spotify_account
        credentials = (self.app.spotify_client_id.get(), self.app.spotify_client_secret.get())
        automatic_metadata = self.app.auto_metadata.get()
        refresh = getattr(self,'refresh_requested',False)
        self.refresh_requested = False
        self.search_button.configure(text=tr("Cancelar"))
        self.status.set("Consultando o catálogo…")
        def worker():
            client = MetadataClient(*credentials)
            client.cancelled = cancel.is_set
            if account.connected:client.spotify_get=account.get
            try:
                from music_search import search_music
                records = search_music(client,query,provider,account=account,cancelled=cancel.is_set,
                                       automatic=automatic_metadata,refresh=refresh)
                self.messages.put(("search", generation, records))
            except CatalogChoiceRequired as exc:
                self.messages.put(("catalog_choice", generation, (exc.anchor, exc.candidates)))
            except Exception as exc:
                self.messages.put(("error", generation, str(exc)))
            finally:
                client.close()
        threading.Thread(target=worker, daemon=True).start()

    def refresh_search(self):
        from music_search import clear_cache
        clear_cache()
        if self.search_button.cget('text') == tr('Cancelar'):
            self.search()
        self.refresh_requested = True
        self.search()

    def compare_results(self):
        if len(self.records)<2:
            self.status.set(tr('Busque pelo menos dois resultados para comparar.'))
            return
        dialog=tk.Toplevel(self);dialog.title(tr('Comparar resultados'));dialog.transient(self.winfo_toplevel())
        body=ttk.Frame(dialog,padding=16);body.pack(fill='both',expand=True)
        labels=[str(i+1)+'. '+str(row.get('title'))+' · '+', '.join(row.get('artists') or []) for i,row in enumerate(self.records)]
        left,right=tk.StringVar(value=labels[0]),tk.StringVar(value=labels[1])
        for column,var in enumerate((left,right)):
            ttk.Combobox(body,textvariable=var,values=labels,state='readonly',width=42).grid(row=0,column=column,padx=6,pady=6)
        text=tk.Text(body,width=90,height=14,wrap='word');text.grid(row=1,column=0,columnspan=2)
        def update(*_):
            a,b=(self.records[labels.index(var.get())] for var in (left,right))
            from duplicate_links import source_key
            source=a.get('source_url')
            if a is b or (source and source_key(source)==source_key(b.get('source_url'))):
                text.configure(state='normal');text.delete('1.0','end')
                text.insert('1.0',tr('Essa música já foi selecionada. Escolha outro resultado para comparar.'))
                text.configure(state='disabled')
                return
            from edition_evidence import differences
            lines=[]
            for key,label in (('title','Título'),('artists','Artistas'),('album','Álbum'),('release_date','Data'),('duration_ms','Duração (ms)'),('isrc','ISRC'),('platform','Catálogo')):
                values=[', '.join(row.get(key) or []) if key=='artists' else str(row.get(key) or '—') for row in (a,b)]
                lines.append(tr(label)+': '+values[0]+'  |  '+values[1])
            lines.extend(['','; '.join(differences(a,b)) or tr('Sem divergências explícitas; isso não comprova a mesma gravação.')])
            text.configure(state='normal');text.delete('1.0','end');text.insert('1.0','\n\n'.join(lines));text.configure(state='disabled')
        left.trace_add('write',update);right.trace_add('write',update);update()

    def search_filters(self):
        dialog=tk.Toplevel(self)
        dialog.title(tr('Filtros da busca'))
        dialog.transient(self.winfo_toplevel())
        body=ttk.Frame(dialog,padding=16);body.pack(fill='both',expand=True)
        variables={}
        for index,(key,label) in enumerate((('artista','Artista'),('titulo','Título'),('album','Álbum'),('versao','Versão'),('ano','Ano ou intervalo'),('duracao','Duração ou intervalo'))):
            ttk.Label(body,text=tr(label)).grid(row=index,column=0,sticky='w',padx=6,pady=5)
            variables[key]=tk.StringVar()
            ttk.Entry(body,textvariable=variables[key],width=32).grid(row=index,column=1)
        exact=tk.BooleanVar()
        ttk.Checkbutton(body,text=tr('Exatamente este título'),variable=exact).grid(row=6,column=0,columnspan=2,sticky='w')
        ttk.Label(body,text='ano:2020-2022 · duracao:3:00-4:00',style='Muted.TLabel').grid(row=7,column=0,columnspan=2,pady=8)
        def apply():
            import re
            query=re.sub(r'(?<!\S)(?:artista|artist|titulo|title|album|versao|version|ano|year|duracao|duration|exata|exact):("[^"]*"|\S+)','',self.query.get()).strip()
            parts=[query]+[key+':"'+value.get().replace('"','').strip()+'"' for key,value in variables.items() if value.get().strip()]
            if exact.get():parts.append('exata:sim')
            self.query.set(' '.join(filter(None,parts)))
            dialog.destroy()
            if self.search_button.cget('text')==tr('Cancelar'):self.search()
            self.search()
        ttk.Button(body,text=tr('Pesquisar'),command=apply).grid(row=8,column=1,sticky='e')

    def current(self):
        selection = self.table.selection()
        return self.records[int(selection[0])] if selection else None

    def selected(self, _=None):
        self.stop_preview()
        self.cover_generation += 1
        record = self.current()
        for button in (self.download_button, self.source_button):
            button.configure(state="normal" if record else "disabled")
        self.preview_button.configure(state="normal" if record and record.get("preview_url") else "disabled")
        self.art.configure(image="", text=tr("♪"))
        self.photo = None
        from metadata_badges import apply_badge,provider,NAMES
        apply_badge(self.platform_label,record or {},text=NAMES.get(provider(record),(record or {}).get("platform","")))
        if not record:
            self.track_title.set(tr("Escolha uma música nos resultados"))
            self.track_info.set(tr("Capa, álbum e metadados acompanham o arquivo."))
            return
        self.track_title.set(record.get("title") or tr("Música"))
        artist_album=" — ".join(filter(None,[", ".join(record.get("artists", [])),record.get("album")]))
        self.track_info.set(" · ".join(filter(None,[artist_album,record.get("release_date"),'; '.join(record.get("match_reasons") or [])])))
        if record.get("cover_url"):
            generation, url = self.cover_generation, record["cover_url"]
            def worker():
                try:
                    self.messages.put(("cover", generation, cover_png(url)))
                except Exception:
                    self.messages.put(("cover", generation, None))
            threading.Thread(target=worker, daemon=True).start()

    def open_clicked(self, event):
        row = self.table.identify_row(event.y)
        if row:
            self.table.selection_set(row)
            self.open_track()
        return "break"

    def open_track(self):
        record = self.current()
        if not record:
            return
        self.stop_preview()
        if self.dialog is not None and self.dialog.winfo_exists():
            self.dialog.destroy()
        self.dialog = TrackDialog(self.app, record, self.photo)

    def open_source(self):
        record = self.current()
        if record:
            webbrowser.open(record["source_url"])

    def preview(self):
        if self.player:
            self.stop_preview()
            return
        record = self.current()
        url = (record or {}).get("preview_url")
        if not url or urlsplit(url).scheme != "https":
            self.status.set("Prévia indisponível para esta faixa.")
            return
        ffplay = executable("ffplay", self.app.ffmpeg.get())
        if not ffplay:
            self.status.set("Configure uma pasta do FFmpeg com ffplay para ouvir a prévia aqui.")
            return
        try:
            from preview_options import preview_seconds
            duration = preview_seconds(self.app.search_preview_duration.get())
            self.player = subprocess.Popen([ffplay, "-nodisp", "-autoexit", "-loglevel", "error", "-t", str(duration), url],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, **media_args())
            self.preview_button.configure(text=tr("Parar prévia"))
            self.status.set(f"Ouvindo prévia de até {duration} segundos do catálogo; limitada ao trecho disponível.")
        except (OSError, ValueError):
            self.status.set("Não foi possível iniciar a prévia. Confira o FFmpeg e a duração nas configurações.")

    def stop_preview(self):
        if self.player:
            player, self.player = self.player, None
            def reap():
                try:
                    if player.poll() is None:
                        player.terminate()
                    player.communicate(timeout=5)
                except (OSError, subprocess.TimeoutExpired):
                    player.kill()
                    player.communicate()
            threading.Thread(target=reap, daemon=True).start()
        self.preview_button.configure(text=tr("Ouvir prévia"))

    def poll(self):
        if self.closed:
            return
        for _ in range(40):
            try:
                kind, generation, value = self.messages.get_nowait()
            except queue.Empty:
                break
            if kind == "cover":
                if generation == self.cover_generation and value:
                    try:
                        self.photo = tk.PhotoImage(data=base64.b64encode(value))
                        self.art.configure(image=self.photo, text=tr(""), width=0)
                    except tk.TclError:
                        pass
                continue
            if generation != self.generation:
                continue
            self.search_button.configure(text=tr("Pesquisar"))
            if kind == "catalog_choice":
                from catalog_picker import CatalogPicker, picker_event
                anchor, candidates = value
                if self.dialog is not None and self.dialog.winfo_exists():
                    self.dialog.destroy()
                self.dialog = CatalogPicker(self.app, picker_event(anchor, candidates),
                    lambda url, a=anchor, c=candidates, g=generation: self.confirm_catalog(a, c, url, g),
                    self.cancel_catalog)
                self.status.set("Confirme a faixa do catálogo que corresponde ao link Spotify.")
                continue
            if kind == "error":
                self.status.set(value)
                continue
            details=value if isinstance(value,dict) else {}
            value=details.get('tracks',[]) if details else value
            self.records = value
            self.table.delete(*self.table.get_children())
            self.selected()
            if value:
                self.empty.place_forget()
            else:
                self.empty.place(relx=.5, rely=.55, anchor="center")
            for index, record in enumerate(value):
                seconds = (record.get("duration_ms") or 0) // 1000
                duration = f"{seconds//60}:{seconds%60:02}" if seconds else "—"
                self.table.insert("", "end", iid=str(index), values=(record.get("title"), ", ".join(record.get("artists", [])), record.get("album") or "—", duration))
            self.status.set(f"{len(value)} resultado(s). Selecione uma faixa para ouvir ou baixar." if value else "Nenhuma música encontrada. Tente outro nome ou catálogo.")
            extra=details.get('warnings',[])+(['Sugestões: '+', '.join(details['suggestions'])] if details.get('suggestions') else [])
            if extra:self.status.set(self.status.get()+' '+'; '.join(extra))
            if value:
                self.table.selection_set("0")
        if self.player and self.player.poll() is not None:
            code = self.player.returncode
            self.player.communicate()
            self.player = None
            self.preview_button.configure(text=tr("Ouvir prévia"))
            self.status.set("Prévia concluída." if code == 0 else "Não foi possível reproduzir a prévia desta faixa.")
        self.poll_id = self.after(100, self.poll)

    def cancel_catalog(self):
        self.generation += 1
        if self.dialog is not None and self.dialog.winfo_exists():
            self.dialog.destroy()
        self.dialog = None
        self.status.set("Escolha de metadados cancelada.")

    def confirm_catalog(self, anchor, candidates, url, generation):
        if generation != self.generation:
            if self.dialog is not None and self.dialog.winfo_exists():
                self.dialog.destroy()
            return
        candidate = next((row for row in candidates if row["source_url"] == url), None)
        if not candidate:
            return
        self.dialog.destroy()
        self.dialog = None
        self.search_button.configure(text=tr("Cancelar"))
        self.status.set("Obtendo os metadados completos da faixa escolhida…")
        def worker():
            client = MetadataClient()
            try:
                record = client.confirm_catalog(anchor, candidate)
                self.messages.put(("search", generation, [record]))
            except Exception as exc:
                self.messages.put(("error", generation, str(exc)))
            finally:
                client.close()
        threading.Thread(target=worker, daemon=True).start()

    def shutdown(self):
        self.provider.trace_remove("write", self.provider_trace)
        if self.closed:
            return
        self.closed = True
        self.search_cancel.set()
        self.after_cancel(self.poll_id)
        self.stop_preview()


class TrackDialog(tk.Toplevel):
    def __init__(self, app, record, photo=None):
        super().__init__(app)
        self.app, self.record, self.photo = app, record, photo
        self.title(tr("Onda • Escolha o formato"))
        self.configure(bg="#101419")
        self.geometry("650x610")
        self.minsize(610, 580)
        self.transient(app)
        from settings_scroll import SettingsCategory
        scroll=SettingsCategory(self,"#101419",padding=24)
        scroll.pack(fill="both",expand=True)
        self.bind("<MouseWheel>",scroll.wheel)
        body=scroll.content
        body.columnconfigure(0, weight=1)
        body.rowconfigure(5, weight=1)
        header = ttk.Frame(body)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        if photo:
            ttk.Label(header, image=photo).pack(side="left", padx=(0, 16))
        info = ttk.Frame(header)
        info.pack(side="left", fill="x", expand=True)
        ttk.Label(info, text=record.get("title") or tr("Música"), font=("Segoe UI", 16, "bold"), wraplength=410).pack(anchor="w")
        ttk.Label(info, text=", ".join(record.get("artists", [])), style="Muted.TLabel", wraplength=410).pack(anchor="w", pady=(5, 0))
        ttk.Label(info, text=record.get("album") or tr("Álbum não informado"), style="Muted.TLabel", wraplength=410).pack(anchor="w")
        self.preset = tk.StringVar(value="MP3 320")
        self.presets = {"MP3 320": ("mp3", "320 kbps"), "MP3 128": ("mp3", "128 kbps"), "FLAC": ("flac", None), "Personalizar": ("m4a", "256 kbps")}
        options = ttk.Frame(body, style="Card.TFrame", padding=12)
        options.grid(row=1, column=0, sticky="ew")
        for key, explanation in (("MP3 320", "Alta qualidade · maior compatibilidade"), ("MP3 128", "Arquivo menor · economiza espaço"), ("FLAC", "Monochrome · FLAC direto quando disponível"), ("Personalizar", "Escolher MP3 ou M4A e outro bitrate")):
            ttk.Radiobutton(options, text=f"{key}   ·   {tr(explanation)}", variable=self.preset, value=key, command=self.update_format).pack(anchor="w", pady=6)
        custom = ttk.Frame(body)
        custom.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        self.format = tk.StringVar(value="M4A")
        self.quality = tk.StringVar(value="256 kbps")
        from simple_download_ui import bind_simple_grid
        bind_simple_grid(app,options)
        bind_simple_grid(app,custom)
        self.format_box = TranslatedCombobox(custom, textvariable=self.format, values=("MP3", "M4A"), state="disabled", width=10)
        self.format_box.pack(side="left", padx=(0, 10))
        self.quality_box = TranslatedCombobox(custom, textvariable=self.quality, values=M4A_QUALITIES, state="disabled", width=15)
        self.quality_box.pack(side="left")
        self.format_box.bind("<<ComboboxSelected>>", self.update_format)
        self.quality_box.bind("<<ComboboxSelected>>", self.update_estimate)
        self.estimate = tk.StringVar()
        ttk.Label(body, textvariable=display_var(self.estimate), foreground="#79e2c4").grid(row=3, column=0, sticky="w", pady=(12, 8))
        self.feedback = tk.StringVar(value="Inclui capa e metadados disponíveis. MP3/M4A usam YouTube; FLAC usa Monochrome.")
        ttk.Label(body, textvariable=display_var(self.feedback), style="Muted.TLabel", wraplength=550).grid(row=4, column=0, sticky="w")
        controls = ttk.Frame(body)
        controls.grid(row=6, column=0, sticky="ew", pady=(12, 0))
        ttk.Button(controls, text=tr("Voltar"), command=self.destroy).pack(side="left")
        ttk.Button(controls, text=tr("Adicionar à fila"), command=lambda: self.submit(False)).pack(side="right", padx=(8, 0))
        ttk.Button(controls, text=tr("Baixar agora"), style="Accent.TButton", command=lambda: self.submit(True)).pack(side="right")
        self.update_format()

    def choice(self):
        if self.app.simple_download_ui.get():
            from download_defaults import effective_download
            config=effective_download({'url':self.record['source_url'],'mode':MODES[self.app.mode.get()],'simple_download_ui':True})
            return config['mode'],config['audio_quality']
        return (self.format.get().lower(), self.quality.get()) if self.preset.get() == "Personalizar" else self.presets[self.preset.get()]

    def update_format(self, _=None):
        custom = self.preset.get() == "Personalizar"
        for box in (self.format_box, self.quality_box):
            box.configure(state="readonly" if custom else "disabled")
        choices = MP3_QUALITIES if self.format.get() == "MP3" else M4A_QUALITIES
        self.quality_box.configure(values=choices)
        if self.quality.get() not in choices:
            self.quality.set(choices[0])
        self.update_estimate()

    def update_estimate(self, _=None):
        from app import readable_bytes
        mode, quality = self.choice()
        size, _ = estimate_size({"duration": (self.record.get("duration_ms") or 0) / 1000}, {"mode": mode, "audio_quality": quality})
        self.estimate.set("Tamanho estimado: ≈ " + readable_bytes(size) if size is not None else "Tamanho variável · valor real mostrado ao concluir")

    def submit(self, start):
        mode, quality = self.choice()
        if self.app.queue_catalog(self.record, mode, quality, start):
            self.destroy()
        else:
            self.feedback.set("A faixa já está na fila nesse formato, ou falta configurar a pasta de destino.")
