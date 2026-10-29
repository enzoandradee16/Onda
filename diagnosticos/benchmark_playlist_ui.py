import json
import os
from pathlib import Path
import statistics
import sys
import tempfile
import time

import argparse

parser = argparse.ArgumentParser(
    description="Measure the event loop while loading 5,000 synthetic tracks"
)
parser.add_argument(
    "source", nargs="?", default=str(Path(__file__).resolve().parents[1] / "Onda")
)
parser.add_argument(
    "destination",
    nargs="?",
    default=str(Path(__file__).parent / "resultados/playlist-ui.json"),
)
args = parser.parse_args()
source, destination = Path(args.source).resolve(), Path(args.destination).resolve()
destination.parent.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(source))
scratch = tempfile.TemporaryDirectory()
os.environ['LOCALAPPDATA'] = scratch.name
from app import App

app = App(show_welcome=False)
app.withdraw()
page = app.playlist_page
if hasattr(page, 'ensure_ready'):
    page = page.ensure_ready()
app.update()
tracks = [
    {
        'title': f'Música {i}',
        'artists': [f'ArtistaZ{i%20}'],
        'source_url': f'https://example.com/{i}',
        'duration_ms': 180000,
    }
    for i in range(5000)
]
results = []
for repeat in range(3):
    lag = []
    alive = True
    deadline = time.perf_counter() + 0.001

    def heartbeat():
        global deadline
        if not alive:
            return
        now = time.perf_counter()
        lag.append(max(0, (now - deadline) * 1000))
        deadline = now + 0.001
        app.after(1, heartbeat)

    app.after(1, heartbeat)
    start = time.perf_counter()
    page.display({'title': 'Diagnóstico sintético', 'tracks': tracks, 'note': ''})
    while page.busy:
        app.update()
        time.sleep(0.001)
    app.update()
    loaded = time.perf_counter() - start
    for term in ('art', 'artis', 'artistaz', 'artistaz1', 'artistaz19'):
        page.filter_text.set(term)
    until = time.perf_counter() + 0.2
    while time.perf_counter() < until:
        app.update()
        time.sleep(0.001)
    assert len(page.table.get_children()) == 250
    results.append(
        {
            'load_s': loaded,
            'maximum_event_loop_delay_ms': max(lag, default=0),
            'visible': 250,
            'records': 5000,
        }
    )
    alive = False
app.destroy()
scratch.cleanup()
destination.write_text(json.dumps({'trials': results}, indent=2), encoding='utf-8')
print(results)
