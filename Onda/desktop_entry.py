"""Bootstrap for the private, relocatable Windows runtime."""
from i18n import tr
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import traceback

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "_runtime"
os.environ["PATH"] = os.pathsep.join((str(TOOLS / "node"), os.environ.get("PATH", "")))
os.environ["ONDA_DOWNLOADS"] = str(Path.home() / "Downloads" / "Onda")
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUTF8"] = "1"
os.environ["PYTHONNOUSERSITE"] = "1"
os.environ["TCL_LIBRARY"] = str(TOOLS / "python" / "tcl" / "tcl8.6")
os.environ["TK_LIBRARY"] = str(TOOLS / "python" / "tcl" / "tk8.6")


def create_app(*, show_welcome=True, prepare_tools=True):
    from ffmpeg_runtime import existing_folder, download_with_window
    folder = existing_folder()
    if folder is None and prepare_tools:
        folder = download_with_window()
    if folder:
        os.environ["PATH"] = str(folder) + os.pathsep + os.environ.get("PATH", "")
    from app import App
    app = App(show_welcome=show_welcome)
    if folder:
        app.ffmpeg.set(str(folder))
    elif folder is None and prepare_tools:
        app.ffmpeg.set("")
        app.write_log("FFmpeg ainda não preparado. Use Configurações → Ferramentas → Preparar FFmpeg.")
    try:
        from window_icons import apply_window_icon
        apply_window_icon(app)
    except Exception:
        pass
    return app


def self_test(target):
    """A non-network diagnostic, with isolated settings and no persistent changes."""
    report = {"ok": False, "python": sys.version, "prefix": sys.prefix}
    try:
        from importlib import import_module
        for module in ('requests','mutagen','yt_dlp','instagram_media','twitter_media','tiktok_media','kwai','media_picker'):
            import_module(module)
        import gallery_dl, curl_cffi, PIL
        from yt_dlp.version import __version__
        report["yt_dlp"] = __version__
        report["gallery_dl"] = gallery_dl.version.__version__
        report["curl_cffi"] = curl_cffi.__version__
        report["Pillow"] = PIL.__version__
        report["tools"] = {}
        from ffmpeg_runtime import existing_folder
        media_folder = existing_folder()
        report["media_tools"] = "ready" if media_folder else "downloaded_on_first_launch"
        checks = [(TOOLS / "node/node.exe", "--version")]
        if media_folder:
            checks.extend((media_folder / (name + ".exe"), "-version") for name in ("ffmpeg", "ffprobe", "ffplay"))
        for executable, flag in checks:
            tool = executable.stem
            result = subprocess.run([str(executable), flag],
                                    capture_output=True, text=True, timeout=15, creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode:
                raise RuntimeError(tool + " falhou")
            report["tools"][tool] = result.stdout.splitlines()[0]
        with tempfile.TemporaryDirectory(prefix="onda-diagnostic-") as temporary:
            os.environ["LOCALAPPDATA"] = temporary
            app = create_app(show_welcome=False, prepare_tools=False)
            try:
                app.update()
                report["tabs"] = len(app.pages.tabs())
                report["downloads"] = app.folder.get()
                report["ok"] = report["tabs"] == 9
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
        tkinter.messagebox.showerror(tr("Onda"), tr("Não foi possível iniciar o aplicativo.\nDetalhes: " + str(log)))
        sys.exit(1)
