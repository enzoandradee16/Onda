"""Local video conversion shared by desktop and Android; originals are read-only."""
import json
import math
import os
from pathlib import Path
import queue
import subprocess
import tempfile
import threading
from audio_tools import executable, process_options

FORMATS=('MP4','MKV','MOV')
AUDIO_FORMATS=('MP3','M4A','AAC')
OUTPUT_FORMATS=FORMATS+AUDIO_FORMATS
QUALITIES=('Equilibrada','Alta qualidade','Arquivo menor')
RESOLUTIONS=('Original','1080p','720p','480p')
VIDEO_BITRATES=('Automático','1000k','2500k','5000k','8000k','12000k','20000k')
AUDIO_BITRATES=('96k','128k','192k','256k','320k')
FRAME_RATES=('Original','24','25','30','50','60')
AUDIO_MODES=('Manter áudio','Sem áudio')
AUDIO_INPUT_EXTENSIONS={'.mp3','.m4a','.aac','.flac','.wav','.ogg','.opus'}
VIDEO_EXTENSIONS={'.mp4','.mkv','.mov','.avi','.webm','.m4v','.mpeg','.mpg','.ts','.mts','.m2ts','.3gp','.flv','.wmv'}

class ConversionCancelled(Exception):
    pass

def probe_video(source, folder='',audio_only=False):
    source=Path(source).resolve()
    if not source.is_file() or source.suffix.lower() not in (VIDEO_EXTENSIONS | AUDIO_INPUT_EXTENSIONS if audio_only else VIDEO_EXTENSIONS):
        raise ValueError('Escolha um arquivo de vídeo local compatível.')
    result=subprocess.run([executable('ffprobe',folder),'-v','error','-show_entries',
        'format=duration:stream=index,codec_type,width,height:stream_disposition=attached_pic',
        '-of','json',str(source)],capture_output=True,text=True,timeout=30,**process_options())
    if result.returncode:raise ValueError('Não foi possível ler este vídeo. O arquivo pode estar incompleto ou protegido.')
    info=json.loads(result.stdout)
    video=next((s for s in info.get('streams',[]) if s.get('codec_type')=='video' and not s.get('disposition',{}).get('attached_pic')),None)
    duration=float(info.get('format',{}).get('duration') or 0)
    audio=next((s for s in info.get('streams',[]) if s.get('codec_type')=='audio'),None)
    if (audio is None if audio_only else video is None) or not math.isfinite(duration) or duration<=0:
        raise ValueError('O vídeo selecionado não contém áudio.' if audio_only and audio is None else 'O arquivo precisa conter vídeo e uma duração válida.')
    return dict(duration=duration,width=int(video['width']) if video and not audio_only else 0,height=int(video['height']) if video and not audio_only else 0,video_index=int(video['index']) if video else -1,has_audio=audio is not None)

def convert_video(config,emit=lambda *args,**kwargs:None,cancelled=lambda:False):
    source=Path(config['source']).resolve();output=Path(config['output']).resolve()
    mode=config.get('video_format','MP4');quality=config.get('video_quality','Equilibrada');resolution=config.get('video_resolution','Original')
    if mode not in OUTPUT_FORMATS or quality not in QUALITIES or resolution not in RESOLUTIONS:
        raise ValueError('Formato, qualidade ou resolução de vídeo inválidos.')
    bitrate=config.get('video_bitrate','Automático');audio_bitrate=config.get('audio_bitrate','192k');fps=config.get('video_fps','Original');audio=config.get('video_audio','Manter áudio')
    if bitrate not in VIDEO_BITRATES or audio_bitrate not in AUDIO_BITRATES or fps not in FRAME_RATES or audio not in AUDIO_MODES:
        raise ValueError('Opções de vídeo ou áudio inválidas.')
    if source==output or output.exists():raise ValueError('Escolha um arquivo de saída novo, diferente do original.')
    if output.suffix.lower()!='.'+mode.lower():raise ValueError('A extensão da saída deve corresponder ao formato escolhido.')
    def check():
        if cancelled():raise ConversionCancelled('Conversão cancelada.')
    check();info=probe_video(source,config.get('ffmpeg',''),audio_only=mode in AUDIO_FORMATS);check()
    if mode in AUDIO_FORMATS and not info['has_audio']:raise ValueError('O vídeo selecionado não contém áudio.')
    trim=None;expected_duration=info['duration']
    if config.get('trim_silence'):
        from silence import cached,detect
        emit('stage',message='Detectando silêncio nas extremidades…')
        try:trim=cached(source,config.get('silence_results',[])) or detect(source,config.get('ffmpeg',''),cancelled)
        except InterruptedError:raise ConversionCancelled('Conversão cancelada.')
        if trim.get('error'):raise ValueError(trim['error'])
        if trim['silent']:raise ValueError('O arquivo é inteiramente silencioso. Desative o recorte para convertê-lo sem cortes.')
        expected_duration=trim['end']-trim['start'];check()
    output.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.onda-convert-',suffix=output.suffix,dir=output.parent);os.close(fd)
    temporary=Path(name);process=None
    try:
        size={'1080p':(1920,1080),'720p':(1280,720),'480p':(854,480)}.get(resolution)
        scale=(f"scale=w='min(iw,{size[0]})':h='min(ih,{size[1]})':force_original_aspect_ratio=decrease:force_divisible_by=2" if size else 'scale=trunc(iw/2)*2:trunc(ih/2)*2')
        command=[executable('ffmpeg',config.get('ffmpeg','')),'-hide_banner','-loglevel','error','-nostdin','-y','-i',str(source),
            '-map',f"0:{info['video_index']}",'-map','0:a:0?','-map_metadata','0','-map_chapters','0',
            '-vf',scale,'-c:v','libx264','-preset','veryfast','-crf',str({'Equilibrada':23,'Alta qualidade':18,'Arquivo menor':28}[quality]),
            '-pix_fmt','yuv420p','-c:a','aac','-b:a','192k']
        if bitrate!='Automático':
            index=command.index('-crf');del command[index:index+2]
            command+=['-b:v',bitrate]
        command[command.index('-b:a')+1]=audio_bitrate
        if fps!='Original':command+=['-r',fps]
        if audio=='Sem áudio':command+=['-an']
        if mode in ('MP4','MOV'):command+=['-movflags','+faststart']
        if mode in AUDIO_FORMATS:
            command=[executable('ffmpeg',config.get('ffmpeg','')),'-hide_banner','-loglevel','error','-nostdin','-y','-i',str(source),'-map','0:a:0','-vn','-map_metadata','0','-c:a','libmp3lame' if mode=='MP3' else 'aac','-b:a',audio_bitrate]
            if mode=='M4A':command+=['-movflags','+faststart']
        if trim:
            position=command.index('-i');command[position:position]=['-ss',str(trim['start'])]
            command+=['-t',str(expected_duration)]
        from performance import thread_args,priority_flags
        command[1:1]=thread_args(config)
        command+=thread_args(config,default=2 if mode not in AUDIO_FORMATS else None)+['-progress','pipe:1','-nostats',str(temporary)]
        child_options=process_options()
        if os.name=='nt':child_options['creationflags']=child_options.get('creationflags',0)|priority_flags(config)
        emit('stage',message='Convertendo vídeo…')
        with tempfile.TemporaryFile() as errors:
            process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=errors,text=True,stdin=subprocess.DEVNULL,**child_options)
            lines=queue.Queue()
            def read():
                try:
                    for line in process.stdout:lines.put(line)
                finally:lines.put(None)
            reader=threading.Thread(target=read,daemon=True);reader.start()
            while True:
                check()
                try:line=lines.get(timeout=.1)
                except queue.Empty:continue
                if line is None:break
                if line.startswith('out_time_us='):
                    try:percent=min(99,max(0,float(line.split('=',1)[1])/1e6/expected_duration*100))
                    except ValueError:continue
                    emit('progress',percent=percent)
            code=process.wait();reader.join(timeout=2);check()
            if code:
                errors.seek(0);detail=errors.read(2500).decode('utf-8',errors='replace')
                raise ValueError('Falha ao converter o vídeo. '+detail)
        rendered=probe_video(temporary,config.get('ffmpeg',''),audio_only=mode in AUDIO_FORMATS);check()
        if abs(rendered['duration']-expected_duration)>max(.25 if trim else 2,expected_duration*.02):
            raise ValueError('A duração do vídeo convertido não corresponde ao original.')
        # Publish exclusively: a file created during conversion is never replaced.
        if os.name=='nt':os.rename(temporary,output)
        else:os.link(temporary,output);temporary.unlink()
        emit('progress',percent=100)
        return {'path':str(output),'duration':rendered['duration'],'width':rendered['width'],'height':rendered['height']}
    finally:
        if process:
            if process.poll() is None:process.kill()
            process.wait()
            if process.stdout:process.stdout.close()
        temporary.unlink(missing_ok=True)


def convert_batch(config,emit=lambda *args,**kwargs:None,cancelled=lambda:False):
    mode=config.get('video_format','MP3')
    if mode not in OUTPUT_FORMATS:raise ValueError('Formato de conversão inválido.')
    sources=list(dict.fromkeys(config.get('sources',[])))
    if not sources or len(sources)>1000:raise ValueError('Selecione de 1 a 1000 arquivos.')
    folder=Path(config['output_folder']).resolve()
    results=[];failures=[]
    for index,source in enumerate(sources):
        if cancelled():raise ConversionCancelled('Conversão cancelada.')
        path=Path(source)
        import re
        name=re.sub(r'^(?:audio|conversion)-batch-[0-9a-f-]{36}-','',path.stem)
        target=folder/(name+' - convertido.'+mode.lower())
        suffix=2
        while target.exists():
            target=folder/(name+f' - convertido ({suffix}).'+mode.lower());suffix+=1
        emit('stage',message=f'{index+1}/{len(sources)} · {path.name}')
        def progress(kind,**data):
            if kind=='progress':emit(kind,percent=(index+data['percent']/100)/len(sources)*100)
        try:
            result=convert_video(dict(config,source=str(path),output=str(target)),progress,cancelled)
            results.append(result)
            emit('file',path=result['path'],mode=mode,size=target.stat().st_size)
        except ConversionCancelled:raise
        except Exception as error:failures.append({'source':str(path),'error':str(error)})
    return {'results':results,'failures':failures,'message':f"{len(results)}/{len(sources)} · "+'; '.join(row['source']+': '+row['error'] for row in failures)}
