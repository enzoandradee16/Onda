"""Shared playback and deterministic independent slow/reverb filters."""
import math
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import threading

MIN_SPEED, MAX_SPEED = 50, 150

def executable(name, folder=""):
    candidate = Path(folder) / (name + ".exe" if os.name == "nt" else name)
    value = str(candidate) if folder and candidate.is_file() else shutil.which(name)
    if not value:
        raise ValueError(f"{name} não encontrado. Configure a pasta do FFmpeg.")
    return value


def process_options():
    return {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session": True}


def effects_filter(speed=100, reverb=0):
    speed, reverb = float(speed), float(reverb)
    if not math.isfinite(speed) or not MIN_SPEED <= speed <= MAX_SPEED or not math.isfinite(reverb) or not 0 <= reverb <= 100:
        raise ValueError("Velocidade deve ficar entre 50 e 150%; reverb entre 0 e 100%.")
    filters = []
    if speed != 100:
        filters += ["aresample=48000", f"asetrate={round(48000 * speed / 100)}", "aresample=48000"]
    if reverb:
        wet = reverb / 100
        delays = [round((23 + i * 29 + (i % 3) * 7) * (0.6 + wet)) for i in range(32)]
        decays = [wet * .14 * math.exp(-i / 9) for i in range(32)]
        filters.append("aecho=1:0.75:" + "|".join(map(str, delays)) + ":" + "|".join(f"{d:.5f}" for d in decays))
        filters.append("alimiter=limit=0.95:level=false:latency=true")
    return ",".join(filters) or "anull"


def effect_name(speed=100, reverb=0):
    speed, wet = float(speed), float(reverb) > 0
    name = "Slowed" if speed < 100 else "Sped Up" if speed > 100 else ""
    return name + " + Reverb" if name and wet else name or ("Reverb" if wet else "")


def source_position(line, speed=100):
    """FFplay's audio clock is after asetrate; map it to the source timeline."""
    match = re.match(r"\s*(-?\d+(?:\.\d+)?)\s+(?:M-A|A-V):", line)
    if match:
        return max(0, float(match[1]) * float(speed) / 100)
    return None


class PreviewPlayer:
    """Resolve/play off the Tk thread; stale requests can never start playback."""
    def __init__(self):
        self.events = queue.Queue()
        self.lock = threading.Lock()
        self.process = None
        self.generation = 0
        self.closed = False
        self.active = False
        self.position = 0.0

    def position_snapshot(self):
        with self.lock:
            return self.position

    def stop(self):
        with self.lock:
            self.generation += 1
            self.active = False
            process, self.process = self.process, None
        if process:
            def reap():
                try:
                    if process.poll() is None:
                        process.terminate()
                    process.wait(timeout=5)
                except (OSError, subprocess.TimeoutExpired):
                    process.kill()
                    process.wait()
            threading.Thread(target=reap, daemon=True).start()

    def play(self, source, folder="", speed=100, reverb=0, start=0, youtube=False, duration=25):
        duration = float(duration)
        if not math.isfinite(duration) or not 10 <= duration <= 180:
            raise ValueError("A prévia deve durar entre 10 e 180 segundos.")
        self.stop()
        with self.lock:
            generation = self.generation
            self.active = True
            self.position = max(0, float(start))
        def worker():
            process = None
            try:
                ffplay = executable("ffplay", folder)
                filters = effects_filter(speed, reverb)
                headers = {}
                url = source
                if youtube:
                    from yt_dlp import YoutubeDL
                    options = {"quiet": True, "no_warnings": True, "noplaylist": True,
                               "socket_timeout": 15, "retries": 1, "format": "bestaudio/best",
                               "js_runtimes": {"deno": {}, "node": {}}}
                    with YoutubeDL(options) as ydl:
                        info = ydl.extract_info(source, download=False)
                    url, headers = info["url"], info.get("http_headers") or {}
                command = [ffplay, "-nodisp", "-autoexit", "-loglevel", "info", "-stats", "-ss", str(max(0, float(start)))]
                if headers:
                    command += ["-headers", "".join(f"{key}: {value}\r\n" for key, value in headers.items() if "\n" not in str(value))]
                command += ["-i", url, "-t", str(duration * float(speed) / 100), "-af", filters + f",atrim=duration={duration:g}"]
                with self.lock:
                    if self.closed or generation != self.generation:
                        return
                    process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                               stderr=subprocess.PIPE, **process_options())
                    self.process = process
                self.events.put((generation, f"Ouvindo prévia de até {duration:g} segundos…"))
                # Stats use carriage returns rather than newline-delimited records.
                line = bytearray()
                while True:
                    chunk = process.stderr.read(1)
                    if not chunk:
                        break
                    if chunk in (b"\r", b"\n"):
                        position = source_position(line.decode("utf-8", errors="replace"), speed)
                        line.clear()
                        if position is not None:
                            with self.lock:
                                if generation == self.generation:
                                    self.position = max(self.position, position)
                    elif len(line) < 4096:
                        line.extend(chunk)
                process.stderr.close()
                process.wait()
                with self.lock:
                    current = generation == self.generation
                    if current:
                        self.process = None
                        self.active = False
                if current:
                    message = "Prévia encerrada." if process.returncode == 0 else "Não foi possível ouvir a prévia. A fonte pode estar indisponível; tente Abrir no YouTube."
                    self.events.put((generation, message))
            except Exception:
                with self.lock:
                    current = generation == self.generation
                    if current:
                        self.active = False
                if current:
                    self.events.put((generation, "Não foi possível iniciar a prévia. Confira FFmpeg/ffplay e a conexão."))
        threading.Thread(target=worker, daemon=True).start()

    def messages(self):
        result = []
        while True:
            try:
                generation, message = self.events.get_nowait()
            except queue.Empty:
                break
            if generation == self.generation:
                result.append(message)
        return result

    def close(self):
        self.closed = True
        self.stop()
