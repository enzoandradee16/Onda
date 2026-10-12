"""Run: python -m unittest -v. Integration tests use ONDA_FFMPEG=path/to/bin."""
import functools
import http.server
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
import wave

from engine import build_options, reject_live, stop_process, validate_url


class ValidationTests(unittest.TestCase):
    def test_urls(self):
        self.assertEqual(validate_url(" https://youtu.be/example "), "https://youtu.be/example")
        for url in ("file:///secret", "javascript:alert(1)", "--exec calc", "https://a b.com", "https://x:bad"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_url(url)

    def test_service_boundaries(self):
        for host in ("open.spotify.com", "spotify.link", "music.apple.com", "OPEN.SPOTIFY.COM."):
            with self.subTest(host=host), self.assertRaisesRegex(ValueError, "aplicativo oficial"):
                validate_url("https://" + host + "/track/example")
        self.assertEqual(validate_url("https://notspotify.com/music"), "https://notspotify.com/music")

    def test_original_never_transcodes(self):
        options = build_options({"mode": "original", "folder": "."})
        self.assertEqual(options["postprocessors"], [])
        self.assertEqual(options["format"], "bestaudio")

    def test_video_fallback_obeys_limit(self):
        options = build_options({"mode": "video", "folder": ".", "height": 720})
        self.assertIn("best[height<=?720]", options["format"])
        self.assertTrue(options["noplaylist"])

    def test_live_rejected(self):
        self.assertIsNotNone(reject_live({"is_live": True}))
        self.assertIsNone(reject_live({"live_status": "was_live"}))

    def test_mp4_limits_apply_to_every_video_fallback(self):
        options = build_options({"mode": "mp4", "folder": ".", "height": 720, "fps": 30})
        for fallback in options["format"].split("/"):
            self.assertIn("[height<=?720][fps<=?30]", fallback)
        self.assertEqual(options["postprocessors"][0]["preferedformat"], "mp4")

    def test_stop_process(self):
        options = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session": True}
        process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], **options)
        try:
            stop_process(process)
            self.assertIsNotNone(process.wait(timeout=5))
        finally:
            if process.poll() is None:
                process.kill()


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


@unittest.skipUnless(os.environ.get("ONDA_FFMPEG"), "Set ONDA_FFMPEG to run real media integration tests")
class MediaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        with wave.open(str(cls.root / "tone.wav"), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(44100)
            audio.writeframes(b"\x00\x00" * 44100)
        ffmpeg = Path(os.environ["ONDA_FFMPEG"]) / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
        subprocess.run([str(ffmpeg), "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                        "color=c=blue:s=160x120:d=1", "-i", str(cls.root / "tone.wav"), "-c:v", "mpeg4",
                        "-c:a", "aac", "-shortest", str(cls.root / "video.mp4")], check=True)
        handler = functools.partial(QuietHandler, directory=str(cls.root))
        subprocess.run([str(ffmpeg), "-hide_banner", "-loglevel", "error", "-i", str(cls.root / "video.mp4"),
                        "-c:v", "libvpx-vp9", "-c:a", "libvorbis", str(cls.root / "video.webm")], check=True)
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.temp.cleanup()

    def worker(self, mode, name="tone.wav"):
        config = {"url": f"http://127.0.0.1:{self.server.server_port}/{name}", "mode": mode,
                  "folder": str(self.root / mode), "ffmpeg": os.environ["ONDA_FFMPEG"]}
        result = subprocess.run([sys.executable, str(Path(__file__).with_name("engine.py"))],
                                input=json.dumps(config) + "\n", text=True, encoding="utf-8",
                                capture_output=True, timeout=45)
        events = [json.loads(line) for line in result.stdout.splitlines() if line.startswith("{")]
        return result, events

    def test_audio_formats_and_saved_files(self):
        for mode, extension in (("original", ".wav"), ("mp3", ".mp3"), ("m4a", ".m4a"), ("flac", ".flac")):
            with self.subTest(mode=mode):
                result, events = self.worker(mode)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(events[-1]["type"], "done")
                path = Path(events[-1]["files"][0])
                self.assertEqual(path.suffix, extension)
                self.assertGreater(path.stat().st_size, 0)
                self.assertTrue(any(e["type"] == "progress" for e in events))
                kinds = [e["type"] for e in events]
                self.assertLess(kinds.index("estimate"), kinds.index("progress"))
                self.assertEqual(next(e["size"] for e in events if e["type"] == "file"), path.stat().st_size)
                if mode == "original":
                    self.assertEqual(path.read_bytes(), (self.root / "tone.wav").read_bytes())

    def test_video_remux(self):
        result, events = self.worker("video", "video.mp4")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(Path(events[-1]["files"][0]).suffix, ".mkv")

    def test_mp4_output_and_webm_conversion(self):
        for source in ("video.mp4", "video.webm"):
            with self.subTest(source=source):
                result, events = self.worker("mp4", source)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                path = Path(events[-1]["files"][0])
                self.assertEqual(path.suffix, ".mp4")
                probe = Path(os.environ["ONDA_FFMPEG"]) / ("ffprobe.exe" if os.name == "nt" else "ffprobe")
                info = json.loads(subprocess.check_output([str(probe), "-v", "error", "-show_streams", "-of", "json", str(path)]))
                self.assertEqual({stream["codec_type"] for stream in info["streams"]}, {"audio", "video"})
                if source == "video.mp4":
                    self.assertEqual(path.read_bytes(), (self.root / source).read_bytes())

    def test_http_error_is_not_success(self):
        result, events = self.worker("original", "missing.wav")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(events[-1]["type"], "error")
        self.assertFalse(any(e["type"] == "done" for e in events))

    @unittest.skipUnless(os.name == "nt", "Windows process-tree verification")
    def test_cancel_stops_ffmpeg_child(self):
        import ctypes
        from ctypes import wintypes
        ffmpeg = str(Path(os.environ["ONDA_FFMPEG"]) / "ffmpeg.exe")
        code = ("import subprocess,sys; "
                "p=subprocess.Popen([sys.argv[1],'-hide_banner','-loglevel','error','-re','-f','lavfi',"
                "'-i','sine=frequency=440:duration=60','-f','null','-'],"
                "stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); "
                "print(p.pid,flush=True); p.wait()")
        parent = subprocess.Popen([sys.executable, "-u", "-c", code, ffmpeg], stdout=subprocess.PIPE,
                                  text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = None
        try:
            child_pid = int(parent.stdout.readline().strip())
            handle = kernel.OpenProcess(0x00100000, False, child_pid)
            self.assertTrue(handle)
            stop_process(parent)
            parent.wait(timeout=5)
            self.assertEqual(kernel.WaitForSingleObject(handle, 5000), 0, "FFmpeg child still running")
        finally:
            stop_process(parent)
            parent.wait(timeout=5)
            parent.stdout.close()
            if handle:
                kernel.CloseHandle(handle)


if __name__ == "__main__":
    unittest.main()
