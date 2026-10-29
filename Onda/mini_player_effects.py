"""Small, bounded audio envelope for the optional desktop visual effects."""
import math
import sys
from array import array

def pcm_envelope(pcm,rate=44100):
    samples=array('h');samples.frombytes(pcm[:len(pcm)//2*2])
    if sys.byteorder!='little':samples.byteswap()
    window=max(2,round(rate*0.08)*2)
    levels=[]
    for start in range(0,len(samples),window):
        end=min(len(samples),start+window);stride=max(1,(end-start)//128)
        values=samples[start:end:stride]
        rms=math.sqrt(sum(float(value)*value for value in values)/max(1,len(values)))/32768
        levels.append(min(1.,rms))
    return levels
