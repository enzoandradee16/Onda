"""Local audio editing and measured two-pass loudness normalization."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

AUDIO_TYPES={'.mp3','.m4a','.flac','.wav','.ogg','.opus'}
FIELDS={'title':'title','artists':'artist','album':'album','genre':'genre','release_date':'date','track_number':'tracknumber','disc_number':'discnumber'}

def read_audio(source):
    from mutagen import File
    path=Path(source)
    audio=File(path,easy=True)
    if audio is None or path.suffix.lower() not in AUDIO_TYPES:
        raise ValueError('Escolha um arquivo de áudio compatível.')
    from mutagen.id3 import ID3
    if isinstance(audio.tags,ID3):
        tags={'title':'TIT2','artist':'TPE1','album':'TALB','genre':'TCON','date':'TDRC','tracknumber':'TRCK','discnumber':'TPOS'}
        values={tag:list(audio.tags[frame].text) if frame in audio.tags else [] for tag,frame in tags.items()}
    else:values=audio
    record={key: list(values.get(tag,[])) if key=='artists' else next(iter(values.get(tag,[])),'') for key,tag in FIELDS.items()}
    record['title']=record['title'] or path.stem
    record['duration']=getattr(audio.info,'length',0)
    return record

def cover_preview(source):
    """Small PNG preview of embedded front artwork; never changes the audio."""
    import base64, io
    from mutagen import File
    from mutagen.id3 import ID3
    from mutagen.flac import Picture
    from PIL import Image
    try:
        audio=File(source)
        tags=audio.tags or {}
        data=None
        if isinstance(tags,ID3):
            pictures=tags.getall('APIC')
            picture=next((p for p in pictures if p.type==3),next(iter(pictures),None))
            data=picture.data if picture else None
        elif getattr(audio,'pictures',None):
            picture=next((p for p in audio.pictures if p.type==3),audio.pictures[0]);data=picture.data
        elif tags.get('covr'):data=bytes(tags['covr'][0])
        elif tags.get('metadata_block_picture'):
            pictures=[Picture(base64.b64decode(value)) for value in tags['metadata_block_picture']]
            picture=next((p for p in pictures if p.type==3),pictures[0]);data=picture.data
        if not data:return ''
        with Image.open(io.BytesIO(data)) as image:
            image.thumbnail((240,240))
            output=io.BytesIO();image.convert('RGB').save(output,format='PNG')
            return base64.b64encode(output.getvalue()).decode('ascii')
    except Exception:return ''


def lyrics_text(path):
    source=Path(path)
    if source.suffix.lower() not in ('.txt','.lrc') or source.stat().st_size>1024*1024:
        raise ValueError('Escolha uma letra TXT ou LRC de até 1 MB.')
    data=source.read_bytes()
    if data.startswith((b'\xff\xfe',b'\xfe\xff')):return data.decode('utf-16')
    try:return data.decode('utf-8-sig')
    except UnicodeDecodeError:return data.decode('cp1252')

def write_audio(source, changes, cover_path='', lyrics=''):
    """Change only selected fields; preserve other tags and embedded artwork."""
    from mutagen import File
    from mutagen.id3 import ID3, USLT, APIC
    from mutagen.mp4 import MP4, MP4Cover
    from mutagen.flac import FLAC, Picture
    path=Path(source)
    audio=File(path,easy=True)
    if audio is None:raise ValueError('Áudio não reconhecido.')
    if audio.tags is None:audio.add_tags()
    from mutagen.id3 import TIT2,TPE1,TALB,TCON,TDRC,TRCK,TPOS
    frames={'title':TIT2,'artists':TPE1,'album':TALB,'genre':TCON,'release_date':TDRC,'track_number':TRCK,'disc_number':TPOS}
    for field,value in changes.items():
        if field not in FIELDS:continue
        values=value if isinstance(value,list) else [str(value)]
        values=[str(v).strip() for v in values if str(v).strip()]
        if isinstance(audio.tags,ID3):
            audio.tags.delall(frames[field].__name__)
            if values:audio.tags.add(frames[field](encoding=3,text=values))
        elif values:audio[FIELDS[field]]=values
        elif FIELDS[field] in audio:del audio[FIELDS[field]]
    audio.save()
    native=File(path)
    if native.tags is None:native.add_tags()
    text=lyrics_text(lyrics) if lyrics else None
    cover=None
    if cover_path:
        from review import local_cover
        cover=local_cover(cover_path)
    if isinstance(native.tags,ID3):
        if text is not None:
            native.tags.delall('USLT');native.tags.add(USLT(encoding=3,lang='por',desc='',text=text))
        if cover:
            native.tags.delall('APIC');native.tags.add(APIC(encoding=3,mime=cover[1],type=3,desc='Cover',data=cover[0]))
    elif isinstance(native,MP4):
        if text is not None:native.tags['\xa9lyr']=[text]
        if cover:native.tags['covr']=[MP4Cover(cover[0],imageformat=MP4Cover.FORMAT_JPEG if cover[1]=='image/jpeg' else MP4Cover.FORMAT_PNG)]
    else:
        if text is not None:native.tags['lyrics']=[text]
        if cover:
            image=Picture();image.data=cover[0];image.mime=cover[1];image.type=3
            if isinstance(native,FLAC):native.clear_pictures();native.add_picture(image)
            else:
                import base64
                native.tags['metadata_block_picture']=[base64.b64encode(image.write()).decode('ascii')]
    native.save()

def normalize_audio(source, config, emit=lambda *args,**kwargs:None, *, preview=False):
    from audio_tools import executable,process_options
    from effects_worker import preserve_tags
    path=Path(source)
    if path.suffix.lower() not in AUDIO_TYPES:return path
    tool=executable('ffmpeg',config.get('ffmpeg',''))
    from performance import thread_args
    prefix=[tool,'-y','-v','info']+thread_args(config)
    if preview:prefix+=['-ss',str(max(0,float(config.get('start',0))))]
    prefix+=['-i',str(path),'-vn','-sn','-dn']+thread_args(config)
    if preview:prefix+=['-t','20']
    emit('stage',message='Medindo o volume da música…')
    result=subprocess.run(prefix+['-af','loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json','-f','null','-'],capture_output=True,timeout=1800,**process_options())
    blocks=re.findall(r'\{[^{}]*"input_i"[^{}]*\}',result.stderr.decode(errors='replace'),re.S)
    if result.returncode or not blocks:raise ValueError('Não foi possível medir o volume deste áudio.')
    measured=json.loads(blocks[-1])
    import math
    values=[measured.get(k) for k in ('input_i','input_tp','input_lra','input_thresh','target_offset')]
    if not all(v is not None and math.isfinite(float(v)) for v in values):
        if preview:raise ValueError('O trecho selecionado está em silêncio; escolha outro ponto da música.')
        emit('log',message='Áudio em silêncio: volume preservado.');return path
    filters='loudnorm=I=-16:TP=-1.5:LRA=11:linear=true:measured_I=%s:measured_TP=%s:measured_LRA=%s:measured_thresh=%s:offset=%s'%tuple(values)
    output=path.with_name(path.stem+('.volume-preview' if preview else '.normalizing')+path.suffix)
    codecs={'.mp3':['-c:a','libmp3lame','-b:a','320k'],'.m4a':['-c:a','aac','-b:a','256k'],'.flac':['-c:a','flac'],'.wav':['-c:a','pcm_s16le'],'.ogg':['-c:a','libvorbis','-q:a','5'],'.opus':['-c:a','libopus','-b:a','192k']}
    suffix=path.suffix.lower()
    if suffix in ('.mp3','.m4a'):
        allowed=(96,128,192,256,320) if suffix=='.mp3' else (96,128,192,256)
        quality=str(config.get('audio_quality','')).split(' ')[0]
        if quality.isdigit() and int(quality) in allowed:bitrate=int(quality)
        else:
            from mutagen import File
            original=File(path)
            bitrate=min(allowed,key=lambda value:abs(value-getattr(original.info,'bitrate',allowed[-1]*1000)/1000))
        codecs[suffix]=['-c:a','libmp3lame' if suffix=='.mp3' else 'aac','-b:a',f'{bitrate}k']
    emit('stage',message='Normalizando volume para −16 LUFS…')
    completed=False
    try:
        result=subprocess.run(prefix+['-af',filters+',aresample=48000,asetnsamples=n=4096:p=0','-ar','48000','-map_metadata','0',*codecs[path.suffix.lower()],str(output)],capture_output=True,timeout=1800,**process_options())
        if result.returncode:raise ValueError('Não foi possível normalizar este áudio.')
        preserve_tags(path,output,None)
        completed=True
        if preview:return output
        os.replace(output,path)
        return path
    finally:
        if not preview or not completed:output.unlink(missing_ok=True)

def edit_copy(config, emit=lambda *args,**kwargs:None):
    from file_output import publish
    source=Path(config['source']).resolve()
    read_audio(source)
    overwrite=bool(config.get('overwrite_original'))
    original_stat=source.stat()
    folder=(source.parent if overwrite else Path(config.get('folder') or source.parent).resolve());folder.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.onda-edit-',dir=folder) as directory:
        from file_output import component
        target=Path(directory)/(component(config.get('output_name') or source.stem)+' - Editada'+source.suffix)
        shutil.copyfile(source,target)
        if config.get('normalize_volume'):normalize_audio(target,config,emit)
        if config.get('edit_metadata'):write_audio(target,config.get('changes',{}),config.get('cover_path',''),config.get('lyrics_path',''))
        elif config.get('lyrics_path'):write_audio(target,{},lyrics=config['lyrics_path'])
        if overwrite:
            current=source.stat()
            if (current.st_mtime_ns,current.st_size)!=(original_stat.st_mtime_ns,original_stat.st_size):
                raise ValueError('O arquivo original mudou durante a edição. Abra-o novamente antes de salvar.')
            shutil.copymode(source,target)
            os.replace(target,source)
            final=str(source)
        else:
            final,_=publish(target,folder,'keep',None)
    if config.get('lyrics_path') and Path(config['lyrics_path']).suffix.lower()=='.lrc':
        Path(final).with_suffix('.lrc').write_text(lyrics_text(config['lyrics_path']),encoding='utf-8')
    return {'path':final,'mode':source.suffix.lstrip('.'),'size':Path(final).stat().st_size,'overwritten':overwrite}
