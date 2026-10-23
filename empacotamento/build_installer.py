"""Build ONDA's standalone installer with its embedded transactional backend."""
import argparse
import hashlib
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def build(bundle, output, *, audit=False):
    bundle = Path(bundle).resolve()
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    version = re.search(r"^VERSION\s*=\s*'([^']+)'", (ROOT/'Onda/app_version.py').read_text(), re.M)[1]
    numeric = '.'.join(re.match(r'(\d+)\.(\d+)\.(\d+)', version).groups())+'.0'
    work = output/'backend'
    work.mkdir(exist_ok=True)
    recipe = ROOT/'empacotamento/Onda.iss'
    if audit:
        # Every registry key, shortcut, mutex and personal-data path is isolated.
        text = recipe.read_text(encoding='utf8')
        text = text.replace('C522DFD9-6BF4-4FE0-9CE4-5D3C5C88E470', '190D43B2-9B31-47EE-A14D-94DB3A2EC850')
        text = text.replace('DefaultGroupName=Onda', 'DefaultGroupName=Onda Installer Audit')
        text = text.replace('{group}\\Onda', '{group}\\Onda Installer Audit')
        text = text.replace('{userdesktop}\\Onda', '{userdesktop}\\Onda Installer Audit')
        text = text.replace("ExpandConstant('{localappdata}\\Onda')", "ExpandConstant('{app}\\audit-profile')")
        text = text.replace('CloseApplications=yes', 'CloseApplications=no')
        text = text.replace('{group}', str(output/'shortcuts/menu'))
        text = text.replace('{userdesktop}', str(output/'shortcuts/desktop'))
        recipe = work/'InstallerAudit.iss'
        recipe.write_text(text, encoding='utf8')
    subprocess.run([str(ROOT/'Android/build/tools/inno/ISCC.exe'), '/Qp',
        '/DPackageRoot='+str(bundle), '/DInstallerOutput='+str(work), str(recipe)], check=True)
    backend = work/f'Onda-{version}-Setup-Windows-x64.exe'
    digest = hashlib.sha256(backend.read_bytes()).hexdigest()
    (work/'engine.sha256').write_text(digest, encoding='ascii')
    (work/'InstallerVersion.cs').write_text(
        'using System.Reflection;\n[assembly: AssemblyTitle("Instalar ONDA")]\n'
        '[assembly: AssemblyProduct("ONDA Installer")]\n'
        f'[assembly: AssemblyVersion("{numeric}")]\n[assembly: AssemblyFileVersion("{numeric}")]\n'
        f'[assembly: AssemblyInformationalVersion("{version}")]\n', encoding='utf8')
    manifest = (ROOT/'empacotamento/Installer.manifest').read_text(encoding='utf8')
    manifest = re.sub(r'(<assemblyIdentity[^>]*version=")[^"]+', lambda m: m[1]+numeric, manifest)
    (work/'Installer.manifest').write_text(manifest, encoding='utf8')
    framework = Path('C:/Windows/Microsoft.NET/Framework64/v4.0.30319')
    target = output/f'Onda-{version}-Setup-Windows-x64.exe'
    args = [str(framework/'csc.exe'), '/nologo', '/target:winexe', '/platform:x64', '/optimize+',
        '/reference:System.Windows.Forms.dll', '/reference:System.Drawing.dll', '/reference:System.Xaml.dll',
        *['/reference:'+str(framework/'WPF'/name) for name in ('WindowsBase.dll', 'PresentationCore.dll', 'PresentationFramework.dll')],
        '/win32icon:'+str(bundle/'onda.ico'), '/win32manifest:'+str(work/'Installer.manifest'),
        '/resource:'+str(backend)+',Onda.InstallEngine',
        '/resource:'+str(work/'engine.sha256')+',Onda.EngineHash',
        '/resource:'+str(ROOT/'empacotamento/Installer.xaml')+',Onda.InstallerView',
        '/out:'+str(target), str(ROOT/'empacotamento/Installer.cs'), str(work/'InstallerVersion.cs')]
    subprocess.run(args, check=True)
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--audit', action='store_true')
    options = parser.parse_args()
    print(build(options.bundle, options.output, audit=options.audit))
