"""Bootstrap for the private, relocatable Windows runtime."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import traceback

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "_runtime"
os.environ["PATH"] = os.pathsep.join((str(TOOLS / "ffmpeg"), str(TOOLS / "node"), os.environ.get("PATH", "")))
os.environ["ONDA_DOWNLOADS"] = str(Path.home() / "Downloads" / "Onda")
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUTF8"] = "1"
os.environ["PYTHONNOUSERSITE"] = "1"
os.environ["TCL_LIBRARY"] = str(TOOLS / "python" / "tcl" / "tcl8.6")
os.environ["TK_LIBRARY"] = str(TOOLS / "python" / "tcl" / "tk8.6")


def create_app(*, show_welcome=True):
    from app import App
    from engine import binaries
    app = App(show_welcome=show_welcome)
    if not binaries(app.ffmpeg.get()):
        app.ffmpeg.set(str(TOOLS / "ffmpeg"))
    try:
        app.iconbitmap(str(ROOT / "onda.ico"))
    except Exception:
        pass
    return app


def self_test(target):
    """A non-network diagnostic, with isolated settings and no persistent changes."""
    report = {"ok": False, "python": sys.version, "prefix": sys.prefix}
    try:
        import requests, mutagen, yt_dlp, gallery_dl, curl_cffi, PIL
        import instagram_media, twitter_media, tiktok_media, kwai, media_picker
        from yt_dlp.version import __version__
        report["yt_dlp"] = __version__
        report["gallery_dl"] = gallery_dl.version.__version__
        report["curl_cffi"] = curl_cffi.__version__
        report["Pillow"] = PIL.__version__
        report["tools"] = {}
        for tool, flag in (("ffmpeg", "-version"), ("ffprobe", "-version"), ("ffplay", "-version"), ("node", "--version")):
            result = subprocess.run([str(TOOLS / ("node" if tool == "node" else "ffmpeg") / (tool + ".exe")), flag],
                                    capture_output=True, text=True, timeout=15, creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode:
                raise RuntimeError(tool + " falhou")
            report["tools"][tool] = result.stdout.splitlines()[0]
        with tempfile.TemporaryDirectory(prefix="onda-diagnostic-") as temporary:
            os.environ["LOCALAPPDATA"] = temporary
            app = create_app(show_welcome=False)
            try:
                app.update()
                report["tabs"] = len(app.pages.tabs())
                report["downloads"] = app.folder.get()
                report["ok"] = report["tabs"] == 6
            finally:
                app.destroy()
    except Exception:
        report["error"] = traceback.format_exc()
    Path(target).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--self-test":
        sys.exit(self_test(sys.argv[2]))
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Onda.Desktop")
        from single_instance import run_single_instance
        sys.exit(run_single_instance(create_app))
    except Exception:
        log = Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir())) / "Onda" / "startup-error.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(traceback.format_exc(), encoding="utf-8")
        import tkinter.messagebox
        tkinter.messagebox.showerror("Onda", "Não foi possível iniciar o aplicativo.\nDetalhes: " + str(log))
        sys.exit(1)
