"""Build the small WebView2 host; the Evergreen runtime stays system-managed."""

import argparse
import io
from pathlib import Path
import subprocess
import urllib.request
import zipfile

VERSION = '1.0.4314.35'
ROOT = Path(__file__).resolve().parents[1]


def build(target):
    target = Path(target).resolve()
    target.mkdir(parents=True, exist_ok=True)
    url = f'https://api.nuget.org/v3-flatcontainer/microsoft.web.webview2/{VERSION}/microsoft.web.webview2.{VERSION}.nupkg'
    with urllib.request.urlopen(url, timeout=60) as response:
        data = response.read(50 * 1024 * 1024)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for name in (
            'lib/net462/Microsoft.Web.WebView2.Core.dll',
            'lib/net462/Microsoft.Web.WebView2.WinForms.dll',
            'runtimes/win-x64/native/WebView2Loader.dll',
        ):
            (target / Path(name).name).write_bytes(archive.read(name))
        for name in archive.namelist():
            if Path(name).name.lower().startswith('license') and not name.endswith('/'):
                (target / ('WebView2-' + Path(name).name)).write_bytes(archive.read(name))
    subprocess.run([
        'C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe',
        '/nologo', '/target:winexe', '/platform:x64', '/optimize+',
        '/reference:System.Windows.Forms.dll', '/reference:System.Drawing.dll',
        '/reference:System.Security.dll',
        '/win32icon:' + str(ROOT / 'Portatil/onda.ico'),
        '/reference:' + str(target / 'Microsoft.Web.WebView2.Core.dll'),
        '/reference:' + str(target / 'Microsoft.Web.WebView2.WinForms.dll'),
        '/out:' + str(target / 'InstagramSession.exe'),
        str(ROOT / 'empacotamento/InstagramSession.cs'),
    ], check=True)
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', type=Path, default=ROOT / 'Portatil/_runtime/browser-session')
    print(build(parser.parse_args().target))
