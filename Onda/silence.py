"""Cancelable silence analysis; automatic trimming affects only the file edges."""
import json,re,subprocess,tempfile,time
from pathlib import Path
from audio_tools import executable,process_options

def fingerprint(source):
    source=Path(source).resolve();info=source.stat()
    return {'source':str(source),'size':info.st_size,'mtime_ns':info.st_mtime_ns}

def bounds(log,duration):
    intervals=[];start=None
    for kind,value in re.findall(r'silence_(start|end):\s*(-?\d+(?:\.\d+)?)',log):
        value=max(0.,min(duration,float(value)))
        if kind=='start':start=value
        elif start is not None:intervals.append((start,max(start,value)));start=None
    if start is not None:intervals.append((start,duration))
    leading=intervals[0][1] if intervals and intervals[0][0]<=.02 else 0.
    trailing=duration-intervals[-1][0] if intervals and duration-intervals[-1][1]<=.05 else 0.
    silent=leading+trailing>=duration-.02
    return {'duration':duration,'leading':leading,'trailing':trailing,'start':leading if not silent else 0.,'end':duration-trailing if not silent else duration,'silent':silent,'intervals':[{'start':a,'end':b} for a,b in intervals]}

def detect(source,folder='',cancelled=lambda:False):
    if cancelled():raise InterruptedError('Detecção cancelada.')
    stamp=fingerprint(source)
    probe=subprocess.run([executable('ffprobe',folder),'-v','error','-show_entries','format=duration:stream=codec_type','-of','json',stamp['source']],capture_output=True,text=True,timeout=30,**process_options())
    if probe.returncode:raise ValueError('Não foi possível ler o arquivo para detectar silêncio.')
    info=json.loads(probe.stdout);duration=float(info.get('format',{}).get('duration') or 0)
    if duration<=0 or not any(stream.get('codec_type')=='audio' for stream in info.get('streams',[])):raise ValueError('O arquivo não contém áudio com duração válida.')
    process=None
    try:
        with tempfile.TemporaryFile() as errors:
            process=subprocess.Popen([executable('ffmpeg',folder),'-hide_banner','-nostdin','-i',stamp['source'],'-map','0:a:0','-vn','-af','silencedetect=noise=-45dB:d=0.3','-f','null','-'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=errors,**process_options())
            while process.poll() is None:
                if cancelled():raise InterruptedError('Detecção cancelada.')
                time.sleep(.05)
            if cancelled():raise InterruptedError('Detecção cancelada.')
            errors.seek(0);log=errors.read().decode('utf-8',errors='replace')
            if process.returncode:raise ValueError('Não foi possível analisar o áudio.')
            if fingerprint(source)!=stamp:raise ValueError('O arquivo mudou durante a análise. Tente novamente.')
            return dict(stamp,**bounds(log,duration))
    finally:
        if process and process.poll() is None:process.kill();process.wait()

def cached(source,rows):
    stamp=fingerprint(source)
    return next((row for row in rows if all(row.get(key)==value for key,value in stamp.items())),None)
