"""Device-only parity and audible DSP checks for selectable band counts."""

import json
import math
from array import array


def verify(value, count):
    from jukebox_equalizer import resize, Equalizer

    settings = resize(json.loads(value), count)
    audible = resize({'enabled': True, 'preamp': 0}, count)
    audible['bands'][-1]['gain'] = -6
    pcm = array('h')
    for i in range(8820):
        sample = round(1000 * math.sin(2 * math.pi * 16000 * i / 44100))
        pcm.extend((sample, sample))
    eq = Equalizer()
    eq.configure(audible)
    result = array('h', eq.process(pcm.tobytes()))
    gain = math.sqrt(
        sum(x * x for x in result[-8000:]) / sum(x * x for x in pcm[-8000:])
    )
    return json.dumps({'settings': settings, 'gain': gain})
