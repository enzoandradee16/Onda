import gc
import json
import os
from pathlib import Path
import sys
import tempfile
import time

import argparse

parser = argparse.ArgumentParser(description="Measure navigation through ONDA settings")
parser.add_argument(
    "source", nargs="?", default=str(Path(__file__).resolve().parents[1] / "Onda")
)
parser.add_argument(
    "output",
    nargs="?",
    default=str(Path(__file__).parent / "resultados/settings-navigation.json"),
)
args = parser.parse_args()
sys.path.insert(0, str(Path(args.source).resolve()))
output = Path(args.output)
output.parent.mkdir(parents=True, exist_ok=True)
gc.disable()
from app import App

with tempfile.TemporaryDirectory() as folder:
    os.environ['LOCALAPPDATA'] = folder
    app = App(show_welcome=False)
    try:
        app.update()
        start = time.perf_counter()
        app.show_settings()
        app.update()
        opening = time.perf_counter() - start
        timings = []
        for _ in range(4):
            for tab in app.settings_pages.tabs():
                start = time.perf_counter()
                app.settings_pages.select(tab)
                app.update()
                timings.append((time.perf_counter() - start) * 1000)
            app.settings_window.withdraw()
            app.update()
            start = time.perf_counter()
            app.show_settings()
            app.update()
            timings.append((time.perf_counter() - start) * 1000)
        output.write_text(
            json.dumps({'first_open_s': opening, 'navigation_ms': timings}, indent=2),
            encoding='utf-8',
        )
        print(
            'Opening:',
            opening,
            'navigation median:',
            __import__('statistics').median(timings),
            'max:',
            max(timings),
        )
    finally:
        app.destroy()
        gc.collect()
