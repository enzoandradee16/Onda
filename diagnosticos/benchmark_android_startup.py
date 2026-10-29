import json
import argparse
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import time

SDK = (
    os.environ.get('ANDROID_SDK_ROOT')
    or os.environ.get('ANDROID_HOME')
    or r'C:\Program Files (x86)\Android\android-sdk'
)
ADB = shutil.which('adb') or str(Path(SDK) / 'platform-tools/adb.exe')
SERIAL = 'emulator-5580'
OUT = Path(os.environ.get('ONDA_BENCH_OUT', str(Path(__file__).parent / 'resultados')))
APP = 'br.com.onda.mobile'


def adb(*args):
    return subprocess.check_output(
        [ADB, '-s', SERIAL, *args], text=True, encoding='utf-8', errors='replace'
    )


def stat(pid):
    value = adb('shell', 'run-as', APP, 'cat', f'/proc/{pid}/stat')
    tokens = value[value.rfind(')') + 2 :].split()
    return sum(int(tokens[i]) for i in (11, 12))


def main():
    global ADB, SERIAL
    parser = argparse.ArgumentParser()
    parser.add_argument('--adb', default=ADB)
    parser.add_argument('--serial', default=SERIAL)
    args = parser.parse_args()
    ADB = args.adb
    SERIAL = args.serial
    OUT.mkdir(exist_ok=True, parents=True)
    result = {'startup': []}
    for repeat in range(5):
        adb('shell', 'am', 'force-stop', APP)
        time.sleep(1)
        output = adb('shell', 'am', 'start', '-W', '-n', APP + '/.MainActivity')
        metrics = {
            key: int(value)
            for key, value in re.findall(
                r'^(ThisTime|TotalTime|WaitTime):\s*(\d+)', output, re.M
            )
        }
        assert 'TotalTime' in metrics, output
        time.sleep(1)
        memory = adb('shell', 'dumpsys', 'meminfo', APP)
        pss = re.search(r'TOTAL PSS:\s*(\d+)', memory)
        if not pss:
            pss = re.search(r'\bTOTAL\s+(\d+)', memory)
        assert pss, memory
        result['startup'].append(
            {'repeat': repeat, **metrics, 'idle_pss_mb': int(pss[1]) / 1024}
        )
        print(result['startup'][-1], flush=True)
    pid = adb('shell', 'pidof', APP).strip().split()[0]
    hz = int(adb('shell', 'getconf', 'CLK_TCK').strip())
    cores = int(adb('shell', 'getconf', '_NPROCESSORS_ONLN').strip())
    before = stat(pid)
    start = time.perf_counter()
    time.sleep(10)
    after = stat(pid)
    duration = time.perf_counter() - start
    result['idle_without_instrumentation'] = {
        'seconds': duration,
        'cpu_s': (after - before) / hz,
        'cpu_one_core_pct': (after - before) / hz / duration * 100,
        'cpu_machine_pct': (after - before) / hz / duration * 100 / cores,
        'logical_cpus': cores,
    }
    (OUT / 'android-startup.json').write_text(
        json.dumps(result, indent=2), encoding='utf-8'
    )
    adb('shell', 'am', 'force-stop', APP)


if __name__ == '__main__':
    main()
