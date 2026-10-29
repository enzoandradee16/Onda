import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock
from unittest.mock import patch
import wave
import math
import array

from audio_tools import effects_filter
from engine import ask_duplicate, ask_review
from file_output import destination, publish
from library import LibraryStore
from metadata import MetadataError
from playlist_import import load_playlist, spotify_playlist
from review import apply_review


class LibraryTests(unittest.TestCase):
    def test_reopen_queue_excludes_secrets_and_restores_interrupted_job(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "state.sqlite3"
            store = LibraryStore(path)
            store.save_queue(
                [
                    {
                        "url": "https://youtube.com/watch?v=x",
                        "mode": "mp3",
                        "folder": folder,
                        "state": "Em andamento",
                        "review_metadata": True,
                        "spotify_client_secret": "SECRET_TEST",
                    },
                    {"url": "https://example.com/done", "state": "Concluído"},
                ]
            )
            restored = LibraryStore(path).load_queue()
            self.assertEqual(len(restored), 1)
            self.assertEqual(restored[0]["state"], "Na fila")
            self.assertTrue(restored[0]["review_metadata"])
            self.assertNotIn(b"SECRET_TEST", path.read_bytes())
            store.add_history(
                Path(folder) / "Room 5 - Make Luv.mp3", "MP3", "https://example.com"
            )
            self.assertEqual(len(LibraryStore(path).history("make luv")), 1)
            self.assertEqual(store.history("unrelated"), [])
            store.clear_history()
            self.assertEqual(store.history(), [])

    def test_duplicates_keep_replace_skip(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            output = root / "final"
            output.mkdir()
            target = output / "Artist - Song.mp3"
            target.write_bytes(b"original")
            for policy in ("keep", "skip", "replace"):
                source = root / target.name
                source.write_bytes(b"new")
                final, skipped = publish(source, output, policy)
                if policy == "keep":
                    self.assertEqual(Path(final).name, "Artist - Song (2).mp3")
                    self.assertEqual(target.read_bytes(), b"original")
                if policy == "skip":
                    self.assertTrue(skipped)
                    self.assertEqual(target.read_bytes(), b"original")
                if policy == "replace":
                    self.assertFalse(skipped)
                    self.assertEqual(target.read_bytes(), b"new")

    def test_organization_cannot_traverse_outside_destination(self):
        with tempfile.TemporaryDirectory() as folder:
            path = destination(
                {"folder": folder, "organization": "Artista / Álbum"},
                {"artists": ["../../Artist"], "album": "../Album"},
            )
            self.assertTrue(path.is_relative_to(Path(folder).resolve()))
            self.assertEqual(len(path.relative_to(Path(folder).resolve()).parts), 2)

    def test_review_preserves_origin_and_accepts_only_tag_fields(self):
        record = {
            "title": "Old",
            "artists": ["Old Artist"],
            "source_url": "https://example.com/original",
            "isrc": "ABC",
        }
        result = apply_review(
            record,
            {
                "title": "New",
                "artists": ["New Artist"],
                "album": "Album",
                "source_url": "https://evil.test",
                "track_number": 2,
            },
        )
        self.assertEqual(result["title"], "New")
        self.assertEqual(result["source_url"], record["source_url"])
        self.assertEqual(result["isrc"], "ABC")
        for changes in (
            {"title": ""},
            {"artists": []},
            {"cover_url": "file:///secret"},
            {"track_number": -1},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                apply_review(record, changes)

    def test_review_and_duplicate_request_reply(self):
        record = {"title": "Old", "artists": ["Artist"]}
        with contextlib.redirect_stdout(io.StringIO()):
            result = ask_review(record, io.StringIO('{"changes":{"title":"New"}}\n'))
        self.assertEqual(result["title"], "New")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "song.mp3"
            path.write_bytes(b"audio")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(
                    ask_duplicate(path, io.StringIO('{"choice":"keep"}\n')), "keep"
                )


class PlaylistTests(unittest.TestCase):
    def test_spotify_reads_only_track_list_not_session(self):
        playlist_id, track_id = "A" * 22, "B" * 22
        data = {
            "props": {
                "pageProps": {
                    "state": {
                        "data": {
                            "entity": {
                                "type": "playlist",
                                "id": playlist_id,
                                "title": "Test",
                                "trackList": [
                                    {
                                        "uri": "spotify:track:" + track_id,
                                        "title": "Song",
                                        "subtitle": "Artist",
                                        "duration": 200000,
                                    },
                                    {"uri": "spotify:episode:" + track_id},
                                ],
                            },
                            "session": {"token": "SECRET_TEST"},
                        }
                    }
                }
            }
        }
        result = spotify_playlist(
            '<script id="__NEXT_DATA__">' + json.dumps(data) + '</script>', playlist_id
        )
        self.assertEqual(len(result["tracks"]), 1)
        self.assertNotIn("SECRET_TEST", json.dumps(result))
        with self.assertRaises(MetadataError):
            spotify_playlist('<script id="__NEXT_DATA__">{}</script>', playlist_id)

    def test_deezer_playlist_list_and_invalid_hosts(self):
        client = Mock()
        client.get_json.side_effect = [
            {"title": "Playlist"},
            {
                "data": [
                    {
                        "id": 123,
                        "title": "Song",
                        "artist": {"name": "Artist"},
                        "duration": 200,
                    }
                ]
            },
        ]
        result = load_playlist("https://www.deezer.com/br/playlist/123", client)
        self.assertEqual(
            result["tracks"][0]["source_url"], "https://www.deezer.com/track/123"
        )
        for url in (
            "https://deezer.com.evil.test/playlist/123",
            "file:///playlist",
            "https://user:password@deezer.com/playlist/123",
        ):
            with self.subTest(url=url), self.assertRaises(MetadataError):
                load_playlist(url, client)


@unittest.skipUnless(os.environ.get("ONDA_FFMPEG"), "Requires FFmpeg")
class EffectRenderTests(unittest.TestCase):
    def test_direct_audio_review_and_duplicate_keep_end_to_end(self):
        import base64
        import functools
        import http.server
        import threading
        from engine import run_worker
        from mutagen.id3 import ID3

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            with wave.open(str(root / "source.wav"), "wb") as audio:
                audio.setparams((1, 2, 44100, 0, "NONE", "not compressed"))
                audio.writeframes(b"\x00\x00" * 44100)
            cover = root / "cover.png"
            cover.write_bytes(
                base64.b64decode(
                    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII="
                )
            )

            class Handler(http.server.SimpleHTTPRequestHandler):
                def log_message(self, *_):
                    pass

            server = http.server.ThreadingHTTPServer(
                ("127.0.0.1", 0), functools.partial(Handler, directory=folder)
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                config = {
                    "url": f"http://127.0.0.1:{server.server_port}/source.wav",
                    "mode": "mp3",
                    "folder": str(root / "out"),
                    "ffmpeg": os.environ["ONDA_FFMPEG"],
                    "review_metadata": True,
                    "organization": "Artista / Álbum",
                    "duplicate_policy": "ask",
                }
                reply = (
                    json.dumps(
                        {
                            "changes": {
                                "title": "Edited Song",
                                "artists": ["Edited Artist"],
                                "album": "Edited Album",
                                "cover_path": str(cover),
                            }
                        }
                    )
                    + "\n"
                )
                for attempt in (1, 2):
                    output = io.StringIO()
                    with (
                        patch("sys.stdin", io.StringIO(reply + '{"choice":"keep"}\n')),
                        contextlib.redirect_stdout(output),
                    ):
                        code = run_worker(config)
                    self.assertEqual(code, 0, output.getvalue())
                    events = [
                        json.loads(line)
                        for line in output.getvalue().splitlines()
                        if line.startswith("{")
                    ]
                    self.assertTrue(any(e["type"] == "review_metadata" for e in events))
                    self.assertEqual(
                        any(e["type"] == "choose_duplicate" for e in events),
                        attempt == 2,
                    )
                    path = Path(events[-1]["files"][0])
                    self.assertEqual(
                        path.parent, root / "out" / "Edited Artist" / "Edited Album"
                    )
                    self.assertEqual(
                        path.stem,
                        "Edited Artist - Edited Song"
                        + (" (2)" if attempt == 2 else ""),
                    )
                    self.assertEqual(str(ID3(path)["TIT2"]), "Edited Song")
                    self.assertEqual(
                        ID3(path).getall("APIC")[0].data, cover.read_bytes()
                    )
            finally:
                server.shutdown()
                server.server_close()
                thread.join()

    def test_slow_changes_pitch_duration_and_reverb_has_a_tail(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            source = root / "tone.wav"
            samples = array.array(
                "h",
                [
                    round(15000 * math.sin(2 * math.pi * 440 * n / 48000))
                    for n in range(48000)
                ],
            )
            with wave.open(str(source), "wb") as audio:
                audio.setparams((1, 2, 48000, 0, "NONE", "not compressed"))
                audio.writeframes(samples.tobytes())
            outputs = {}
            for label, speed, reverb in (
                ("dry", 100, 0),
                ("slow", 50, 0),
                ("fast", 150, 0),
                ("fast_wet", 125, 30),
                ("reverb", 100, 80),
                ("both", 80, 30),
            ):
                output = root / (label + ".wav")
                result = subprocess.run(
                    [
                        sys.executable,
                        str(Path(__file__).with_name("effects_worker.py")),
                    ],
                    input=json.dumps(
                        {
                            "source": str(source),
                            "output": str(output),
                            "speed": speed,
                            "reverb": reverb,
                            "ffmpeg": os.environ["ONDA_FFMPEG"],
                        }
                    )
                    + "\n",
                    text=True,
                    encoding="utf-8",
                    capture_output=True,
                    timeout=30,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                events = [json.loads(line) for line in result.stdout.splitlines()]
                self.assertEqual(events[-1]["type"], "done")
                self.assertTrue(any(row["type"] == "progress" for row in events))
                with wave.open(str(output)) as audio:
                    values = array.array("h", audio.readframes(audio.getnframes()))
                    outputs[label] = len(values) / audio.getframerate(), values
            self.assertAlmostEqual(outputs["dry"][0], 1, delta=0.02)
            self.assertAlmostEqual(outputs["slow"][0], 2, delta=0.02)
            self.assertAlmostEqual(outputs["fast"][0], 1 / 1.5, delta=0.02)
            self.assertGreater(outputs["fast_wet"][0], 0.8)
            # Zero crossings confirm slowed audio changes pitch as well as tempo.
            for label, expected in (("dry", 440), ("slow", 220), ("fast", 660)):
                values = outputs[label][1][4800:28800]
                crossings = sum(a <= 0 < b for a, b in zip(values, values[1:]))
                self.assertAlmostEqual(crossings / 0.5, expected, delta=5)
            self.assertGreater(outputs["reverb"][0], 1.5)
            self.assertGreater(max(abs(x) for x in outputs["reverb"][1][48000:]), 50)
            self.assertEqual(effects_filter(100, 0), "anull")
            self.assertNotIn("asetrate", effects_filter(100, 40))
            self.assertNotIn("aecho", effects_filter(80, 0))
            self.assertEqual(source.read_bytes()[44:], samples.tobytes())

    def test_export_keeps_tags_cover_and_refuses_original(self):
        from tagging import apply_tags
        from test_automation import catalog
        import base64
        from mutagen.id3 import ID3

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            source, output = root / "source.mp3", root / "effects.mp3"
            ffmpeg = str(
                Path(os.environ["ONDA_FFMPEG"])
                / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
            )
            subprocess.run(
                [
                    ffmpeg,
                    "-v",
                    "error",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=440:duration=1",
                    str(source),
                ],
                check=True,
            )
            cover = base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII="
            )
            apply_tags(
                source,
                catalog(),
                {"source_url": "https://example.com", "title": "Song"},
                (cover, "image/png"),
            )
            original = source.read_bytes()
            from effects_worker import render

            before = ID3(source)
            for speed, reverb, label in (
                (85, 20, "Slowed + Reverb"),
                (90, 0, "Slowed"),
                (125, 0, "Sped Up"),
                (125, 30, "Sped Up + Reverb"),
                (100, 30, "Reverb"),
                (100, 0, ""),
            ):
                with (
                    self.subTest(effect=label),
                    contextlib.redirect_stdout(io.StringIO()),
                ):
                    self.assertEqual(
                        render(
                            {
                                "source": str(source),
                                "output": str(output),
                                "speed": speed,
                                "reverb": reverb,
                                "replace": True,
                                "ffmpeg": os.environ["ONDA_FFMPEG"],
                            }
                        ),
                        0,
                    )
                    tags = ID3(output)
                    self.assertEqual(
                        str(tags["TIT2"]),
                        catalog()["title"] + (" - " + label if label else ""),
                    )
                    self.assertEqual(set(tags), set(before))
                    for key in before:
                        if key != "TIT2":
                            self.assertEqual(tags[key].pprint(), before[key].pprint())
                    self.assertEqual(tags.getall("APIC")[0].data, cover)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(
                    render(
                        {
                            "source": str(source),
                            "output": str(source),
                            "ffmpeg": os.environ["ONDA_FFMPEG"],
                        }
                    ),
                    1,
                )
            self.assertEqual(source.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
