"""Integration checks for an AUDIT build only, never the production AppId."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(audit, bundle, output):
    audit, bundle, output = map(lambda p: Path(p).resolve(), (audit, bundle, output))
    recipe = (audit/'backend/InstallerAudit.iss').read_text(encoding='utf8')
    assert '190D43B2-9B31-47EE-A14D-94DB3A2EC850' in recipe
    assert 'C522DFD9-6BF4-4FE0-9CE4-5D3C5C88E470' not in recipe
    assert '{userdesktop}' not in recipe and '{group}' not in recipe
    output.mkdir(parents=True, exist_ok=False)
    setup = audit/'Onda-1.2.0-Setup-Windows-x64.exe'
    backend = audit/'backend/Onda-1.2.0-Setup-Windows-x64.exe'
    checks = []

    def run(args, expected=0, timeout=180, env=None):
        result = subprocess.run(list(map(str, args)), timeout=timeout, env=env)
        assert result.returncode == expected, (args[0], result.returncode, expected)
        return result.returncode

    def install(exe, target, name, desktop=False):
        run([exe, '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-', '/DIR='+str(target),
             '/TASKS='+('desktopicon' if desktop else ''), '/ONDAPROGRESS='+str(output/(name+'-progress.txt')),
             '/LOG='+str(output/(name+'.log'))])
        files = [p for p in (bundle/'Onda').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc']
        for source in files:
            assert digest(source) == digest(target/source.relative_to(bundle)), source
        assert (output/(name+'-progress.txt')).is_file()
        assert (target/'unins000.exe').is_file()
        checks.append({'check': name, 'ok': True, 'sources_checked': len(files)})

    def markers(target):
        settings = target/'audit-profile/settings.json'
        settings.parent.mkdir(exist_ok=True)
        settings.write_text('{"preserve":true}', encoding='utf8')
        media = target/'audit-profile/downloads/arquivo-do-usuário.mp3'
        media.parent.mkdir(exist_ok=True)
        media.write_bytes(b'synthetic user media')
        return {p: p.read_bytes() for p in (settings, media)}

    def preserved(values):
        assert all(p.is_file() and p.read_bytes() == data for p, data in values.items())

    def uninstall(target, name, values):
        run([target/'unins000.exe', '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/LOG='+str(output/(name+'.log'))])
        # Inno's bootstrap may return before its detached copy completes.
        deadline = time.monotonic()+30
        while (target/'Onda.exe').exists() and time.monotonic() < deadline:
            time.sleep(.1)
        assert not (target/'Onda.exe').exists()
        preserved(values)
        checks.append({'check': name, 'ok': True, 'personal_files_preserved': True})

    run([setup, '--self-test', output/'frontend-self-test.json'])
    assert json.loads((output/'frontend-self-test.json').read_text())['ok']
    checks.append({'check': 'frontend-self-test', 'ok': True})
    fresh = output/'instalação nova com espaços'
    install(setup, fresh, 'fresh-custom-install')
    assert not (audit/'shortcuts/desktop/Onda Installer Audit.lnk').exists()
    values = markers(fresh)
    env = dict(os.environ, LOCALAPPDATA=str(output/'launcher-profile'), QT_QPA_PLATFORM='offscreen', QSG_RHI_BACKEND='software')
    run([fresh/'Onda.exe', '--qt-self-test', output/'installed-launcher.json'], env=env)
    assert json.loads((output/'installed-launcher.json').read_text(encoding='utf8'))['ok']
    checks.append({'check': 'installed-qt-launcher', 'ok': True})
    uninstall(fresh, 'fresh-custom-uninstall', values)

    existing = output/'instalação anterior'
    install(backend, existing, 'classic-install')
    values = markers(existing)
    install(setup, existing, 'custom-upgrade', desktop=True)
    preserved(values)
    for name in ('menu/Onda Installer Audit.lnk', 'menu/Desinstalar Onda.lnk', 'desktop/Onda Installer Audit.lnk'):
        assert (audit/'shortcuts'/name).is_file(), name
    checks.append({'check': 'shortcuts-and-upgrade-preservation', 'ok': True})
    uninstall(existing, 'custom-upgrade-uninstall', values)
    assert not (audit/'shortcuts/desktop/Onda Installer Audit.lnk').exists()
    blocked = output/'not-a-directory'
    blocked.write_text('preserve', encoding='utf8')
    failed = subprocess.run([str(setup), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-',
        '/DIR='+str(blocked), '/LOG='+str(output/'failure.log')], timeout=120)
    assert failed.returncode != 0
    assert blocked.read_text() == 'preserve'
    checks.append({'check': 'backend-failure-propagated', 'ok': True, 'exit_code': failed.returncode})
    (output/'results.json').write_text(json.dumps({'ok': True, 'checks': checks}, indent=2), encoding='utf8')
    print(json.dumps(checks, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    verify(args.audit, args.bundle, args.output)
