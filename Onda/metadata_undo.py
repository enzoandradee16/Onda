"""One persistent metadata transaction. Stores tags/artwork, never audio copies."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import tempfile
import threading
import uuid

_lock=threading.RLock()


def base():
    from cache_cleanup import root_path,linked
    folder=root_path()/'metadata-undo'
    folder.mkdir(parents=True,exist_ok=True)
    if linked(folder):raise ValueError('Pasta de histórico inválida.')
    return folder


def digest(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def _copy_audio(source,target):
    try:
        shutil.copy2(source,target)
    except PermissionError:
        # Android may deny copying SELinux extended attributes after the complete
        # audio was copied. Only tolerate that case; never accept a partial copy.
        if not Path(target).is_file() or digest(source)!=digest(target):raise


def available():
    return (base()/'last.json').is_file()


def _write(path,value):
    temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False),encoding='utf8')
    os.replace(temporary,path)


def _read_last():
    path=base()/'last.json'
    try:
        if not path.is_file() or path.stat().st_size>4*1024*1024:return {}
        value=json.loads(path.read_text(encoding='utf8'))
        if not isinstance(value,dict) or not isinstance(value.get('entries'),list):return {}
        uuid.UUID(value['transaction'])
        return value
    except (OSError,ValueError,KeyError,TypeError):return {}


def capture(source,transaction,sidecar=False,overwrite=False):
    from tag_transfer import snapshot,encode
    folder=base()/str(uuid.UUID(transaction));folder.mkdir(exist_ok=True)
    from cache_cleanup import linked
    if linked(folder):raise ValueError('Pasta de histórico inválida.')
    import time
    previous=_read_last().get('transaction')
    for candidate in base().iterdir():
        if candidate.name in (transaction,previous) or not candidate.is_dir() or linked(candidate):continue
        try:uuid.UUID(candidate.name)
        except ValueError:continue
        if candidate.resolve().is_relative_to(base().resolve()) and time.time()-candidate.stat().st_mtime>86400:shutil.rmtree(candidate)
    value=snapshot(source)
    if sidecar:
        import base64
        companion=Path(source).with_suffix('.lrc')
        if overwrite and companion.exists():
            if linked(companion) or companion.stat().st_size>1048576:raise ValueError('A letra externa não pode ser guardada para desfazer. Salve uma cópia ou desmarque a letra.')
            value['_lrc_before']=base64.b64encode(companion.read_bytes()).decode('ascii')
        else:value['_lrc_before']=None
    payload=encode(value)
    if sum(p.stat().st_size for p in folder.glob('*.json'))+len(payload.encode('utf8'))>128*1024*1024:
        raise ValueError('As tags e capas excedem 128 MB. Edite menos arquivos por vez para permitir desfazer.')
    path=folder/(uuid.uuid4().hex+'.json');path.write_text(payload,encoding='utf8')
    return str(path)


def register(snapshot,target,edited,transaction,sha256=None):
    with _lock:
        folder=base();path=Path(snapshot).resolve()
        if not path.is_relative_to(folder.resolve()) or not path.is_file():raise ValueError('Histórico de edição inválido.')
        journal=folder/'last.json'
        old=_read_last()
        value=old if old.get('transaction')==transaction else dict(transaction=transaction,entries=[])
        value['entries'].append(dict(target=str(target),snapshot=str(path),sha256=sha256 or digest(edited)))
        data=json.loads(path.read_text(encoding='utf8'))
        if '_lrc_before' in data:
            companion=Path(target).with_suffix('.lrc')
            data['_lrc_after_sha256']=digest(companion) if companion.is_file() else None
            _write(path,data)
        _write(journal,value)
        if old and old.get('transaction')!=transaction:
            previous=folder/str(uuid.UUID(old['transaction']))
            if previous.resolve().is_relative_to(folder.resolve()) and previous.is_dir() and not previous.is_symlink():shutil.rmtree(previous)


def pending():
    return _read_last().get('entries',[])


def restore_file(source,snapshot,expected):
    """Atomic tag replacement, rejecting files changed since the edit."""
    from mutagen import File
    from tag_transfer import decode,apply,_unpack
    import base64,io
    source=Path(source).resolve()
    if digest(source)!=expected:raise ValueError('O arquivo mudou após a edição. O desfazer foi interrompido para preservar essas alterações.')
    path=Path(snapshot).resolve()
    if not path.is_relative_to(base().resolve()):raise ValueError('Histórico de edição inválido.')
    payload=decode(path.read_text(encoding='utf8'))
    companion=source.with_suffix('.lrc')
    if '_lrc_after_sha256' in payload:
        from cache_cleanup import linked
        if companion.exists() and linked(companion):raise ValueError('A letra externa mudou após a edição.')
        if (digest(companion) if companion.is_file() else None)!=payload['_lrc_after_sha256']:
            raise ValueError('A letra externa mudou após a edição. O desfazer foi interrompido.')
    with tempfile.TemporaryDirectory(prefix='.onda-undo-',dir=source.parent) as folder:
        target=Path(folder)/source.name;_copy_audio(source,target)
        audio=File(target)
        if audio.tags is not None:audio.delete()
        audio=File(target)
        if hasattr(audio,'clear_pictures'):audio.clear_pictures()
        native=payload['native']
        if native['family']=='id3':
            from mutagen.id3 import ID3
            original=ID3(fileobj=io.BytesIO(base64.b64decode(native['data'])))
            if audio.tags is None:audio.add_tags()
            for frame in original.values():audio.tags.add(frame)
            audio.tags.unknown_frames=list(original.unknown_frames)
        else:
            if audio.tags is None:audio.add_tags()
            for key,value in native.get('values',{}).items():audio.tags[key]=_unpack(value)
        audio.save()
        apply(target,payload,{},True,True)
        if digest(source)!=expected:raise ValueError('O arquivo mudou durante o desfazer.')
        backup=Path(folder)/('previous-'+source.name)
        try:os.link(source,backup)
        except OSError:_copy_audio(source,backup)
        os.replace(target,source)
        try:
            if '_lrc_before' in payload:
                if payload['_lrc_before'] is None:companion.unlink(missing_ok=True)
                else:
                    previous=Path(folder)/'previous.lrc';previous.write_bytes(base64.b64decode(payload['_lrc_before'],validate=True));os.replace(previous,companion)
        except Exception:
            os.replace(backup,source)
            raise


def finish(target):
    with _lock:
        journal=base()/'last.json'
        if not journal.exists():return
        value=json.loads(journal.read_text(encoding='utf8'))
        value['entries']=[row for row in value['entries'] if row['target']!=target]
        if value['entries']:_write(journal,value)
        else:
            journal.unlink()
            folder=base()/str(uuid.UUID(value['transaction']))
            if folder.resolve().is_relative_to(base().resolve()) and folder.is_dir() and not folder.is_symlink():shutil.rmtree(folder)


def undo(cancelled=lambda:False):
    results=[]
    for entry in reversed(pending()):
        if cancelled():raise InterruptedError('Operação cancelada.')
        if entry['target'].startswith('content:'):raise ValueError('Restaure este arquivo pelo aplicativo Android.')
        restore_file(entry['target'],entry['snapshot'],entry['sha256']);finish(entry['target']);results.append(entry['target'])
    if not results:raise ValueError('Não há edição de metadados para desfazer.')
    return dict(restored=results,message=f'Metadados anteriores restaurados em {len(results)} arquivo(s).')
