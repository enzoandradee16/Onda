"""Continuous, bounded PCM crossfades shared by Windows and Android."""
from array import array
import sys
from jukebox import Session, RATE, CHANNELS


def mix_pcm(outgoing,incoming,start,total):
    """Complementary stereo ramps: no silent gap and no correlated-signal clipping."""
    a=array('h');a.frombytes(outgoing);b=array('h');b.frombytes(incoming)
    if sys.byteorder!='little':a.byteswap();b.byteswap()
    frames=len(a)//CHANNELS
    for frame in range(frames):
        gain=min(1.,(start+frame+1)/max(1,total))
        for channel in range(CHANNELS):
            k=frame*CHANNELS+channel;a[k]=round(a[k]*(1-gain)+b[k]*gain)
    if sys.byteorder!='little':a.byteswap()
    return a.tobytes()


class _Buffered:
    def __init__(self,cache):
        self.session=Session(cache);self.cache=str(cache);self.part=None;self.offset=0
    def fill(self,args,kwargs):
        if self.part is None or self.offset>=len(self.part['pcm']):
            self.part=self.session.chunk(*args,**kwargs);self.offset=0
        return (len(self.part['pcm'])-self.offset)//4
    def take(self,frames):
        part=dict(self.part);total=len(part['pcm'])//4;start=self.offset//4
        part['pcm']=part['pcm'][self.offset:self.offset+frames*4];self.offset+=frames*4
        part.update(seconds=frames/RATE,phase_start=start/max(1,total),phase_end=(start+frames)/max(1,total),edge_completed=start+frames==total,beat_seconds=total/RATE)
        return part
    def close(self):self.session.close()


class Stream:
    def __init__(self,cache):
        self.current=_Buffered(cache);self.incoming=None;self.fade_frames=0;self.mixed=0;self.announce=False
    @property
    def transitioning(self):return self.incoming is not None
    def switch(self,cache,seconds=2):
        if self.incoming is not None:raise ValueError('Aguarde a transição atual terminar.')
        target=_Buffered(cache)
        self.fade_frames=round(RATE*max(0.,min(10.,float(seconds))));self.mixed=0
        if not self.fade_frames:
            self.current.close();self.current=target
        else:self.incoming=target
        self.announce=True
    def seek(self,index):
        # A seek targets the track currently becoming audible.
        if self.incoming is not None:
            self.current.close();self.current=self.incoming;self.incoming=None
        self.current.session.seek(index);self.current.part=None;self.current.offset=0
    def chunk(self,*args,**kwargs):
        count=self.current.fill(args,kwargs)
        if self.incoming is not None:
            count=min(count,self.incoming.fill(args,kwargs),self.fade_frames-self.mixed,RATE//10)
            old=self.current.take(count);part=self.incoming.take(count)
            part['pcm']=mix_pcm(old['pcm'],part['pcm'],self.mixed,self.fade_frames)
            self.mixed+=count
            if self.mixed>=self.fade_frames:
                self.current.close();self.current=self.incoming;self.incoming=None
        else:part=self.current.take(count)
        if self.announce:
            part['track_changed']=(self.incoming or self.current).cache;self.announce=False
        part['crossfade_active']=self.incoming is not None
        return part
    def close(self):
        self.current.close()
        if self.incoming is not None:self.incoming.close();self.incoming=None
