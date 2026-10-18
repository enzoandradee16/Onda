from i18n import tr
from i18n_tk import TranslatedCombobox, display_var
import queue
import threading
import tkinter as tk
import unicodedata
from tkinter import filedialog, ttk

from engine import MODES, HEIGHTS, FPS_OPTIONS, MP3_QUALITIES, M4A_QUALITIES
from metadata import MetadataClient, is_streaming_link
from playlist_import import load_playlist, load_text
from version_picker import duration_label


def search_text(value):
    return "".join(char for char in unicodedata.normalize("NFKD", str(value).casefold())
                   if not unicodedata.combining(char))


class PlaylistPane(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=(0, 18, 0, 0))
        self.app = app
        self.spotify_account = app.spotify_account
        self.spotify_window = None
        self.list_window = None
        self.url = tk.StringVar()
        self.status = tk.StringVar(value="Álbuns Spotify, Deezer e Apple · playlists Spotify, Deezer e YouTube · limite em Configurações → Downloads.")
        self.confirm_version = tk.BooleanVar(value=True)
        self.records = {}
        self.search_index = {}
        self.filter_text = tk.StringVar()
        self._filter_after = None
        self._render_after = None
        self._render_generation = 0
        self.filter_count = tk.StringVar(value="Carregue um álbum ou playlist")
        self.playlist_title = ""
        self.cover_generation = 0
        self.cover_image = None
        self.events = queue.Queue()
        self.generation = 0
        self.closed = False
        self.busy = False
        self.columnconfigure(0, weight=1)
        self.rowconfigure(6, weight=1, minsize=220)
        ttk.Label(self, text=tr("Seus álbuns e playlists na biblioteca."), font=("Segoe UI", 21, "bold"), anchor="center").grid(row=0, column=0, sticky="ew")
        row = ttk.Frame(self)
        row.grid(row=1, column=0, sticky="ew", pady=18)
        link_row = ttk.Frame(row)
        link_row.pack(fill="x")
        ttk.Entry(link_row, textvariable=self.url).pack(side="left", fill="x", expand=True)
        self.load_button = ttk.Button(link_row, text=tr("Carregar álbum ou playlist"), command=self.load)
        self.load_button.pack(side="left", padx=8)
        tools = ttk.Frame(row)
        tools.pack(fill="x", pady=(10, 0))
        self.import_button = ttk.Button(tools, text=tr("Importar arquivo"), command=self.text_file)
        self.import_button.pack(side="left")
        self.export_button = ttk.Button(tools, text=tr("Exportar lista"), command=self.export_file, state="disabled")
        self.export_button.pack(side="left", padx=8)
        self.spotify_button = ttk.Button(tools, text=tr("Spotify conectado" if self.spotify_account.connected else "Conectar Spotify"), command=self.connect_spotify)
        self.spotify_button.pack(side="left")
        self.list_button = ttk.Button(tools, text=tr("Ver lista"), command=self.show_list, state="disabled")
        self.list_button.pack(side="right")
        from playlist_sync_ui import controls as sync_controls
        sync_controls(self,row)
        ttk.Label(self, textvariable=display_var(self.status), style="Muted.TLabel", wraplength=790, anchor="center", justify="center").grid(row=2, column=0, sticky="ew", pady=(0, 12))
        formats = ttk.Frame(self)
        formats.grid(row=3, column=0, sticky="ew", pady=(0, 12))
        formats.columnconfigure(0, weight=2)
        formats.columnconfigure(1, weight=1)
        formats.columnconfigure(2, weight=1)
        ttk.Label(formats, text=tr("Formato de download"), style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        mode = TranslatedCombobox(formats, textvariable=app.playlist_mode, state="readonly",
                            values=[key for key, value in MODES.items() if value not in ("photos", "social")], width=30)
        mode.grid(row=1, column=0, sticky="ew", padx=(0, 12), pady=(4, 0))
        mode.bind("<<ComboboxSelected>>", self.format_changed)
        self.quality_label = ttk.Label(formats, text=tr("Qualidade de áudio"), style="Muted.TLabel")
        self.quality_label.grid(row=0, column=1, sticky="w")
        self.quality_combo = TranslatedCombobox(formats, state="readonly", width=16)
        self.quality_combo.grid(row=1, column=1, sticky="ew", padx=(0, 12), pady=(4, 0))
        self.fps_label = ttk.Label(formats, text=tr("FPS máximo"), style="Muted.TLabel")
        self.fps_label.grid(row=0, column=2, sticky="w")
        self.fps_combo = TranslatedCombobox(formats, textvariable=app.playlist_fps, values=list(FPS_OPTIONS), state="readonly", width=13)
        self.fps_combo.grid(row=1, column=2, sticky="ew", pady=(4, 0))
        self.format_changed()
        from simple_download_ui import bind_simple_grid
        bind_simple_grid(app,formats)
        self.collection_card = ttk.Frame(self, padding=10, style="Card.TFrame")
        self.collection_card.grid(row=4,column=0,sticky="ew",pady=(0,10))
        self.collection_card.columnconfigure(1,weight=1)
        self.collection_cover=ttk.Label(self.collection_card,text=tr("♫"),style="Card.TLabel",anchor="center",width=8)
        self.collection_cover.grid(row=0,column=0,rowspan=3,padx=(0,12))
        self.collection_name=ttk.Label(self.collection_card,style="Card.TLabel",font=("Segoe UI",18,"bold"))
        self.collection_name.grid(row=0,column=1,sticky="w")
        self.collection_artist=ttk.Label(self.collection_card,style="Card.TLabel",font=("Segoe UI",12,"bold"))
        self.collection_artist.grid(row=1,column=1,sticky="w",pady=(6,4))
        self.collection_detail=ttk.Label(self.collection_card,style="CardMuted.TLabel")
        self.collection_detail.grid(row=2,column=1,sticky="w")
        self.collection_card.grid_remove()
        search = ttk.Frame(self)
        search.grid(row=5, column=0, sticky="ew", pady=(0, 12))
        ttk.Label(search, text=tr("Buscar nesta lista"), style="Muted.TLabel").pack(anchor="w", pady=(0, 6))
        search_row = ttk.Frame(search)
        search_row.pack(fill="x")
        self.search_entry = ttk.Entry(search_row, textvariable=self.filter_text)
        self.search_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(search_row, text=tr("Limpar"), command=lambda: self.filter_text.set("")).pack(side="left", padx=8)
        ttk.Label(search_row, textvariable=display_var(self.filter_count), style="Muted.TLabel").pack(side="right")
        self.search_entry.bind("<Escape>", lambda _: self.filter_text.set(""))
        self.filter_text.trace_add("write", self.schedule_filter)
        panel = ttk.Frame(self)
        panel.grid(row=6, column=0, sticky="nsew")
        self.table = ttk.Treeview(panel, columns=("title", "artist", "duration", "match"), show="headings", selectmode="extended")
        from list_context import bind_playlist
        bind_playlist(self)
        for key, label, width in (("title", "MÚSICA", 270), ("artist", "ARTISTA", 170), ("duration", "DURAÇÃO", 85), ("match", "VERSÃO DE ÁUDIO", 270)):
            self.table.heading(key, text=tr(label))
            self.table.column(key, width=width, minwidth=60, stretch=key in ("title", "match"))
        self.table.pack(side="left", fill="both", expand=True)
        ttk.Scrollbar(panel, command=self.table.yview).pack(side="right", fill="y")
        self.table.configure(yscrollcommand=panel.winfo_children()[-1].set)
        controls = ttk.Frame(self)
        controls.grid(row=7, column=0, sticky="ew", pady=12)
        ttk.Button(controls, text=tr("Selecionar visíveis"), command=lambda: self.table.selection_set(self.table.get_children())).pack(side="left")
        self.check_button = ttk.Button(controls, text=tr("Conferir correspondências"), command=self.check)
        self.check_button.pack(side="left", padx=8)
        self.download_now_button = ttk.Button(controls, text=tr("Baixar agora"), command=lambda: self.add(start=True), style="Accent.TButton")
        self.download_now_button.pack(side="right")
        self.add_button = ttk.Button(controls, text=tr("Adicionar à fila"), command=self.add)
        self.add_button.pack(side="right", padx=(0, 8))
        self.confirm_version_check = ttk.Checkbutton(self, text=tr("Confirmar a versão de cada música antes de baixar"), variable=self.confirm_version)
        self.confirm_version_check.grid(row=8, column=0, sticky="w", pady=6)
        self.auto_match_trace = app.auto_match.trace_add("write", self.sync_auto_match)
        self.sync_auto_match()
        ttk.Label(self, text=tr("Busque por música ou artista. As ações usam somente os itens visíveis selecionados. Formato e qualidade são próprios desta aba. Streaming: FLAC usa Monochrome; MP3/M4A usam YouTube. Vídeo vira MP3 e original vira M4A."), style="Muted.TLabel", wraplength=790).grid(row=9, column=0, sticky="w", pady=8)
        self.poll_id = self.after(100, self.poll)

    def sync_auto_match(self, *_):
        automatic = self.app.auto_match.get()
        self.confirm_version_check.configure(state="disabled" if automatic else "normal",
                    text=tr("Seleção automática ativada em Configurações → Downloads" if automatic else "Confirmar a versão de cada música antes de baixar"))

    def format_changed(self, _=None):
        mode = MODES[self.app.playlist_mode.get()]
        self.quality_label.grid()
        self.quality_combo.grid()
        for widget in (self.fps_label, self.fps_combo):
            widget.grid() if mode in ("video", "mp4") else widget.grid_remove()
        if mode in ("video", "mp4"):
            self.quality_label.configure(text=tr("Resolução máxima"))
            self.quality_combo.configure(textvariable=self.app.playlist_height, values=list(HEIGHTS))
        elif mode in ("mp3", "m4a"):
            self.quality_label.configure(text=tr("Qualidade de áudio"))
            variable = self.app.playlist_mp3_quality if mode == "mp3" else self.app.playlist_m4a_quality
            self.quality_combo.configure(textvariable=variable, values=MP3_QUALITIES if mode == "mp3" else M4A_QUALITIES)
        else:
            self.quality_label.grid_remove()
            self.quality_combo.grid_remove()

    def set_busy(self, value):
        self.busy = value
        for button in (self.load_button, self.check_button, self.add_button, self.download_now_button, self.import_button, self.spotify_button,*self.sync_buttons):
            button.configure(state="disabled" if value else "normal")
        self.sync_buttons[-1].configure(state="normal" if not value and self.sync_result and self.sync_result["counts"]["missing"] else "disabled")
        self.export_button.configure(state="normal" if self.records and not value else "disabled")
        self.list_button.configure(state="normal" if self.records and not value else "disabled")

    def load(self, start_download=False, sync_folder=None):
        if self.busy:
            return
        if self.spotify_window is not None and self.spotify_window.winfo_exists():
            if self.spotify_window.busy:
                self.status.set("Conclua ou cancele a conexão Spotify antes de carregar a playlist.")
                return
            self.spotify_window.close()
        self.generation += 1
        generation, url = self.generation, self.url.get().strip()
        limit = int(self.app.playlist_limit.get())
        credentials = self.app.spotify_client_id.get(), self.app.spotify_client_secret.get()
        self.status.set("Carregando álbum ou playlist…")
        self.set_busy(True)
        def worker():
            client = MetadataClient(*credentials)
            try:
                result=load_playlist(url, client, limit=limit, account=self.spotify_account, cancelled=lambda: self.closed)
                result["_clipboard_download"]=start_download
                result["_collection_url"]=url
                result["_sync_folder"]=sync_folder
                self.events.put((generation, "loaded", result))
            except Exception as exc:
                self.events.put((generation, "error", str(exc)))
            finally:
                client.close()
        threading.Thread(target=worker, daemon=True).start()

    def text_file(self):
        if self.busy:
            return
        path = filedialog.askopenfilename(parent=self.app, filetypes=[(tr("Listas e CSV"), "*.txt *.m3u *.m3u8 *.csv"), (tr("CSV do Exportify"), "*.csv"), ("TXT / M3U", "*.txt *.m3u *.m3u8")])
        if path:
            try:
                from pathlib import Path
                if Path(path).stat().st_size > 10 * 1024 * 1024:
                    raise ValueError("A lista deve ter até 10 MB.")
                from playlist_files import load_csv
                loader = load_csv if Path(path).suffix.lower() == ".csv" else load_text
                result = loader(Path(path).read_text(encoding="utf-8-sig"), limit=int(self.app.playlist_limit.get()))
                result["title"] = Path(path).stem
                self.display(result)
            except (OSError, ValueError) as exc:
                self.status.set(str(exc))

    def show_list(self):
        if self.busy or not self.records:
            return
        if self.list_window is not None and self.list_window.winfo_exists():
            self.list_window.deiconify()
            self.list_window.lift()
            self.list_window.focus_set()
            return
        from playlist_list_ui import PlaylistListWindow
        self.list_window = PlaylistListWindow(self)

    def connect_spotify(self):
        if self.busy:
            return
        if self.spotify_window is not None and self.spotify_window.winfo_exists():
            self.spotify_window.lift()
            return
        from spotify_account_ui import SpotifyConnection
        self.spotify_window = SpotifyConnection(self)

    def export_file(self):
        if self.busy or not self.records:
            return
        from pathlib import Path
        from playlist_files import export_text
        from file_output import component
        path = filedialog.asksaveasfilename(parent=self.app, title=tr("Exportar toda a playlist carregada"),
                    initialfile=component(self.playlist_title) + ".txt", defaultextension=".txt",
                    filetypes=[(tr("TXT (links)"), "*.txt"), (tr("M3U (links e títulos)"), "*.m3u"), ("M3U UTF-8", "*.m3u8")])
        if not path:
            return
        temporary = None
        try:
            import os
            import tempfile
            content = export_text(self.records.values(), m3u=Path(path).suffix.lower() in (".m3u", ".m3u8"))
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=Path(path).parent, prefix="onda-lista-", suffix=".tmp", delete=False) as output:
                temporary = Path(output.name)
                output.write(content)
            os.replace(temporary, path)
            self.status.set(f"{len(self.records)} itens exportados: {Path(path).name}. Inclui toda a lista carregada, mesmo com busca ativa; são links, não os arquivos de áudio.")
        except (OSError, ValueError) as exc:
            self.status.set(f"Não foi possível exportar: {exc}")
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def display(self, result):
        self.sync_result=None
        self.collection_url=result.get("_collection_url","")
        self.playlist_title = result.get("title") or "Playlist"
        self.playlist_folder_title = result.get("folder_title") or self.playlist_title
        self.cover_generation += 1
        self.collection_card.grid()
        self.collection_name.configure(text=self.playlist_title)
        self.collection_artist.configure(text=result.get("subtitle") or "")
        detail=" · ".join(str(value) for value in ("Álbum" if result.get("kind")=="album" else "Playlist", f"{len(result['tracks'])} músicas") if value)
        self.collection_detail.configure(text=tr(detail))
        self.collection_cover.configure(image="",text=tr("♫"))
        self.cover_image=None
        if result.get("cover_url"):
            generation, cover_generation, url=self.generation,self.cover_generation,result["cover_url"]
            def load_cover(generation=generation, cover_generation=cover_generation, url=url):
                try:
                    from catalog_ui import cover_png
                    image=cover_png(url)
                except Exception:image=None
                self.events.put((generation,"cover",(cover_generation,image)))
            threading.Thread(target=load_cover,daemon=True).start()
        for key in self.records:
            if self.table.exists(key):
                self.table.delete(key)
        self.records = {str(i): row for i, row in enumerate(result["tracks"])}
        self.search_index = {key: search_text((row.get("title") or "") + " " + " ".join(row.get("artists", [])))
                             for key, row in self.records.items()}
        self._render_generation += 1
        generation = self._render_generation
        if self._render_after is not None:
            self.after_cancel(self._render_after)
        self.set_busy(True)
        pending = iter(self.records.items())
        def render_batch():
            self._render_after = None
            if self.closed or generation != self._render_generation:
                return
            for _ in range(100):
                try:
                    key, row = next(pending)
                except StopIteration:
                    self.table.selection_set(self.table.get_children())
                    self.filter_text.set("")
                    self.filter_records()
                    self.status.set(f"{result['title']} · {len(self.records)} itens. {result['note']}") 
                    if result.get('_sync_folder'):
                        from playlist_sync_ui import start as start_comparison
                        self.after_idle(lambda:start_comparison(self,result['_sync_folder']))
                    if self.list_window is not None and self.list_window.winfo_exists():
                        self.list_window.refresh(self)
                    self.set_busy(False)
                    if result.get("_clipboard_download"):self.add(start=True)
                    return
                self.table.insert("", "end", iid=key, values=(row["title"], ", ".join(row.get("artists", [])),
                    duration_label(row["duration_ms"] / 1000 if row.get("duration_ms") else None), tr("A consultar")))
            self._render_after = self.after(1, render_batch)
        render_batch()

    def schedule_filter(self, *_):
        if self._filter_after is not None:
            self.after_cancel(self._filter_after)
        self._filter_after = self.after(150, self.filter_records)

    def filter_records(self, *_):
        if self._filter_after is not None:
            self.after_cancel(self._filter_after)
            self._filter_after = None
        if self._render_after is not None:
            return
        words = search_text(self.filter_text.get()).split()
        visible = [key for key in self.records if all(word in self.search_index[key] for word in words)]
        selected = set(self.table.selection())
        self.table.set_children("", *visible)
        self.table.selection_set([key for key in visible if key in selected])
        count = len(visible)
        self.filter_count.set(f"{count} de {len(self.records)}" if count or not words else "Nenhum resultado")

    def selected_keys(self):
        if self._filter_after is not None:
            self.filter_records()
        visible = set(self.table.get_children())
        return [key for key in self.table.selection() if key in visible]

    def check(self):
        selected = [(key, self.records[key]) for key in self.selected_keys()]
        if self.busy or not selected:
            return
        generation = self.generation
        credentials = self.app.spotify_client_id.get(), self.app.spotify_client_secret.get()
        automatic = self.app.auto_match.get()
        automatic_metadata = self.app.auto_metadata.get()
        flac = MODES[self.app.playlist_mode.get()] == "flac"
        self.set_busy(True)
        self.status.set("Conferindo versões das faixas selecionadas…")
        def worker():
            from catalog_match import CatalogChoiceRequired
            from matching import find_youtube, AmbiguousMatch
            class Quiet:
                def debug(self, _): pass
                def warning(self, _): pass
                def error(self, _): pass
            client = MetadataClient(*credentials)
            try:
                for key, row in selected:
                    if self.closed:
                        return
                    try:
                        if not is_streaming_link(row["source_url"]):
                            status = tr("Vídeo da própria playlist")
                        else:
                            if row.get('platform') == 'Spotify' and row.get('artists') and row.get('method') in ('Spotify Web API', 'Spotify Embed público'):
                                from spotify_search import cached_record
                                record = cached_record(row, row['source_url'])
                            else:
                                record = client.resolve(row["source_url"], **({"automatic":True} if automatic_metadata else {}))
                            if flac:
                                from lossless_source import search_matches, choose_match
                                def need_choice(_record, candidates):
                                    raise AmbiguousMatch(candidates)
                                match = choose_match(record, search_matches(record), need_choice, {"auto_match": automatic})
                                status = "Monochrome • " + match["title"]
                            else:
                                match = find_youtube(record, Quiet(), prefer_best=True) if automatic else find_youtube(record, Quiet())
                                status = match["title"]
                    except (CatalogChoiceRequired, AmbiguousMatch):
                        status = tr("Escolha necessária ao baixar")
                    except Exception as exc:
                        status = tr(str(exc))
                    self.events.put((generation, "match", (key, status)))
            finally:
                client.close()
                self.events.put((generation, "checked", None))
        threading.Thread(target=worker, daemon=True).start()

    def add(self, start=False):
        if self.busy:
            return
        if start and self.app.updating:
            self.status.set('Aguarde a atualização das ferramentas terminar.')
            return
        selected = [self.records[key] for key in self.selected_keys()]
        if not selected:
            self.status.set('Selecione pelo menos uma faixa ou vídeo da lista.')
            return
        added = self.app.add(lines=[row["source_url"] for row in selected], reuse_existing=start,
                             overrides={"playlist": False, "playlist_title": getattr(self, "playlist_folder_title", self.playlist_title), "confirm_version": self.confirm_version.get(),
                                        "mode": MODES[self.app.playlist_mode.get()], "height": HEIGHTS[self.app.playlist_height.get()],
                                        "fps": FPS_OPTIONS[self.app.playlist_fps.get()],
                                        "mp3_quality": self.app.playlist_mp3_quality.get(), "m4a_quality": self.app.playlist_m4a_quality.get()})
        from spotify_search import cached_record
        from queue_titles import record_name
        by_url = {row['source_url']: row for row in selected}
        cached = False
        for item in added or []:
            job = self.app.jobs.get(item)
            if job is None:
                continue
            row = by_url.get(job['url'], {})
            from queue_details import queue_info
            job['queue_info']=queue_info(row)
            name = record_name(row)
            if name:
                job['display_name'] = name
                self.app.tree.set(item, 'name', name)
                cached = True
            if row.get('platform') == 'Spotify' and row.get('artists') and row.get('method') in ('Spotify Web API', 'Spotify Embed público'):
                job['catalog_record'] = cached_record(row, row['source_url'])
                cached = True
        if cached:
            self.app.persist_queue()
        count = len(added or [])
        from file_output import component
        self.status.set(f"{count} itens adicionados. Destino: {component(getattr(self, 'playlist_folder_title', self.playlist_title))} dentro da pasta configurada.")
        if count and start:
            self.app.start(only_items=added)
            self.app.show_queue()

    def poll(self):
        if self.closed:
            return
        for _ in range(40):
            try:
                generation, kind, value = self.events.get_nowait()
            except queue.Empty:
                break
            if generation != self.generation:
                continue
            if kind == "cover":
                if value[0]==self.cover_generation and value[1]:
                    import base64
                    self.cover_image=tk.PhotoImage(data=base64.b64encode(value[1]))
                    self.collection_cover.configure(image=self.cover_image,text=tr(""),width=0)
            elif kind == "loaded":
                self.display(value)
            elif kind == "error":
                self.status.set(value)
                self.set_busy(False)
            elif kind == "local_comparison":
                from playlist_sync_ui import show as show_comparison
                show_comparison(self,value)
            elif kind == "match" and self.table.exists(value[0]):
                self.table.set(value[0], "match", value[1])
            elif kind == "checked":
                self.status.set("Consulta concluída. A seleção de versões segue as configurações de Downloads.")
                self.set_busy(False)
        self.poll_id = self.after(100, self.poll)

    def shutdown(self):
        if self.closed:
            return
        self.closed = True
        for callback in (self._filter_after, self._render_after):
            if callback is not None:
                self.after_cancel(callback)
        self._filter_after = self._render_after = None
        self.app.auto_match.trace_remove("write", self.auto_match_trace)
        if self.list_window is not None and self.list_window.winfo_exists():
            self.list_window.destroy()
        if self.spotify_window is not None and self.spotify_window.winfo_exists():
            self.spotify_window.close()
        self.generation += 1
        self.after_cancel(self.poll_id)
