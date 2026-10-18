"""Slowed + Reverb workspace: local audio, independent controls, preview/export."""
from i18n import tr
from i18n_tk import TranslatedCombobox, display_var
import json
import math
from pathlib import Path
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from audio_tools import PreviewPlayer, effects_filter, effect_name, process_options, executable, MIN_SPEED, MAX_SPEED
from engine import stop_process


PRESETS = {
    "Original": (100, 0),
    "Slowed leve": (90, 0),
    "Slowed intenso": (75, 0),
    "Sped Up leve": (115, 0),
    "Sped Up intenso": (130, 0),
    "Sped Up + Reverb": (120, 25),
    "Só Reverb": (100, 30),
    "Clássico": (85, 25),
    "Atmosférico": (75, 50),
}


class EffectsPane(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=(0, 12, 0, 0))
        self.app = app
        self.source = tk.StringVar()
        self.speed = tk.DoubleVar(value=85)
        self.reverb = tk.DoubleVar(value=25)
        self.keep_pitch = app.effects_keep_pitch
        self.preset = tk.StringVar(value="Clássico")
        self.start_time = tk.StringVar(value="0")
        self.mode = tk.StringVar(value="MP3")
        self.status = tk.StringVar(value="Abra uma música do computador ou use um arquivo do histórico.")
        self.player = PreviewPlayer()
        self.events = queue.Queue()
        self.process = None
        self.process_lock = threading.Lock()
        self.busy = False
        self.closed = False
        self.cancelled = threading.Event()
        self.debounce = None
        self.preview_active = False
        self.playback_mode = None
        self.duration = 0.0
        self.position = tk.DoubleVar(value=0)
        self.time_label = tk.StringVar(value="0:00 / —")
        self.dragging = False
        self.resume_mode = None
        self.probe_generation = 0
        self.probe_after = None
        self.render_temp = None
        self.output_folder = None
        self.columnconfigure(0, weight=1)
        ttk.Label(self, text=tr("Slowed · Sped Up · Reverb"), font=("Segoe UI", 23, "bold"), anchor="center").grid(row=0, column=0, sticky="ew")
        ttk.Label(self, text=tr("Desacelere ou acelere sua música. Adicione reverb se quiser."), style="Muted.TLabel", anchor="center").grid(row=1, column=0, sticky="ew", pady=(5, 12))
        file_row = ttk.Frame(self)
        file_row.grid(row=2, column=0, sticky="ew")
        ttk.Entry(file_row, textvariable=self.source).pack(side="left", fill="x", expand=True)
        ttk.Button(file_row, text=tr("Abrir áudio"), command=self.choose).pack(side="left", padx=(8, 0))
        card = ttk.Frame(self, style="Card.TFrame", padding=14)
        card.grid(row=3, column=0, sticky="ew", pady=10)
        card.columnconfigure(0, weight=1)
        self.speed_label = tk.StringVar()
        self.reverb_label = tk.StringVar()
        ttk.Label(card, textvariable=display_var(self.speed_label), style="Card.TLabel", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w")
        presets = ttk.Frame(card, style="Card.TFrame")
        presets.grid(row=0, column=1, sticky="e")
        ttk.Label(presets, text=tr("Preset"), style="CardMuted.TLabel").pack(side="left", padx=(8, 8))
        self.preset_box = TranslatedCombobox(presets, textvariable=self.preset, values=(*PRESETS, "Personalizado"), state="readonly", width=17)
        self.preset_box.pack(side="left")
        self.preset_box.bind("<<ComboboxSelected>>", self.apply_preset)
        self.speed_slider = ttk.Scale(card, from_=MIN_SPEED, to=MAX_SPEED, variable=self.speed, command=self.changed)
        self.speed_slider.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 4))
        speed_guide = ttk.Frame(card, style="Card.TFrame")
        speed_guide.grid(row=2, column=0, columnspan=2, sticky="ew")
        for column in range(3):
            speed_guide.columnconfigure(column, weight=1, uniform="speed")
        for column, text, anchor in ((0, "50% · Slowed", "w"), (1, "100% · original", "center"), (2, "150% · Sped Up", "e")):
            ttk.Label(speed_guide, text=tr(text), style="CardMuted.TLabel", anchor=anchor).grid(row=0, column=column, sticky="ew")
        ttk.Label(card, textvariable=display_var(self.reverb_label), style="Card.TLabel", font=("Segoe UI", 12, "bold")).grid(row=3, column=0, sticky="w", pady=(16, 0))
        self.reverb_slider = ttk.Scale(card, from_=0, to=100, variable=self.reverb, command=self.changed)
        self.reverb_slider.grid(row=4, column=0, columnspan=2, sticky="ew", pady=8)
        ttk.Label(card, text=tr("0% · sem reverb                                                   100% · mais ambiente"), style="CardMuted.TLabel").grid(row=5, column=0, sticky="w")
        self.keep_pitch_checkbox = ttk.Checkbutton(card, text=tr('Manter tom (pitch) ao alterar a velocidade'), variable=self.keep_pitch)
        self.keep_pitch_checkbox.grid(row=6, column=0, columnspan=2, sticky='w', pady=(10, 0))
        timeline = ttk.Frame(self)
        timeline.grid(row=4, column=0, sticky="ew", pady=(0, 12))
        timeline.columnconfigure(0, weight=1)
        ttk.Label(timeline, text=tr("Posição na música"), style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(timeline, textvariable=display_var(self.time_label), style="Muted.TLabel").grid(row=0, column=1, sticky="e")
        self.timeline = ttk.Scale(timeline, from_=0, to=1, variable=self.position, state="disabled")
        self.timeline.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        self.timeline.bind("<ButtonPress-1>", self.seek_begin)
        self.timeline.bind("<B1-Motion>", self.seek_move)
        self.timeline.bind("<ButtonRelease-1>", self.seek_end)
        for key, seconds in (("Left", -5), ("Right", 5)):
            self.timeline.bind("<" + key + ">", lambda event, step=seconds: self.seek_key(step))
        preview = ttk.Frame(self)
        preview.grid(row=5, column=0, sticky="ew")
        ttk.Button(preview, text=tr("Ouvir original"), command=lambda: self.preview(False)).pack(side="left", padx=4)
        ttk.Button(preview, text=tr("Ouvir com efeitos"), style="Accent.TButton", command=self.preview).pack(side="left", padx=4)
        ttk.Button(preview, text=tr("Parar"), command=self.stop_preview).pack(side="left", padx=4)
        ttk.Label(self, text=tr("Arraste a barra para escolher o trecho. A duração da prévia pode ser alterada em Configurações. Ajuste os efeitos enquanto ouve."), style="Muted.TLabel", wraplength=760).grid(row=6, column=0, sticky="w", pady=8)
        export = ttk.Frame(self)
        export.grid(row=7, column=0, sticky="ew", pady=8)
        ttk.Label(export, text=tr("Salvar como")).pack(side="left")
        TranslatedCombobox(export, textvariable=self.mode, values=("MP3", "M4A", "FLAC", "WAV"), state="readonly", width=9).pack(side="left", padx=10)
        self.export_button = ttk.Button(export, text=tr("Exportar música inteira"), command=self.export)
        self.export_button.pack(side="left")
        self.cancel_button = ttk.Button(export, text=tr("Cancelar exportação"), command=self.cancel, state="disabled")
        self.cancel_button.pack(side="right")
        self.bar = ttk.Progressbar(self, maximum=100)
        self.bar.grid(row=8, column=0, sticky="ew", pady=8)
        self.status_label = ttk.Label(self, textvariable=display_var(self.status), style="Muted.TLabel", wraplength=800)
        self.status_label.grid(row=9, column=0, sticky="w")
        self.lyric_rows=[]
        self.lyric_text=tk.StringVar()
        self.lyric_label=ttk.Label(self,textvariable=self.lyric_text,wraplength=760,anchor="center",font=('Segoe UI',12,'bold'))
        self.lyric_label.grid(row=10,column=0,sticky="ew",pady=8)
        ttk.Button(self,text=tr("Importar letra LRC"),command=self.choose_lyrics).grid(row=11,column=0,sticky="w")
        self.keep_pitch_trace = self.keep_pitch.trace_add("write", lambda *_: self.changed())
        self.source.trace_add("write", self.source_changed)
        self.changed()
        self.poll_id = self.after(100, self.poll)

    def choose_lyrics(self):
        path=filedialog.askopenfilename(parent=self.app,title=tr("Importar letra LRC"),filetypes=[('LRC','*.lrc')])
        if path:
            try:
                from synced_lyrics import read_lrc
                self.lyric_rows=read_lrc(path)
                if not self.lyric_rows:raise ValueError(tr("Nenhum tempo válido na letra LRC."))
                self.app.synced_lyrics.set(True)
            except (OSError,ValueError) as error:self.status.set(str(error))

    def choose(self):
        path = filedialog.askopenfilename(parent=self.app, title=tr("Áudio para Slowed, Sped Up e Reverb"), filetypes=[(tr("Áudio"), "*.mp3 *.m4a *.flac *.wav *.ogg *.opus *.webm *.aac"), (tr("Todos os arquivos"), "*.*")])
        if path:
            self.use_file(path)

    def use_file(self, path):
        self.stop_preview()
        self.lyric_rows=[];self.lyric_text.set("")
        sidecar=Path(path).with_suffix('.lrc')
        if self.app.synced_lyrics.get() and sidecar.is_file():
            try:
                from synced_lyrics import read_lrc
                self.lyric_rows=read_lrc(sidecar)
            except (OSError,ValueError):pass
        self.source.set(str(path))
        self.status.set("Áudio selecionado. Ouça um trecho antes de exportar.")

    @staticmethod
    def clock(seconds):
        seconds = max(0, int(seconds))
        hours, rest = divmod(seconds, 3600)
        minutes, seconds = divmod(rest, 60)
        return f"{hours}:{minutes:02}:{seconds:02}" if hours else f"{minutes}:{seconds:02}"

    def set_position(self, seconds):
        seconds = max(0, min(float(seconds), self.duration)) if self.duration else max(0, float(seconds))
        self.position.set(seconds)
        if hasattr(self,'lyric_rows'):
            from synced_lyrics import line_at
            self.lyric_text.set(line_at(self.lyric_rows,seconds) if self.app.synced_lyrics.get() else "")
        self.start_time.set(str(seconds))
        self.time_label.set(self.clock(seconds) + " / " + (self.clock(self.duration) if self.duration else "—"))

    def source_changed(self, *_):
        self.stop_preview()
        self.probe_generation += 1
        self.duration = 0
        self.set_position(0)
        self.timeline.configure(state="disabled", to=1)
        if self.probe_after:
            self.after_cancel(self.probe_after)
        self.probe_after = self.after(300, self.probe_duration)

    def probe_duration(self):
        self.probe_after = None
        generation, source, folder = self.probe_generation, self.source.get(), self.app.ffmpeg.get()
        def worker():
            try:
                if not Path(source).is_file():
                    return
                result = subprocess.run([executable("ffprobe", folder), "-v", "error", "-show_entries", "format=duration", "-of", "json", source],
                    capture_output=True, text=True, encoding="utf-8", timeout=20, **process_options())
                duration = float(json.loads(result.stdout)["format"]["duration"])
                if math.isfinite(duration) and duration > 0:
                    self.events.put({"type": "duration", "generation": generation, "duration": duration})
            except (OSError, ValueError, KeyError, subprocess.SubprocessError):
                self.events.put({"type": "duration_error", "generation": generation})
        threading.Thread(target=worker, daemon=True).start()

    def sync_position(self):
        if self.playback_mode is not None and not self.dragging:
            self.set_position(self.player.position_snapshot())

    def seek_begin(self, event):
        if not self.duration:
            return "break"
        self.timeline.focus_set()
        self.sync_position()
        self.resume_mode = self.playback_mode if self.player.active else None
        self.stop_preview()
        self.dragging = True
        return self.seek_move(event)

    def seek_move(self, event):
        if self.dragging:
            fraction = (event.x - 8) / max(1, self.timeline.winfo_width() - 16)
            self.set_position(self.duration * max(0, min(1, fraction)))
        return "break"

    def seek_end(self, event):
        if self.dragging:
            self.seek_move(event)
            self.dragging = False
            mode, self.resume_mode = self.resume_mode, None
            if mode is not None:
                self.preview(mode)
        return "break"

    def seek_key(self, step):
        if self.duration:
            self.sync_position()
            mode = self.playback_mode if self.player.active else None
            self.stop_preview()
            self.set_position(self.position.get() + step)
            if mode is not None:
                self.preview(mode)
        return "break"

    def changed(self, _=None):
        values = (round(self.speed.get()), round(self.reverb.get()))
        self.preset.set(next((name for name, pair in PRESETS.items() if pair == values), "Personalizado"))
        speed = round(self.speed.get())
        self.speed_label.set(f"Velocidade · {speed}% · " + ("Slowed" if speed < 100 else "Sped Up" if speed > 100 else "original"))
        self.reverb_label.set(f"Reverb · {self.reverb.get():.0f}%" + (" · desligado" if round(self.reverb.get()) == 0 else ""))
        if self.debounce:
            self.after_cancel(self.debounce)
            self.debounce = None
        if self.preview_active:
            self.debounce = self.after(650, self.preview)

    def apply_preset(self, _=None):
        values = PRESETS.get(self.preset.get())
        if values:
            self.speed.set(values[0])
            self.reverb.set(values[1])
            self.changed()

    def preview(self, processed=True):
        self.debounce = None
        try:
            source = Path(self.source.get()).expanduser().resolve()
            if not source.is_file():
                raise ValueError("Abra um arquivo de áudio primeiro.")
            self.sync_position()
            start = float(self.start_time.get())
            if not math.isfinite(start) or start < 0:
                raise ValueError("Escolha uma posição válida na música.")
            if self.duration and start >= self.duration:
                start = 0
            self.set_position(start)
            speed, reverb = (round(self.speed.get()), round(self.reverb.get())) if processed else (100, 0)
            keep_pitch = self.keep_pitch.get() if processed else False
            effects_filter(speed, reverb, keep_pitch)
            self.app.catalog_page.stop_preview()
            from preview_options import preview_seconds
            duration = preview_seconds(self.app.effects_preview_duration.get())
            self.player.play(str(source), self.app.ffmpeg.get(), speed, reverb, start, duration=duration, keep_pitch=keep_pitch)
            self.preview_active = processed
            self.playback_mode = processed
            self.status.set("Preparando prévia…")
        except (ValueError, OSError) as exc:
            self.status.set(str(exc))

    def stop_preview(self):
        self.sync_position()
        self.preview_active = False
        self.playback_mode = None
        if self.debounce:
            self.after_cancel(self.debounce)
            self.debounce = None
        self.player.stop()

    def export(self):
        if self.busy:
            return
        source = Path(self.source.get()).expanduser()
        if not source.is_file():
            self.status.set("Abra um arquivo de áudio primeiro.")
            return
        speed, reverb = round(self.speed.get()), round(self.reverb.get())
        effect = effect_name(speed, reverb)
        suffix = "." + self.mode.get().lower()
        output = filedialog.asksaveasfilename(parent=self.app, title=tr("Salvar versão com efeitos"), initialdir=str(source.parent),
                   initialfile=source.stem + (" - " + effect if effect else "") + suffix, defaultextension=suffix,
                   filetypes=[(self.mode.get(), "*" + suffix)], confirmoverwrite=False)
        if not output:
            return
        if source.resolve() == Path(output).resolve():
            messagebox.showerror(tr("Exportar"), tr("Escolha outro nome para preservar o original."), parent=self.app)
            return
        replace = Path(output).exists()
        if replace and not messagebox.askyesno(tr("Exportar"), tr("O arquivo já existe. Substituir esta cópia?"), parent=self.app):
            return
        self.stop_preview()
        self.busy = True
        self.render_temp = None
        self.output_folder = Path(output).resolve().parent
        self.cancelled.clear()
        self.export_button.configure(state="disabled")
        self.speed_slider.configure(state="disabled")
        self.reverb_slider.configure(state="disabled")
        self.preset_box.configure(state="disabled")
        self.keep_pitch_checkbox.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.status.set("Exportando a música inteira…")
        self.bar.configure(value=0)
        quality = self.app.mp3_quality.get() if suffix == ".mp3" else self.app.m4a_quality.get()
        config = {"source": str(source.resolve()), "output": output, "speed": speed, "reverb": reverb, "keep_pitch": self.keep_pitch.get(),
                  "ffmpeg": self.app.ffmpeg.get(), "replace": replace, "bitrate": int(quality.split()[0])}
        from performance import snapshot
        config.update(snapshot(self.app))
        threading.Thread(target=self.render, args=(config,), daemon=True).start()

    def render(self, config):
        process = None
        success = False
        code = 1
        temporary = None
        try:
            python = Path(sys.executable)
            if python.name.lower() == "pythonw.exe":
                python = python.with_name("python.exe")
            from performance import priority_flags
            child_options=process_options()
            if os.name=="nt":child_options["creationflags"]=child_options.get("creationflags",0)|priority_flags(config)
            with self.process_lock:
                process = subprocess.Popen([str(python), "-u", str(Path(__file__).with_name("effects_worker.py"))],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", **child_options)
                self.process = process
            if self.cancelled.is_set():
                stop_process(process)
            else:
                process.stdin.write(json.dumps(config) + "\n")
                process.stdin.flush()
                for line in process.stdout:
                    try:
                        event = json.loads(line)
                    except ValueError:
                        continue
                    if event.get("type") == "done":
                        success = True
                    if event.get("type") == "temporary":
                        path = Path(event["path"]).resolve()
                        if path.parent == Path(config["output"]).resolve().parent and path.name.startswith(".onda-render-"):
                            temporary = path
                    self.events.put(event)
            code = process.wait()
        except Exception as exc:
            self.events.put({"type": "error", "message": str(exc)})
        finally:
            if process:
                if process.poll() is None:
                    stop_process(process)
                    process.wait()
                for stream in (process.stdin, process.stdout):
                    if stream:
                        stream.close()
            with self.process_lock:
                self.process = None
            if self.cancelled.is_set() and temporary:
                import time
                for attempt in range(10):
                    try:
                        temporary.unlink(missing_ok=True)
                        break
                    except OSError:
                        time.sleep(.1)
            self.events.put({"type": "exit", "success": success and code == 0, "cancelled": self.cancelled.is_set()})

    def poll(self):
        if self.closed:
            return
        self.sync_position()
        for message in self.player.messages():
            self.status.set(message)
            if "encerrada" in message or "Não foi" in message:
                self.preview_active = False
                self.playback_mode = None
        for _ in range(40):
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break
            if event["type"] == "duration":
                if event["generation"] == self.probe_generation:
                    self.duration = event["duration"]
                    self.timeline.configure(to=self.duration, state="normal")
                    self.set_position(self.position.get())
            elif event["type"] == "duration_error":
                if event["generation"] == self.probe_generation:
                    self.status.set("Não foi possível ler a duração. Confira o arquivo e a pasta do FFmpeg.")
            elif event["type"] == "progress":
                self.bar.configure(value=event["percent"])
            elif event["type"] == "temporary":
                path = Path(event["path"]).resolve()
                if path.parent == self.output_folder and path.name.startswith(".onda-render-"):
                    self.render_temp = path
            elif event["type"] == "error":
                self.status.set(event["message"])
            elif event["type"] == "done":
                self.status.set("Salvo: " + event["path"])
                self.bar.configure(value=100)
                self.app.record_history(event["path"], "Efeitos", self.source.get())
            elif event["type"] == "exit":
                if self.render_temp:
                    try:
                        self.render_temp.unlink(missing_ok=True)
                    except OSError:
                        pass
                    self.render_temp = None
                self.busy = False
                self.export_button.configure(state="normal")
                self.speed_slider.configure(state="normal")
                self.reverb_slider.configure(state="normal")
                self.preset_box.configure(state="readonly")
                self.keep_pitch_checkbox.configure(state="normal")
                self.cancel_button.configure(state="disabled")
                if event.get("cancelled"):
                    self.status.set("Exportação cancelada. O original foi preservado.")
                if self.app.closing and not self.app.active:
                    self.app.destroy()
                    return
        self.poll_id = self.after(100, self.poll)

    def cancel(self):
        self.cancelled.set()
        def stop():
            with self.process_lock:
                if self.process:
                    stop_process(self.process)
        threading.Thread(target=stop, daemon=True).start()

    def shutdown(self):
        self.closed = True
        self.keep_pitch.trace_remove("write", self.keep_pitch_trace)
        self.probe_generation += 1
        if self.probe_after:
            self.after_cancel(self.probe_after)
            self.probe_after = None
        self.stop_preview()
        self.player.close()
        self.cancel()
        if self.poll_id:
            self.after_cancel(self.poll_id)
            self.poll_id = None
