"""Prepare the reviewed local ONDA 1.1.3 artifacts; does not commit, tag or publish."""
from pathlib import Path
import hashlib,json,shutil,subprocess,zipfile,re
VERSION='1.1.3'
repo=Path(__file__).resolve().parent.parent
release=repo/'Release'/VERSION
release.mkdir(exist_ok=True)
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as stream:
  for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
prior=repo/'Release/1.0.0'
prior_manifest=json.loads((prior/'MANIFEST.json').read_text(encoding='utf-8-sig'))
prior_sources=json.loads((prior/'SOURCE_MANIFEST.json').read_text(encoding='utf-8-sig'))
# Native tool recipes and dependency inventory must still match the shipped sources.
for entry in prior_sources['files']:
 name=entry['path']
 if name.startswith('Celular/nativebuild/') or name in ('docs/dependencias.json','Onda/requirements.txt'):
  p=repo/name
  assert p.is_file() and sha(p)==entry['sha256'],f'Dependency/native source changed: {name}'
for kind in ('Fontes-nativos-Android','Fontes-de-terceiros'):
 old=prior/f'Onda-1.0.0-{kind}.zip'
 expected=next(item['sha256'] for item in prior_manifest['artifacts'] if item['filename']==old.name)
 assert sha(old)==expected
 shutil.copy2(old,release/f'Onda-{VERSION}-{kind}.zip')
shutil.copy2(repo/'Instalador/Onda-Setup.exe',release/f'Onda-{VERSION}-Setup-Windows-x64.exe')
shutil.copy2(repo/f'Celular/APK/ONDA-Android-{VERSION}-arm64-v8a.apk',release/f'ONDA-Android-{VERSION}-arm64-v8a.apk')
for source,target in [('RELEASE_NOTES.md','RELEASE_NOTES.md'),('THIRD_PARTY_NOTICES.md','THIRD_PARTY_NOTICES.md'),('Celular/THIRD_PARTY_NOTICES_ANDROID.md','THIRD_PARTY_NOTICES_ANDROID.md'),('PUBLICAR_RELEASE.md','PUBLICAR.md'),('docs/REVISAO-1.1.3.md','VALIDACAO.md')]:
 shutil.copy2(repo/source,release/target)
native=[]
with zipfile.ZipFile(release/f'ONDA-Android-{VERSION}-arm64-v8a.apk') as apk:
 assert apk.testzip() is None
 for line in (repo/'Celular/nativebuild/SHA256SUMS.txt').read_text().splitlines():
  if not line.strip():continue
  expected,name=line.split(None,1);name=name.strip()
  if not name.startswith('arm64-v8a/'):continue
  data=apk.read('lib/'+name);assert hashlib.sha256(data).hexdigest()==expected
  native.append({'file':name,'bytes':len(data),'sha256':expected})
 assert len(native)==3
raw=subprocess.check_output(['git','-C',str(repo),'ls-files','-co','--exclude-standard','-z'])
files={repo/name.decode('utf8') for name in raw.split(b'\0') if name}
files.update(p for p in (repo/'empacotamento').iterdir() if p.is_file() and p.suffix.lower() in {'.py','.ps1','.cs','.iss','.bat','.md','.txt'})
excluded={'.git','.build-tmp','__pycache__','build','.gradle','.kotlin','node_modules','.venv','Portatil','Instalador','Release','native-tools','shared'}
files={p for p in files if p.is_file() and not any(part in excluded for part in p.relative_to(repo).parts)}
for p in files:
 assert p.suffix.lower() not in {'.jks','.keystore','.apk','.exe','.pyc','.p12','.key'},str(p)
 assert p.name.lower() not in {'local.properties','cookies.txt','.env','preferences.xml','onda.sqlite3','credentials.json'},str(p)
commit=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
dirty=bool(subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--untracked-files=normal'],text=True).strip())
assert not dirty, 'Commit source changes before packaging.'
source_manifest={'version':VERSION,'git_base_commit':commit,'contains_uncommitted_changes':dirty,'files':[{'path':p.relative_to(repo).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(files)]}
(release/'SOURCE_MANIFEST.json').write_text(json.dumps(source_manifest,ensure_ascii=False,indent=2),encoding='utf8')
with zipfile.ZipFile(release/f'Onda-{VERSION}-Fontes.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in sorted(files):z.write(p,f'Onda-{VERSION}/'+p.relative_to(repo).as_posix())
 z.write(release/'SOURCE_MANIFEST.json',f'Onda-{VERSION}/SOURCE_MANIFEST.json')
portable_files=[]
with zipfile.ZipFile(release/f'Onda-{VERSION}-Portable-Windows-x64.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in sorted((repo/'Portatil').rglob('*')):
  if not p.is_file():continue
  rel=p.relative_to(repo/'Portatil')
  if rel.parent==Path('.') and p.suffix=='.zip':continue
  if '__pycache__' in rel.parts or p.suffix=='.pyc' or '.onda-work' in rel.parts:continue
  assert rel.parts[:2]!=('_runtime','ffmpeg')
  assert p.name.lower() not in {'cookies.txt','preferences.json','queue.json','onda.sqlite3','.env','language.json','onda-release.jks'}
  z.write(p,f'Onda-{VERSION}/'+rel.as_posix());portable_files.append(rel.as_posix())
for p in release.glob('*.zip'):
 with zipfile.ZipFile(p) as z:assert z.testzip() is None,p
for p in (repo/'Onda').glob('*.py'):
 if not p.name.startswith('test_'):assert p.read_bytes()==(repo/'Portatil/Onda'/p.name).read_bytes(),p
report=json.loads((repo/'diagnosticos/resultados/release-1.1.3-validation.json').read_text())
manifest={'prepared_on':'2026-10-15','status':'prepared-local-patch-not-published','version':VERSION,'git_base_commit':commit,'contains_uncommitted_preparation':dirty,'source_manifest':'SOURCE_MANIFEST.json','windows':{'platform':'Windows 10/11 x64','file_version':'1.1.3.0','authenticode_signed':False,'ffmpeg_bundled':False,'portable_self_test':True},'android':{'package':'br.com.onda.mobile','version':VERSION,'version_code':21,'min_sdk':26,'target_sdk':35,'abi':'arm64-v8a','debuggable':False,'signed':True,'certificate_sha256':'0edd6f5de88fc24b7a45212b51ba7d428030302459e9ed8d619d7dbc29fb81b3','production_upgrade_from':['1.1.2/code20'],'production_upgrade_test_passed':True,'native_tools':native},'tests':report,'validation':'VALIDACAO.md','artifacts':[{'filename':p.name,'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(release.iterdir()) if p.suffix in ('.zip','.exe','.apk')]}
(release/'MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
checks=[p for p in release.iterdir() if p.is_file() and p.name!='SHA256SUMS.txt']
(release/'SHA256SUMS.txt').write_text(''.join(f'{sha(p)}  {p.name}\n' for p in sorted(checks)),encoding='ascii')
print(json.dumps({'source_files':len(files),'portable_files':len(portable_files),'artifacts':manifest['artifacts']},ensure_ascii=False,indent=2))
