"""Ten peaking biquads, stereo state and settings restricted to Jukebox PCM."""
from array import array
import json
import math
import sys
from pathlib import Path
from functools import lru_cache

FREQUENCIES=(31.25,62.5,125,250,500,1000,2000,4000,8000,16000)

def number(value,default,low,high):
    try:
        result=float(value)
        return max(low,min(high,result)) if math.isfinite(result) else default
    except (ValueError,TypeError,OverflowError):return default

def clean(value=None):
    if isinstance(value,str):
        try:value=json.loads(value)
        except (ValueError,TypeError):value=None
    if not isinstance(value,dict):value={}
    bands=value.get('bands',[])
    if not isinstance(bands,list):bands=[]
    result=[]
    for i,f in enumerate(FREQUENCIES):
        band=bands[i] if i<len(bands) and isinstance(bands[i],dict) else {}
        result.append({'frequency':number(band.get('frequency'),f,20,20000),
                       'gain':number(band.get('gain'),0,-12,12),'q':number(band.get('q'),1.4,.1,10)})
    return {'enabled':value.get('enabled') is True,'preamp':number(value.get('preamp'),-6,-24,0),'bands':result}

@lru_cache(maxsize=1)
def presets():
    rows=json.loads((Path(__file__).parent/'settings_schema/equalizer_presets.json').read_text(encoding='utf-8'))
    return {row['name']:clean({'enabled':True,'preamp':row['preamp'],'bands':[{'gain':gain} for gain in row['gains']]}) for row in rows}

def preset_name(value):
    value=clean(value)
    for name,preset in presets().items():
        if abs(value['preamp']-preset['preamp'])<.01 and all(abs(band[key]-reference[key])<.01 for band,reference in zip(value['bands'],preset['bands']) for key in ('frequency','gain','q')):return name
    return 'Personalizado'

class Equalizer:
    def __init__(self,rate=44100):
        self.rate=rate;self.key=None;self.filters=[];self.states=[];self.gain=1;self.transition=None
    def configure(self,value):
        value=clean(value)
        key=(value['enabled'],value['preamp'],tuple(tuple(b.values()) for b in value['bands']))
        if key==self.key:return
        if self.key is not None:
            old=Equalizer(self.rate);old.filters=self.filters;old.states=[row[:] for row in self.states];old.gain=self.gain
            self.transition=old
        self.key=key;self.gain=10**(value['preamp']/20) if value['enabled'] else 1
        filters=[]
        for band in value['bands']:
            if not value['enabled'] or band['gain']==0:continue
            a=10**(band['gain']/40);w=2*math.pi*min(band['frequency'],self.rate*.49)/self.rate
            alpha=math.sin(w)/(2*band['q']);cos=math.cos(w);a0=1+alpha/a
            filters.append(((1+alpha*a)/a0,-2*cos/a0,(1-alpha*a)/a0,-2*cos/a0,(1-alpha/a)/a0))
        # Keep histories for unchanged stages; coefficient changes start a fresh cascade.
        if filters!=self.filters:self.states=[[0.,0.,0.,0.] for _ in filters]
        self.filters=filters
    def process(self,pcm):
        if self.transition is None:return self._process(pcm)
        old=self.transition;self.transition=None
        count=min(len(pcm)//4,round(self.rate*.02))
        if not count:return pcm
        previous=array('h');previous.frombytes(old._process(pcm[:count*4]))
        current=array('h');current.frombytes(self._process(pcm))
        if sys.byteorder!='little':previous.byteswap();current.byteswap()
        for i in range(count):
            alpha=(i+1)/count
            for channel in range(2):
                k=i*2+channel;current[k]=round(previous[k]*(1-alpha)+current[k]*alpha)
        if sys.byteorder!='little':current.byteswap()
        return current.tobytes()
    def _process(self,pcm):
        if not self.filters and self.gain==1:return pcm
        data=array('h');data.frombytes(pcm)
        if sys.byteorder!='little':data.byteswap()
        samples=[x*self.gain for x in data]
        for (b0,b1,b2,a1,a2),state in zip(self.filters,self.states):
            l1,l2,r1,r2=state
            for i in range(0,len(samples),2):
                x=samples[i];y=b0*x+l1;l1=b1*x-a1*y+l2;l2=b2*x-a2*y;samples[i]=y
                x=samples[i+1];y=b0*x+r1;r1=b1*x-a1*y+r2;r2=b2*x-a2*y;samples[i+1]=y
            state[:]=l1,l2,r1,r2
        out=array('h',(32767 if x>32767 else -32768 if x<-32768 else round(x) for x in samples))
        if sys.byteorder!='little':out.byteswap()
        return out.tobytes()
