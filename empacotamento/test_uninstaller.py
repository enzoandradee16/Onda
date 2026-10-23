"""Exercise only the compiled audit uninstaller with isolated synthetic data."""
import argparse
import base64
import json
import subprocess
import time
from pathlib import Path
import winreg

AUDIT = r'Software\Microsoft\Windows\CurrentVersion\Uninstall\{190D43B2-9B31-47EE-A14D-94DB3A2EC850}_is1'
PRODUCTION = r'Software\Microsoft\Windows\CurrentVersion\Uninstall\{C522DFD9-6BF4-4FE0-9CE4-5D3C5C88E470}_is1'


def registry(path):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, access=winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
            return {name: winreg.QueryValueEx(key, name)[0] for name in ('InstallLocation', 'UninstallString', 'QuietUninstallString')}
    except FileNotFoundError:
        return None


def verify(audit, output):
    audit, output = Path(audit).resolve(), Path(output).resolve()
    recipe = (audit/'backend/InstallerAudit.iss').read_text(encoding='utf8')
    assert '190D43B2-9B31-47EE-A14D-94DB3A2EC850' in recipe and 'C522DFD9-6BF4-4FE0-9CE4-5D3C5C88E470' not in recipe
    assert registry(AUDIT) is None, 'Another audit installation is still registered'
    original_registry = registry(PRODUCTION)
    output.mkdir(parents=True, exist_ok=False)
    checks = []

    def front(target, name, switches=(), mode='--audit-remove'):
        report = output/(name+'.json')
        subprocess.run([str(target/'Desinstalar ONDA.exe'), mode, str(report), *switches], timeout=30)
        deadline = time.monotonic()+150
        while not report.exists() and time.monotonic()<deadline:
            time.sleep(.1)
        assert report.exists(), name+' did not finish'
        result = json.loads(report.read_text(encoding='utf-8-sig'))
        if 'error_base64' in result:
            result['error'] = base64.b64decode(result['error_base64']).decode('utf8')
        time.sleep(.1)
        return result

    selftest = output/'self-test.json'
    subprocess.run([str(audit/'uninstaller/Desinstalar ONDA.exe'), '--self-test', str(selftest)], check=True, timeout=30)
    result = json.loads(selftest.read_text(encoding='utf-8-sig'))
    assert result['ok'] and result['keeps_data_and_tools_by_default'] and result['languages']==['pt-BR','es','en']
    checks.append({'check':'frontend-defaults-languages-and-states','ok':True})
    for index, (delete_data, delete_tools) in enumerate(((False,False),(True,False),(False,True),(True,True))):
        target = output/f'installation-{index}'
        subprocess.run([str(audit/'Onda-1.2.0-Setup-Windows-x64.exe'), '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-',
                        '/DIR='+str(target),'/LOG='+str(output/f'install-{index}.log')], check=True, timeout=180)
        registered = registry(AUDIT)
        assert registered and registered['UninstallString']=='"'+str(target/'Desinstalar ONDA.exe')+'"', registered
        assert 'unins' in registered['QuietUninstallString'] and '/VERYSILENT' in registered['QuietUninstallString']
        profile = target/'audit-profile';profile.mkdir(exist_ok=True)
        personal = [profile/name for name in ('settings.json','language.json','library.sqlite3')]
        tools = [profile/'tools/ffmpeg/9.0.2'/name for name in ('ffmpeg.exe','ffprobe.exe','ffplay.exe','LICENSE.txt','README.txt','verified.json')]
        protected = [profile/'downloads/music.mp3',profile/'cookies.txt',profile/'unrelated.txt',profile/'tools/ffmpeg/9.0.2/user-tool.exe']
        for path in personal+tools+protected:
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'synthetic '+path.name.encode())
        originals={p:p.read_bytes() for p in personal+tools+protected}
        if index==0:
            assert front(target,'cancel',mode='--audit-ui-cancel')['cancelled']
            assert (target/'Onda.exe').is_file() and registry(AUDIT)
            assert all(p.read_bytes()==value for p,value in originals.items())
            checks.append({'check':'cancel-button-preserves-installation-and-data','ok':True})
        if index==3:
            # Reinstall over the same folder before exercising the custom frontend.
            # Inno rewrites its data file on upgrade, so its integrity stamp must refresh.
            subprocess.run([str(audit/'Onda-1.2.0-Setup-Windows-x64.exe'),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-',
                            '/DIR='+str(target),'/LOG='+str(output/'upgrade.log')],check=True,timeout=180)
            assert all(p.read_bytes()==value for p,value in originals.items())
            stamp=target/'uninstall-engine.sha256';original=stamp.read_bytes();stamp.write_text('tampered')
            result=front(target,'tampered')
            assert not result['ok'] and (target/'Onda.exe').exists() and registry(AUDIT)
            stamp.write_bytes(original)
            checks.append({'check':'tampered-backend-rejected-before-removal','ok':True})
        switches=(['--remove-data'] if delete_data else [])+(['--remove-tools'] if delete_tools else [])
        result=front(target,f'remove-{index}',switches,'--audit-ui-remove' if index in (0,3) else '--audit-remove')
        assert result['ok'],result
        assert not (target/'Onda.exe').exists() and not (target/'Desinstalar ONDA.exe').exists() and registry(AUDIT) is None
        for paths,deleted in ((personal,delete_data),(tools,delete_tools)):
            for path in paths:
                assert not path.exists() if deleted else path.is_file() and path.read_bytes()==originals[path],path
        assert all(p.is_file() and p.read_bytes()==originals[p] for p in protected)
        assert registry(PRODUCTION)==original_registry
        checks.append({'check':f'cleanup-data-{delete_data}-tools-{delete_tools}','ok':True,'media_cookies_and_custom_tools_preserved':True,'ui_worker':index in (0,3)})
    report={'ok':True,'checks':checks,'production_registration_unchanged':True}
    (output/'results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();verify(args.audit,args.output)
