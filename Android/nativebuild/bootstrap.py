"""Fetch locked native sources/toolchains and build ONDA media tools on Windows."""
from pathlib import Path
import argparse, ctypes, hashlib, json, os, shutil, subprocess, tarfile, urllib.request, zipfile

HERE=Path(__file__).resolve().parent

def sha256(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def fetch(entry,folder):
    folder.mkdir(parents=True,exist_ok=True)
    path=folder/entry['filename']
    if not path.exists():
        bundled=HERE/'sources'/entry['filename']
        if bundled.is_file() and sha256(bundled)==entry['sha256']:
            shutil.copy2(bundled,path)
    if not path.exists():
        temporary=path.with_suffix(path.suffix+'.part')
        request=urllib.request.Request(entry['url'],headers={'User-Agent':'ONDA-native-builder'})
        with urllib.request.urlopen(request,timeout=120) as response,temporary.open('wb') as output:
            shutil.copyfileobj(response,output,1024*1024)
        if sha256(temporary)!=entry['sha256']:raise ValueError('SHA-256 incorreto: '+path.name)
        temporary.replace(path)
    if sha256(path)!=entry['sha256']:raise ValueError('SHA-256 incorreto: '+path.name)
    return path

def extract(path,target):
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            for info in z.infolist():
                if not (target/info.filename).resolve().is_relative_to(target.resolve()):raise ValueError('Caminho ZIP inválido')
            z.extractall(target)
    else:
        with tarfile.open(path) as t:t.extractall(target,filter='data')

def short_path(path):
    buffer=ctypes.create_unicode_buffer(32768)
    if not ctypes.windll.kernel32.GetShortPathNameW(str(path),buffer,len(buffer)):
        raise OSError('Não foi possível obter o caminho curto. Use uma pasta sem espaços.')
    return buffer.value

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work',type=Path,required=True,help='Isolated working directory (needs roughly 8 GB)')
    p.add_argument('--abi',choices=('arm64-v8a','x86_64'),default='arm64-v8a')
    p.add_argument('--sources-only',action='store_true')
    p.add_argument('--install-to',type=Path,help='Copy the three verified build outputs into this native-tools directory and refresh the recipe checksum manifest')
    args=p.parse_args();work=args.work.resolve();work.mkdir(parents=True,exist_ok=True)
    for entry in json.loads((HERE/'source-lock.json').read_text(encoding='utf-8')):
        archive=fetch(entry,work/'sources')
        with tarfile.open(archive) as t:root=t.getmembers()[0].name.split('/')[0]
        if not (work/'src'/root).exists():extract(archive,work/'src')
    if args.sources_only:return
    if os.name!='nt':raise SystemExit('Esta receita foi validada no Windows com NDK r28c e MSYS2. Use --sources-only para obter os fontes em outro sistema.')
    for entry in json.loads((HERE/'toolchains.json').read_text(encoding='utf-8')):
        archive=fetch(entry,work/'toolchains')
        marker=work/('android-ndk-r28c/source.properties' if archive.suffix=='.zip' else 'msys64/usr/bin/bash.exe')
        if not marker.exists():extract(archive,work)
    shutil.copy2(HERE/'build-native.sh',work/'build-native.sh')
    base=short_path(work).replace('\\','/');base='/'+base[0].lower()+base[2:]
    bash=work/'msys64/usr/bin/bash.exe'
    subprocess.run([str(bash),'-lc','pacman -Sy --needed --noconfirm make diffutils perl pkgconf nasm mingw-w64-ucrt-x86_64-gcc mingw-w64-ucrt-x86_64-cmake'],check=True)
    subprocess.run([str(bash),'-lc',f'cd "{base}" && bash build-native.sh {args.abi}'],check=True)
    if args.install_to:
        destination=args.install_to.resolve()/args.abi
        destination.mkdir(parents=True,exist_ok=True)
        checksum_file=HERE/'SHA256SUMS.txt'
        lines=checksum_file.read_text(encoding='ascii').splitlines() if checksum_file.exists() else []
        lines=[line for line in lines if not line.split()[-1].startswith(args.abi+'/')]
        for name in ('libffmpeg.so','libffprobe.so','libqjs.so'):
            original=work/'out'/args.abi/name
            shutil.copy2(original,destination/name)
            lines.append(sha256(original)+'  '+args.abi+'/'+name)
        checksum_file.write_text('\n'.join(sorted(lines))+'\n',encoding='ascii')
    print('Ferramentas geradas em',work/'out'/args.abi)
    print('Confira os testes antes de atualizar native-tools e SHA256SUMS.txt.')

if __name__=='__main__':main()
