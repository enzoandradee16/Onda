"""Local beat graph and continuous PCM renderer shared by desktop and Android.

An independent implementation, not the Eternal Jukebox algorithm or service.
"""
from array import array
from collections import Counter
from pathlib import Path
import cmath, hashlib, json, math, os, random, subprocess, threading, time, uuid, wave

RATE, CHANNELS, VERSION = 44100, 2, 1
MAX_SECONDS = 900
_active=Counter()
_active_lock=threading.Lock()

class Cancelled(ValueError):pass

def check(cancelled):
    if cancelled():raise Cancelled('Operação cancelada.')

def _run(command,cancelled):
    from audio_tools import process_options
    with subprocess.Popen(command,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,**process_options()) as process:
        # FFmpeg errors are bounded by -loglevel error; drain concurrently for malformed inputs.
        def drain():
            while process.stderr.read(4096):pass
        reader=threading.Thread(target=drain,daemon=True);reader.start()
        try:
            deadline=time.monotonic()+180
            while process.poll() is None:
                check(cancelled)
                if time.monotonic()>deadline:raise ValueError('A análise demorou demais. Escolha uma faixa menor.')
                time.sleep(.08)
            reader.join(2)
            if process.returncode:raise ValueError('Não foi possível preparar o áudio. Confira o arquivo e o FFmpeg.')
        finally:
            if process.poll() is None:process.kill();process.wait()

def _fft_setup(size):
    bits=size.bit_length()-1
    order=[int(f'{n:0{bits}b}'[::-1],2) for n in range(size)]
    stages=[];width=2
    while width<=size:
        stages.append((width,[cmath.exp(-2j*math.pi*k/width) for k in range(width//2)]));width*=2
    return order,stages

_FFT=_fft_setup(512)
_WINDOW=[.5-.5*math.cos(2*math.pi*i/511) for i in range(512)]
_BINS=[]
for k in range(1,257):
    hz=k*8000/512
    pitch=round(69+12*math.log2(hz/440))%12
    _BINS.append((k,pitch,min(7,int(math.log2(max(1,hz/40))))))

def _features(samples):
    order,stages=_FFT
    values=[complex(samples[i]*_WINDOW[i]) for i in order]
    for width,weights in stages:
        half=width//2
        for start in range(0,512,width):
            for k,w in enumerate(weights):
                a,b=values[start+k],values[start+k+half]*w
                values[start+k],values[start+k+half]=a+b,a-b
    chroma=[0.0]*12;bands=[0.0]*8
    for k,pitch,band in _BINS:
        power=abs(values[k]);bands[band]+=power
        if 80<=k*8000/512<=3500:chroma[pitch]+=power
    def norm(vector):
        length=math.sqrt(sum(v*v for v in vector)) or 1
        return [v/length for v in vector]
    energy=math.sqrt(sum(v*v for v in samples)/512)/32768
    return norm(chroma)+norm(bands),energy

def analyse_wave(path,cancelled=lambda:False,progress=lambda _:None):
    """Bounded, low-rate spectral analysis; silence never creates arbitrary jumps."""
    features=[];energies=[]
    with wave.open(str(path),'rb') as sound:
        if sound.getframerate()!=8000 or sound.getnchannels()!=1:raise ValueError('Áudio de análise inválido.')
        count=sound.getnframes();duration=count/8000
        if not 3<=duration<=MAX_SECONDS+.1:raise ValueError('Use uma música entre 3 segundos e 15 minutos.')
        for offset in range(0,max(0,count-512),256):
            if offset%16384==0:check(cancelled);progress(min(85,int(offset/max(1,count)*85)))
            sound.setpos(offset);data=array('h',sound.readframes(512))
            if os.sys.byteorder!='little':data.byteswap()
            if len(data)!=512:break
            vector,energy=_features(data);features.append(vector);energies.append(energy)
    if len(features)<10:raise ValueError('A faixa é curta demais para analisar.')
    onset=[max(0,energies[i]-energies[i-1]) for i in range(1,len(energies))]
    frame=.032
    scores={lag:sum(onset[i]*onset[i-lag] for i in range(lag,len(onset)))/max(1,len(onset)-lag) for lag in range(10,28)}
    lag=max(scores,key=scores.get);period=lag*frame
    power=sum(v*v for v in onset)/max(1,len(onset))
    confidence=scores[lag]/power if power>1e-10 else 0
    phase=max(range(lag),key=lambda p:sum(onset[i] for i in range(p,len(onset),lag)))
    beats=[0.0];position=float(phase);previous=None;step=float(lag)
    while position<len(onset):
        center=round(position)
        near=range(max(0,center-2),min(len(onset),center+3))
        if not near:break
        peak=max(near,key=onset.__getitem__)
        if onset[peak]<.0005:peak=min(len(onset)-1,center)
        stamp=peak*frame
        if stamp-beats[-1]>=period*.55 and duration-stamp>=period*.4:
            beats.append(round(stamp,4))
            if previous is not None:
                interval=peak-previous
                if lag*.8<=interval<=lag*1.2:step=.9*step+.1*interval
            previous=peak
        position=peak+step
    if duration-beats[-1]<.08:beats.pop()
    beats.append(round(duration,4))
    descriptors=[];levels=[]
    for start,end in zip(beats,beats[1:]):
        a=min(len(features)-1,int(start/frame));b=max(a+1,min(len(features),int(end/frame)))
        descriptors.append([sum(row[k] for row in features[a:b])/(b-a) for k in range(20)])
        levels.append(sum(energies[a:b])/(b-a))
    n=len(descriptors);neighbors=[[] for _ in range(n)]
    buckets={}
    for i,vector in enumerate(descriptors):buckets.setdefault((i%4,max(range(12),key=vector.__getitem__)),[]).append(i)
    for i in range(n):
        if i%32==0:check(cancelled);progress(85+int(i/max(1,n)*14))
        if confidence<.22:continue
        following=(i+1)%n;anchor=descriptors[following];pitch=max(range(12),key=anchor.__getitem__)
        candidates=buckets.get((following%4,pitch),[])
        step=max(1,len(candidates)//160);ranked=[]
        for j in candidates[::step]:
            if abs(j-following)<12 or levels[j]<.004 or levels[following]<.004:continue
            lengths=(beats[j+1]-beats[j],beats[following+1]-beats[following])
            if min(lengths)/max(lengths)<.82:continue
            ratio=min(levels[j],levels[following])/max(levels[j],levels[following])
            if ratio<.55:continue
            a,b=anchor,descriptors[j]
            chroma=sum(a[k]*b[k] for k in range(12))/(math.sqrt(sum(v*v for v in a[:12])*sum(v*v for v in b[:12])) or 1)
            timbre=sum(a[k]*b[k] for k in range(12,20))/(math.sqrt(sum(v*v for v in a[12:])*sum(v*v for v in b[12:])) or 1)
            if chroma>=.94 and timbre>=.94:ranked.append((.65*chroma+.35*timbre,j))
        neighbors[i]=[j for _,j in sorted(ranked,reverse=True)[:5]]
    return {'version':VERSION,'duration':duration,'bpm':round(60/period,1),'beat_confidence':round(confidence,3),'beats':beats,'neighbors':neighbors,'links':sum(map(len,neighbors))}

def cache_root():
    from cache_cleanup import root_path
    return root_path()/'jukebox'

def prepare(source,folder='',cancelled=lambda:False,progress=lambda _:None):
    from audio_tools import executable
    source=Path(source).resolve()
    if not source.is_file():raise ValueError('Escolha um arquivo de áudio válido.')
    digest=hashlib.sha256(str(VERSION).encode())
    with source.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):check(cancelled);digest.update(block)
    base=cache_root()/digest.hexdigest();base.mkdir(parents=True,exist_ok=True)
    pcm=base/'audio.wav';graph=base/'analysis.json'
    with _active_lock:_active[str(base)]+=1
    try:
        if pcm.is_file() and graph.is_file():
            try:
                model=json.loads(graph.read_text());validate_model(model)
                with wave.open(str(pcm),'rb') as sound:
                    if sound.getframerate()!=RATE or sound.getnchannels()!=CHANNELS or sound.getsampwidth()!=2 or abs(sound.getnframes()/RATE-model['duration'])>.1:raise ValueError('Cache de áudio inválido.')
                return dict(model,cache=str(base),title=source.stem,source=str(source),cached=True)
            except (ValueError,KeyError,TypeError,wave.Error,EOFError):
                graph.unlink(missing_ok=True)
        ffprobe=executable('ffprobe',folder)
        result=subprocess.run([ffprobe,'-v','error','-show_entries','format=duration','-of','json',str(source)],capture_output=True,timeout=20,**__import__('audio_tools').process_options())
        duration=float(json.loads(result.stdout)['format']['duration'])
        if not math.isfinite(duration) or not 3<=duration<=MAX_SECONDS:raise ValueError('Use uma música entre 3 segundos e 15 minutos.')
        ffmpeg=executable('ffmpeg',folder);token=uuid.uuid4().hex
        temp=base/(token+'.wav');mono=base/(token+'-mono.wav')
        try:
            progress(0)
            _run([ffmpeg,'-y','-v','error','-i',str(source),'-vn','-t',str(MAX_SECONDS+.1),'-ar',str(RATE),'-ac','2','-c:a','pcm_s16le',str(temp)],cancelled)
            _run([ffmpeg,'-y','-v','error','-i',str(temp),'-ar','8000','-ac','1',str(mono)],cancelled)
            model=analyse_wave(mono,cancelled,progress);check(cancelled)
            # PCM precedes the atomic graph commit: incomplete jobs never become reusable caches.
            os.replace(temp,pcm)
            staging=base/(token+'.json');staging.write_text(json.dumps(model),encoding='utf-8');os.replace(staging,graph)
            return dict(model,cache=str(base),title=source.stem,source=str(source),cached=False)
        finally:temp.unlink(missing_ok=True);mono.unlink(missing_ok=True)
    finally:
        with _active_lock:
            _active[str(base)]-=1
            if not _active[str(base)]:_active.pop(str(base),None)

def validate_model(model):
    beats=model['beats'];n=len(beats)-1
    if model.get('version')!=VERSION or not 2<=n<=4000 or len(model['neighbors'])!=n:raise ValueError('Análise inválida.')
    if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in beats) or beats[0]!=0 or beats[-1]>MAX_SECONDS+.1 or any(not 0<b-a<=2 for a,b in zip(beats,beats[1:])):raise ValueError('Análise inválida.')
    if any(not isinstance(row,list) or len(row)>5 for row in model['neighbors']):raise ValueError('Análise inválida.')
    if any(type(j)!=int or not 0<=j<n for row in model['neighbors'] for j in row):raise ValueError('Análise inválida.')

class Session:
    def __init__(self,cache,seed=None):
        self.base=Path(cache).resolve()
        if self.base.parent!=cache_root().resolve():raise ValueError('Cache inválido.')
        self.model=json.loads((self.base/'analysis.json').read_text());validate_model(self.model)
        self.sound=wave.open(str(self.base/'audio.wav'),'rb')
        self.index=0;self.since_jump=0;self.jumps=0;self.random=random.Random(seed);self.closed=False;self.fade_in=0
        with _active_lock:_active[str(self.base)]+=1
    def _read(self,start,count):
        start=max(0,min(start,self.sound.getnframes()));self.sound.setpos(start)
        return self.sound.readframes(max(0,min(count,self.sound.getnframes()-start)))
    def seek(self,index):
        if self.closed:raise ValueError('Reprodução encerrada.')
        if type(index)!=int or not 0<=index<len(self.model['neighbors']):raise ValueError('Trecho inválido.')
        self.index=index;self.since_jump=0;self.fade_in=round(RATE*.008)

    def chunk(self,variation=45,smooth=35,volume=80,normal=False):
        if self.closed:raise ValueError('Reprodução encerrada.')
        variation=max(0,min(100,float(variation)));smooth=max(0,min(100,float(smooth)));volume=max(0,min(100,float(volume)))
        i=self.index;beats=self.model['beats'];n=len(beats)-1
        next_index=(i+1)%n
        options=self.model['neighbors'][i]
        if not normal and options and self.since_jump>=4 and self.random.random()<variation/100*.35:next_index=self.random.choice(options)
        jumped=next_index!=(i+1)%n
        start,end=round(beats[i]*RATE),round(beats[i+1]*RATE)
        data=array('h');data.frombytes(self._read(start,end-start))
        if os.sys.byteorder!='little':data.byteswap()
        if self.fade_in:
            count=min(self.fade_in,len(data)//CHANNELS)
            for frame in range(count):
                for channel in range(CHANNELS):
                    k=frame*CHANNELS+channel;data[k]=round(data[k]*(frame+1)/count)
            self.fade_in=0
        if next_index==0 and smooth:
            count=min(int(RATE*.08*smooth/100),len(data)//CHANNELS)
            for frame in range(count):
                for channel in range(CHANNELS):
                    k=len(data)-count*CHANNELS+frame*CHANNELS+channel;data[k]=round(data[k]*(1-(frame+1)/count))
            self.fade_in=count
        elif jumped and smooth:
            fade=min(int(RATE*.08*smooth/100),len(data)//CHANNELS,round(beats[next_index]*RATE))
            if fade:
                incoming=array('h');incoming.frombytes(self._read(round(beats[next_index]*RATE)-fade,fade))
                if os.sys.byteorder!='little':incoming.byteswap()
                offset=len(data)-fade*CHANNELS
                for frame in range(fade):
                    alpha=(frame+1)/fade
                    for channel in range(CHANNELS):
                        k=frame*CHANNELS+channel
                        data[offset+k]=round(data[offset+k]*(1-alpha)+incoming[k]*alpha)
        gain=volume/100
        if gain!=1:data=array('h',(round(sample*gain) for sample in data))
        self.index=next_index;self.since_jump=0 if jumped else self.since_jump+1;self.jumps+=int(jumped)
        if os.sys.byteorder!='little':data.byteswap()
        return {'pcm':data.tobytes(),'index':i,'next':next_index,'jumped':jumped,'jumps':self.jumps,'seconds':len(data)/(RATE*CHANNELS)}
    def close(self):
        if not self.closed:
            self.closed=True;self.sound.close()
            with _active_lock:
                _active[str(self.base)]-=1
                if not _active[str(self.base)]:_active.pop(str(self.base),None)

def cache_in_use(path):
    with _active_lock:return any(str(Path(path).resolve()).startswith(base+os.sep) for base in _active)

class SearchLog:
    def __init__(self,config,cancelled):
        self.cancelled=cancelled
        self.youtube_cookiejar=None
        self.youtube_options={key:config[key] for key in ('cookiefile','http_headers','ffmpeg_location') if config.get(key)}
    def debug(self,message):check(self.cancelled)
    def warning(self,message):check(self.cancelled)
    def error(self,message):check(self.cancelled)

def fetch_audio(config,record=None,cancelled=lambda:False,progress=lambda _:None):
    """Reuse catalog matching and the existing bounded download recovery; cache only."""
    from engine import build_options,download_with_recovery,validate_url
    from metadata import is_streaming_link
    import tempfile
    url=(record or {}).get('source_url') or config.get('url','')
    root=cache_root();root.mkdir(parents=True,exist_ok=True)
    options=build_options(dict(config,mode='original',folder=str(root),playlist=False,playlist_limit=1))
    if config.get('youtube_cookies_file'):options['cookiefile']=config['youtube_cookies_file']
    if config.get('youtube_user_agent'):options['http_headers']={'User-Agent':config['youtube_user_agent']}
    logger=SearchLog(options,cancelled)
    if record is not None or is_streaming_link(url):
        if record is None:
            from metadata import MetadataClient
            client=MetadataClient(config.get('spotify_client_id',''),config.get('spotify_client_secret',''));client.cancelled=cancelled
            try:record=client.resolve(url,automatic=True)
            finally:client.close()
        from matching import resolve_youtube
        url=resolve_youtube(record,logger,lambda *_:None,automatic=True)['source_url']
    url=validate_url(url);saved=[]
    from yt_dlp.postprocessor.common import PostProcessor
    class Capture(PostProcessor):
        def run(self,info):
            path=info.get('filepath') or info.get('_filename')
            if path:saved.append(path)
            return [],info
    def hook(data):
        check(cancelled)
        total=data.get('total_bytes') or data.get('total_bytes_estimate') or 0
        progress(int(data.get('downloaded_bytes',0)/total*100) if total else 0)
    # Never write a cache download to the user's music folders, history or queue.
    with tempfile.TemporaryDirectory(prefix='jukebox-download-',dir=root) as temporary:
        options.update(outtmpl=str(Path(temporary)/'audio.%(ext)s'),noplaylist=True,playlistend=1,max_filesize=128*1024*1024,logger=logger,progress_hooks=[hook],match_filter=lambda info,**_: 'Use uma faixa de até 15 minutos.' if info.get('is_live') or (info.get('duration') or 0)>MAX_SECONDS else None)
        options.pop('postprocessors',None)
        def configure(ydl):
            if logger.youtube_cookiejar is not None:
                ydl.cookiejar=logger.youtube_cookiejar
            ydl.add_post_processor(Capture(ydl),when='after_move')
        result=download_with_recovery(url,options,configure,saved)
        check(cancelled)
        if result or len(saved)!=1:raise ValueError('Não foi possível obter uma única faixa de áudio.')
        model=prepare(saved[0],config.get('ffmpeg',''),cancelled,progress)
    model['source']=str(Path(model['cache'])/'audio.wav')
    if record:
        model['title']=' — '.join(filter(None,[', '.join(record.get('artists',[])),record.get('title')]))
        model['cover_url']=record.get('cover_url') or '';model['album']=record.get('album') or ''
    return model
