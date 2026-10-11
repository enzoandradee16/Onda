"""Onda — desktop media downloader. Run with Python 3.10+."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import webbrowser

from engine import HEIGHTS, MODES, FPS_OPTIONS, binaries, stop_process, validate_url
from ui import UiMixin
from credentials import CredentialStore, CredentialError
from preferences import PreferenceStore
from file_output import DUPLICATES

BASE = Path(__file__).resolve().parent
BG, PANEL, TEXT, MUTED, ACCENT = "#10151e", "#1a2230", "#eef3fa", "#a6b4c8", "#65dfbd"


def readable_bytes(value):
    if not value:
        return "—"
    number = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if number < 1024 or unit == "TB":
            return f"{number:.1f} {unit}"
        number /= 1024


class App(UiMixin, tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Onda • Vídeo & áudio")
        self.geometry("980x780")
        self.minsize(840, 720)
        self.configure(bg=BG)
        self.events = queue.Queue()
        self.jobs = {}
        self.active = None
        self.running = False
        self.closing = False
        self.process = None
        self.process_lock = threading.Lock()
        self.cancelled = threading.Event()
        self.mode = tk.StringVar(value=next(iter(MODES)))
        self.height = tk.StringVar(value="1080p")
        self.fps = tk.StringVar(value="Original")
        self.catalog_provider = tk.StringVar(value="Deezer")
        self.folder = tk.StringVar(value=os.environ.get("ONDA_DOWNLOADS", str(BASE / "downloads")))
        self.ffmpeg = tk.StringVar()
        self.playlist = tk.BooleanVar(value=False)
        self.mp3_quality = tk.StringVar(value="320 kbps")
        self.m4a_quality = tk.StringVar(value="256 kbps")
        self.review_metadata = tk.BooleanVar(value=False)
        self.organization = tk.StringVar(value="Catálogo")
        self.duplicates = tk.StringVar(value="Perguntar")
        self.update_status = tk.StringVar(value="Atualize quando o YouTube mudar ou apresentar falhas.")
        self.updating = False
        self.choice_window = None
        self.preference_store = PreferenceStore()
        self._preference_after = None
        preference_warning = ""
        preferences = None
        try:
            preferences = self.preference_store.load()
        except (ValueError, OSError) as exc:
            preference_warning = str(exc)
        self.remember_settings = tk.BooleanVar(value=preferences is not None)
        self.preference_status = tk.StringVar(value="Salvamento automático ativado." if preferences is not None else "Desmarcado: opções só para esta sessão.")
        self.preference_fields = {name: getattr(self, name) for name in ("mode", "height", "fps", "catalog_provider", "folder", "ffmpeg", "playlist", "mp3_quality", "m4a_quality", "review_metadata", "organization", "duplicates")}
        for name, value in (preferences or {}).items():
            self.preference_fields[name].set(value)
        self.credential_store = CredentialStore()
        credential_warning = ""
        saved = None
        try:
            saved = self.credential_store.load()
        except CredentialError as exc:
            credential_warning = str(exc)
        self.credential_status = tk.StringVar(value="Credenciais salvas neste computador." if saved else "Ainda não salvas neste computador.")
        env_id, env_secret = os.environ.get("SPOTIFY_CLIENT_ID", ""), os.environ.get("SPOTIFY_CLIENT_SECRET", "")
        if env_id or env_secret:
            initial_id, initial_secret = env_id, env_secret
            self.credential_status.set("Usando credenciais das variáveis de ambiente.")
        else:
            initial_id, initial_secret = saved or ("", "")
        self.spotify_client_id = tk.StringVar(value=initial_id)
        self.spotify_client_secret = tk.StringVar(value=initial_secret)
        self._saved_credentials = saved
        self.spotify_client_id.trace_add("write", self.spotify_credentials_edited)
        self.spotify_client_secret.trace_add("write", self.spotify_credentials_edited)
        self.status = tk.StringVar(value="Pronto para começar")
        self.detail = tk.StringVar(value="Cole um link e adicione à fila.")
        from library import LibraryStore
        self.library = LibraryStore(self.preference_store.path.parent / "library.sqlite3")
        self._style()
        self._layout()
        self.restore_queue()
        for variable in self.preference_fields.values():
            variable.trace_add("write", self.schedule_preferences)
        if preference_warning:
            self.write_log(preference_warning)
            self.preference_status.set("Não foi possível restaurar. Marque para salvar novamente.")
        if credential_warning:
            self.write_log(credential_warning)
            self.credential_status.set("Falha ao carregar. Informe e salve novamente.")
        self.protocol("WM_DELETE_WINDOW", self.close)
        self._poll_after = self.after(100, self.poll_events)

    def mode_changed(self, _=None):
        self.update_quality_selector()

    def schedule_preferences(self, *_):
        if self.remember_settings.get():
            if self._preference_after is not None:
                self.after_cancel(self._preference_after)
            self._preference_after = self.after(400, self.persist_preferences)

    def persist_preferences(self):
        if self._preference_after is not None:
            self.after_cancel(self._preference_after)
            self._preference_after = None
        if not self.remember_settings.get():
            return
        try:
            self.preference_store.save({name: variable.get() for name, variable in self.preference_fields.items()})
            self.preference_status.set("Configurações salvas automaticamente.")
        except OSError:
            self.preference_status.set("Falha ao salvar. Confira as permissões da pasta do Onda.")
            self.write_log("Não foi possível salvar as configurações deste computador.")

    def toggle_remember_settings(self):
        if self._preference_after is not None:
            self.after_cancel(self._preference_after)
            self._preference_after = None
        if self.remember_settings.get():
            self.persist_preferences()
        else:
            try:
                self.preference_store.forget()
                self.preference_status.set("Preferências removidas. Na próxima abertura serão usados os padrões.")
            except OSError:
                self.remember_settings.set(True)
                self.preference_status.set("Não foi possível remover as configurações salvas.")

    def choose_folder(self):
        folder = filedialog.askdirectory(title="Pasta de destino")
        if folder:
            self.folder.set(folder)

    def choose_ffmpeg(self):
        folder = filedialog.askdirectory(title="Pasta que contém ffmpeg e ffprobe")
        if folder:
            self.ffmpeg.set(folder)

    def add(self, lines=None, overrides=None):
        from_input = lines is None
        lines = lines if lines is not None else [line.strip() for line in self.urls.get("1.0", "end").splitlines() if line.strip()]
        overrides = overrides or {}
        added = []
        if not lines:
            return
        if not self.folder.get().strip():
            messagebox.showwarning("Destino", "Escolha uma pasta de destino.")
            return
        invalid = []
        try:
            from metadata import is_streaming_link
        except ImportError:
            messagebox.showerror("Dependência ausente", "Execute instalar.bat para atualizar as dependências.")
            return
        existing = {(job["url"], job["mode"], job["folder"], job["height"], job["playlist"], job.get("audio_quality"), job.get("fps"), job.get("selected_catalog_url"))
                    for job in self.jobs.values() if job["state"] in ("Na fila", "Em andamento")}
        for line in lines:
            streaming = is_streaming_link(line)
            try:
                url = line if streaming else validate_url(line)
            except ValueError as exc:
                invalid.append(line)
                self.write_log(str(exc))
                continue
            job = {"url": url, "mode": MODES[self.mode.get()], "height": HEIGHTS[self.height.get()],
                   "folder": str(Path(self.folder.get()).expanduser().resolve()),
                   "playlist": self.playlist.get(), "state": "Na fila", "review_metadata": self.review_metadata.get(),
                   "organization": self.organization.get(), "duplicate_policy": DUPLICATES[self.duplicates.get()]}
            job.update(overrides)
            if streaming:
                job["streaming"] = True
                job["playlist"] = False
                if job["mode"] in ("video", "original"):
                    job["mode"] = "mp3" if job["mode"] == "video" else "m4a"
                    self.write_log("Link de streaming: formato automático " + job["mode"].upper() + " para áudio com tags e capa.")
            job["audio_quality"] = overrides.get("audio_quality") or (self.mp3_quality.get() if job["mode"] == "mp3" else (self.m4a_quality.get() if job["mode"] == "m4a" else None))
            job["fps"] = overrides.get("fps", FPS_OPTIONS[self.fps.get()]) if job["mode"] == "video" else None
            key = (url, job["mode"], job["folder"], job["height"], job["playlist"], job["audio_quality"], job["fps"], job.get("selected_catalog_url"))
            if key in existing:
                continue
            existing.add(key)
            format_name = job["mode"].upper() + (" " + job["audio_quality"].split()[0] if job["audio_quality"] else "")
            item = self.tree.insert("", "end", values=(url, format_name, "A consultar", job["state"]), tags=(job["state"],))
            self.jobs[item] = job
            added.append(item)
        if from_input:
            self.urls.delete("1.0", "end")
            self.urls.insert("1.0", "\n".join(invalid))
        self.refresh_queue()
        self.persist_queue()
        self.refresh_placeholder()
        if invalid:
            messagebox.showwarning("Links não adicionados", "Alguns links não são aceitos. Use Ver detalhes para consultar o motivo.")
        return added

    def queue_catalog(self, record, mode, quality=None, start=False):
        overrides = {"mode": mode, "audio_quality": quality}
        if record.get("requested_source_url"):
            overrides["selected_catalog_url"] = record["source_url"]
        added = self.add(lines=[record.get("requested_source_url") or record["source_url"]], overrides=overrides)
        if not added:
            return False
        from size_estimate import estimate_size
        for item in added:
            self.tree.set(item, "name", " — ".join([", ".join(record.get("artists", [])), record.get("title") or "Música"]))
            size, _ = estimate_size({"duration": (record.get("duration_ms") or 0) / 1000}, self.jobs[item])
            if size is not None:
                self.tree.set(item, "size", "≈ " + readable_bytes(size))
        self.pages.select(self.download_page)
        if start and not self.active:
            self.start()
        return True

    def open_metadata(self, links=()):
        try:
            from metadata_ui import MetadataWindow
        except ImportError:
            messagebox.showerror("Dependência ausente", "Execute instalar.bat para instalar as dependências de metadados.")
            return
        return MetadataWindow(self, links)

    def save_spotify_credentials(self):
        try:
            pair = (self.spotify_client_id.get().strip(), self.spotify_client_secret.get().strip())
            self.credential_store.save(*pair)
        except CredentialError as exc:
            messagebox.showerror("Credenciais Spotify", str(exc), parent=self)
            return
        self._saved_credentials = pair
        self.credential_status.set("Salvas com proteção do Windows. Serão carregadas ao abrir o Onda.")

    def spotify_credentials_edited(self, *_):
        pair = (self.spotify_client_id.get().strip(), self.spotify_client_secret.get().strip())
        if pair != self._saved_credentials:
            self.credential_status.set("Alterações apenas nesta sessão. Clique em Salvar para lembrar depois.")
        else:
            self.credential_status.set("Credenciais salvas neste computador.")

    def forget_spotify_credentials(self):
        try:
            self.credential_store.forget()
        except CredentialError as exc:
            messagebox.showerror("Credenciais Spotify", str(exc), parent=self)
            return
        self._saved_credentials = None
        self.spotify_client_id.set("")
        self.spotify_client_secret.set("")
        self.credential_status.set("Credenciais removidas deste computador e dos campos da sessão.")

    def set_state(self, item, state):
        self.jobs[item]["state"] = state
        self.tree.set(item, "status", state)
        self.tree.item(item, tags=(state,))
        self.refresh_queue()
        self.persist_queue()

    def start(self):
        if self.active:
            return
        if self.updating:
            self.status.set("Aguarde a atualização do yt-dlp terminar.")
            return
        if not importlib.util.find_spec("yt_dlp"):
            messagebox.showerror("Dependência ausente", "Execute instalar.bat para instalar yt-dlp.")
            return
        if not binaries(self.ffmpeg.get().strip()):
            messagebox.showerror("FFmpeg necessário", "Selecione a pasta de FFmpeg e ffprobe em Configurações. Consulte Ajuda se necessário.")
            return
        self.running = True
        self.next_job()

    def next_job(self):
        pending = next((item for item in self.tree.get_children() if self.jobs[item]["state"] == "Na fila"), None)
        if not self.running or not pending:
            self.running = False
            self.start_button.configure(state="normal")
            self.cancel_button.configure(state="disabled")
            if not pending:
                self.status.set("Fila finalizada")
            return
        self.active = pending
        self.jobs[pending]["saved_sizes"] = {}
        self.cancelled.clear()
        self.set_state(pending, "Em andamento")
        self.tree.selection_set(pending)
        self.tree.see(pending)
        self.start_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.status.set("Obtendo informações…")
        self.detail.set("Aguardando o servidor. O cancelamento continua disponível.")
        self.set_progress(None)
        config = {**self.jobs[pending], "ffmpeg": self.ffmpeg.get().strip(),
                  "spotify_client_id": self.spotify_client_id.get(),
                  "spotify_client_secret": self.spotify_client_secret.get()}
        threading.Thread(target=self.supervise, args=(pending, config), daemon=True).start()

    def supervise(self, item, config):
        success = False
        process = None
        try:
            executable = Path(sys.executable)
            if executable.name.lower() == "pythonw.exe":
                executable = executable.with_name("python.exe")
            args = dict(stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, encoding="utf-8", errors="replace", bufsize=1,
                        env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            if os.name == "nt":
                args["creationflags"] = subprocess.CREATE_NO_WINDOW
            else:
                args["start_new_session"] = True
            with self.process_lock:
                process = subprocess.Popen([str(executable), "-u", str(BASE / "engine.py")], **args)
                self.process = process
            if self.cancelled.is_set():
                stop_process(process)
            else:
                process.stdin.write(json.dumps(config) + "\n")
                process.stdin.flush()
                for line in process.stdout:
                    try:
                        event = json.loads(line)
                        if not isinstance(event, dict) or "type" not in event:
                            raise ValueError()
                    except ValueError:
                        event = {"type": "log", "message": line.strip()}
                    if event["type"] == "done":
                        success = True
                    self.events.put((item, event))
            code = process.wait()
            success = success and code == 0
        except Exception as exc:
            self.events.put((item, {"type": "error", "message": str(exc)}))
        finally:
            if process:
                if process.poll() is None:
                    stop_process(process)
                    process.wait()
                if process.stdout:
                    process.stdout.close()
                if process.stdin and not process.stdin.closed:
                    process.stdin.close()
            with self.process_lock:
                self.process = None
            self.events.put((item, {"type": "exited", "success": success, "cancelled": self.cancelled.is_set()}))

    def set_progress(self, value):
        if value is None:
            self.progress_text.set("Em andamento")
            if self.bar["mode"] != "indeterminate":
                self.bar.configure(mode="indeterminate")
                self.bar.start(15)
        else:
            self.progress_text.set(f"{value:.0f}%")
            self.bar.stop()
            self.bar.configure(mode="determinate", value=value)

    def poll_events(self):
        for _ in range(150):
            try:
                item, event = self.events.get_nowait()
            except queue.Empty:
                break
            kind = event["type"]
            if kind.startswith("update_"):
                if kind == "update_log":
                    self.write_log(event["message"])
                else:
                    self.updating = False
                    self.update_button.configure(state="normal")
                    self.update_status.set("yt-dlp atualizado. Os próximos downloads usarão esta versão." if event.get("success") else "Falha na atualização. Confira Ver detalhes.")
                continue
            if item != self.active:
                continue
            if kind in ("error", "log"):
                self.write_log(event.get("message", ""))
            elif kind == "stage":
                self.set_progress(None)
                self.status.set(event["message"])
                self.detail.set("Processamento automático do link de streaming…")
            elif kind in ("review_metadata", "choose_duplicate"):
                if self.cancelled.is_set():
                    continue
                from review_ui import MetadataReview, DuplicateDialog
                self.dismiss_version_picker()
                if kind == "review_metadata":
                    self.status.set("Revise os metadados e a capa")
                    self.choice_window = MetadataReview(self, event, lambda changes, job=item: self.send_reply(job, {"changes": changes}), self.cancel)
                else:
                    self.status.set("Escolha como tratar o arquivo existente")
                    self.choice_window = DuplicateDialog(self, event, lambda choice, job=item: self.send_reply(job, {"choice": choice}), self.cancel)
                self.detail.set("A fila aguarda sua confirmação.")
            elif kind in ("choose_version", "choose_catalog"):
                if self.cancelled.is_set():
                    continue
                self.status.set("Escolha a versão que deseja baixar")
                self.detail.set("A fila aguarda sua escolha na janela de versões.")
                if kind == "choose_catalog":
                    from catalog_picker import CatalogPicker as Picker
                    self.status.set("Confirme qual música corresponde ao link Spotify")
                    self.detail.set("A fila aguarda sua escolha dos metadados do catálogo.")
                else:
                    from version_picker import VersionPicker as Picker
                self.choice_window = Picker(self, event, lambda selected, job=item: self.send_version(job, selected), self.cancel)
            elif kind == "file":
                self.write_log("Salvo: " + event["path"])
                self.jobs[item]["last_file"] = event["path"]
                if not event.get("skipped"):
                    self.record_history(event["path"], self.jobs[item]["mode"].upper(), self.jobs[item]["url"])
                if isinstance(event.get("size"), int):
                    self.jobs[item]["saved_sizes"][event["path"]] = event["size"]
                    self.tree.set(item, "size", readable_bytes(sum(self.jobs[item]["saved_sizes"].values())))
            elif kind == "estimate":
                label = "≈ " + readable_bytes(event["size"]) if event.get("size") is not None else "Indisponível"
                if event.get("playlist") and event.get("size") is not None:
                    label += " / item"
                self.tree.set(item, "size", label)
                self.write_log("Tamanho estimado: " + label + ". " + event.get("reason", ""))
                if event.get("title"):
                    self.tree.set(item, "name", event["title"])
            elif kind == "progress":
                title = event.get("title") or self.jobs[item]["url"]
                self.tree.set(item, "name", title)
                self.status.set(title[:100])
                total, downloaded = event.get("total"), event.get("downloaded", 0)
                if event["status"] == "finished":
                    self.set_progress(None)
                    self.detail.set("Transferência concluída; preparando o arquivo…")
                else:
                    percent = min(100, downloaded / total * 100) if total else None
                    self.set_progress(percent)
                    eta = event.get("eta")
                    suffix = f"  •  item {event['index']}" if event.get("index") else ""
                    prefix = f"{percent:.1f}%  •  " if percent is not None else ""
                    self.detail.set(f"{prefix}{readable_bytes(downloaded)} / {readable_bytes(total)}  •  "
                                    f"{readable_bytes(event.get('speed'))}/s  •  "
                                    f"restante: {int(eta) if eta is not None else '—'} s{suffix}")
            elif kind == "processing":
                self.set_progress(None)
                self.detail.set("Processando áudio/vídeo… O arquivo será marcado como concluído ao terminar.")
            elif kind == "exited":
                self.dismiss_version_picker()
                state = "Cancelado" if event["cancelled"] else ("Concluído" if event["success"] else "Falhou")
                self.set_state(item, state)
                self.set_progress(100 if state == "Concluído" else 0)
                self.status.set(state)
                self.detail.set("Arquivos disponíveis na pasta de destino." if state == "Concluído" else
                                "Use Ver detalhes para conferir o motivo, ou tente novamente.")
                self.active = None
                self.refresh_queue()
                if self.closing and not self.effects_page.busy:
                    self.destroy()
                    return
                self.next_job()
        self._poll_after = self.after(100, self.poll_events)

    def write_log(self, text):
        if not text:
            return
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        if int(self.log.index("end-1c").split(".")[0]) > 350:
            self.log.delete("1.0", "100.0")
        self.log.see("end")
        self.log.configure(state="disabled")

    def cancel(self):
        self.dismiss_version_picker()
        self.running = False
        self.cancelled.set()
        self.cancel_button.configure(state="disabled")
        self.status.set("Cancelando…")
        def stop():
            with self.process_lock:
                if self.process:
                    stop_process(self.process)
        threading.Thread(target=stop, daemon=True).start()

    def dismiss_version_picker(self):
        if self.choice_window is not None:
            if self.choice_window.winfo_exists():
                self.choice_window.destroy()
            self.choice_window = None

    def send_version(self, item, selected_id):
        self.send_reply(item, {"selected_id": selected_id})

    def send_reply(self, item, reply):
        if item != self.active or self.cancelled.is_set():
            self.dismiss_version_picker()
            return
        try:
            with self.process_lock:
                if self.process is None or self.process.poll() is not None:
                    raise OSError()
                self.process.stdin.write(json.dumps(reply) + "\n")
                self.process.stdin.flush()
        except (OSError, ValueError):
            self.write_log("Não foi possível enviar a escolha. Tente o item novamente.")
            self.cancel()
            return
        self.dismiss_version_picker()
        self.status.set("Escolha recebida. Continuando…")

    def retry(self):
        for item in self.tree.selection():
            if self.jobs[item]["state"] in ("Falhou", "Cancelado"):
                self.set_state(item, "Na fila")

    def remove(self):
        for item in self.tree.selection():
            if item != self.active:
                del self.jobs[item]
                self.tree.delete(item)
        self.refresh_queue()
        self.persist_queue()

    def open_folder(self):
        selected = self.tree.selection()
        folder = self.jobs[selected[0]]["folder"] if selected else self.folder.get()
        path = Path(folder).expanduser().resolve()
        try:
            path.mkdir(parents=True, exist_ok=True)
            if os.name == "nt":
                os.startfile(str(path))
            else:
                subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(path)])
        except OSError as exc:
            messagebox.showerror("Pasta", str(exc))

    def help(self):
        window = tk.Toplevel(self)
        window.title("Sobre o Onda")
        window.configure(bg=BG)
        window.geometry("670x490")
        text = ("Onda • downloads de vídeo e áudio\n\n"
                "1. Instale as dependências com instalar.bat.\n"
                "2. Configure FFmpeg (ffprobe e ffplay) e Node ou Deno para o YouTube.\n"
                "3. Cole links, escolha o formato e adicione à fila.\n"
                "4. Clique em Baixar fila. A barra acompanha cada transferência.\n\n"
                "Spotify / Deezer / Apple: a fila busca áudio correspondente no YouTube e aplica tags/capa. "
                "Sem API Spotify, os metadados vêm de uma faixa equivalente no Deezer ou Apple. "
                "Este programa não exporta músicas protegidas por DRM.\n\n"
                "FLAC usa compressão sem perdas, mas converter MP3/AAC/Opus para FLAC "
                "não restaura o áudio original. Original evita recodificação.\n\n"
                "Configurações de formato, pasta e playlist são capturadas ao adicionar. "
                "Cancelar para a fila; tentar novamente pode retomar arquivos .part. "
                "A fila pendente é salva e restaurada pausada ao abrir. Use conteúdo seu ou autorizado.")
        ttk.Label(window, text=text, wraplength=620, justify="left", padding=20).pack(fill="both", expand=True)
        ttk.Button(window, text="Guia completo (README)", command=lambda: self.open_readme()).pack(pady=8)
        buttons = ttk.Frame(window)
        buttons.pack(pady=(0, 15))
        for label, url in (("FFmpeg", "https://ffmpeg.org/download.html"),
                           ("Deno", "https://docs.deno.com/runtime/getting_started/installation/"),
                           ("Spotify", "https://support.spotify.com/br-pt/article/listen-offline/"),
                           ("Apple Lossless", "https://support.apple.com/118295")):
            ttk.Button(buttons, text=label, command=lambda address=url: webbrowser.open(address)).pack(side="left", padx=4)

    def open_readme(self):
        if os.name == "nt":
            os.startfile(str(BASE / "README.md"))
        else:
            webbrowser.open((BASE / "README.md").as_uri())

    def destroy(self):
        if hasattr(self, "catalog_page"):
            self.catalog_page.shutdown()
        for name in ("effects_page", "playlist_page"):
            if hasattr(self, name):
                getattr(self, name).shutdown()
        for name in ("_poll_after", "_preference_after"):
            callback = getattr(self, name, None)
            if callback is not None:
                try:
                    self.after_cancel(callback)
                except tk.TclError:
                    pass
                setattr(self, name, None)
        super().destroy()

    def close(self):
        if self.updating:
            messagebox.showinfo("Atualização em andamento", "Aguarde a atualização terminar antes de fechar o Onda.", parent=self)
            return
        self.persist_preferences()
        self.persist_queue()
        if self.active or self.effects_page.busy:
            self.closing = True
            if self.active:
                self.cancel()
            if self.effects_page.busy:
                self.effects_page.cancel()
        else:
            self.destroy()

    def persist_queue(self):
        if not hasattr(self, "library"):
            return
        try:
            jobs = []
            for job in self.jobs.values():
                saved = dict(job)
                if self.closing and job is self.jobs.get(self.active) and saved.get("state") == "Cancelado":
                    saved["state"] = "Na fila"
                jobs.append(saved)
            self.library.save_queue(jobs)
        except Exception as exc:
            self.write_log("Não foi possível salvar a fila: " + str(exc))

    def restore_queue(self):
        try:
            jobs = self.library.load_queue()
            for job in jobs:
                if job.get("mode") not in MODES.values():
                    continue
                self.add(lines=[job["url"]], overrides=job)
            if jobs:
                self.status.set("Fila restaurada · clique em Baixar fila para continuar")
        except Exception as exc:
            self.write_log("Não foi possível restaurar a fila: " + str(exc))

    def record_history(self, path, mode, source=""):
        try:
            self.library.add_history(path, mode, source)
            self.history_page.refresh()
        except Exception as exc:
            self.write_log("Não foi possível salvar no histórico: " + str(exc))

    def tab_changed(self, _=None):
        selected = self.pages.select()
        if selected != str(self.catalog_page):
            self.catalog_page.stop_preview()
        if selected != str(self.effects_page):
            self.effects_page.stop_preview()
        if selected == str(self.history_page):
            self.history_page.refresh()

    def update_downloader(self):
        if self.updating:
            return
        if self.active or self.effects_page.busy or self.playlist_page.busy:
            self.update_status.set("Termine os downloads, consultas de playlist e exportações antes de atualizar.")
            return
        self.updating = True
        self.update_button.configure(state="disabled")
        self.update_status.set("Atualizando yt-dlp e componente JavaScript…")
        self.catalog_page.stop_preview()
        self.effects_page.stop_preview()
        def worker():
            from audio_tools import process_options
            python = Path(sys.executable)
            if python.name.lower() == "pythonw.exe":
                python = python.with_name("python.exe")
            try:
                with subprocess.Popen([str(python), "-m", "pip", "--disable-pip-version-check", "install", "--upgrade", "yt-dlp[default]"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", **process_options()) as process:
                    for line in process.stdout:
                        self.events.put((None, {"type": "update_log", "message": line.strip()}))
                    success = process.wait() == 0
            except Exception as exc:
                success = False
                self.events.put((None, {"type": "update_log", "message": str(exc)}))
            self.events.put((None, {"type": "update_done", "success": success}))
        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    App().mainloop()
