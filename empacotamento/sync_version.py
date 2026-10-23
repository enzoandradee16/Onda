"""Synchronize Windows packaging metadata before compiling the launcher/installer."""
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def sync_version(root=ROOT):
    source=(root/'Onda/app_version.py').read_text(encoding='utf-8')
    version=re.search(r"^VERSION\s*=\s*['\"]([^'\"]+)['\"]",source,re.M).group(1)
    match=re.fullmatch(r'(\d+)\.(\d+)\.(\d+)(?:-(?:alpha|beta|rc)\.?\d+)?',version)
    if not match:raise ValueError('Invalid Windows application version')
    numeric='.'.join(match.groups())+'.0'
    launcher=root/'empacotamento/Launcher.cs'
    text=launcher.read_text(encoding='utf-8')
    for attribute,value in [('AssemblyVersion',numeric),('AssemblyFileVersion',numeric),('AssemblyInformationalVersion',version)]:
        text,count=re.subn(r'(\[assembly: '+attribute+r'\(")[^"]+("\)\])',lambda m:m[1]+value+m[2],text)
        if count!=1:raise ValueError('Missing version attribute: '+attribute)
    launcher.write_text(text,encoding='utf-8')
    installer=root/'empacotamento/Onda.iss'
    text=installer.read_text(encoding='utf-8')
    for key,value in [('UninstallDisplayName','Onda '+version),('AppVersion',version),('VersionInfoVersion',numeric),('OutputBaseFilename','Onda-'+version+'-Setup-Windows-x64')]:
        text,count=re.subn(r'^'+key+r'=.*$',lambda _:key+'='+value,text,flags=re.M)
        if count!=1:raise ValueError('Missing installer version: '+key)
    installer.write_text(text,encoding='utf-8')
    return version


if __name__=='__main__':
    print(sync_version())
