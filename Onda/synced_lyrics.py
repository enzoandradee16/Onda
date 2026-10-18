"""Bounded LRC parsing, shared by desktop and Android playback."""
import bisect
import re
from audio_library import lyrics_text

def parse_lrc(text):
    if len(text)>1024*1024:raise ValueError('Letra muito grande.')
    offset=0
    match=re.search(r'\[offset:([+-]?\d+)\]',text,re.I)
    if match:offset=int(match[1])/1000
    rows=[]
    pattern=r'\[(\d{1,3}):([0-5]\d)(?:[.:](\d{1,3}))?\]'
    for line in text.splitlines():
        stamps=list(re.finditer(pattern,line))
        if not stamps:continue
        words=line[stamps[-1].end():].strip()
        for stamp in stamps:
            fraction=stamp[3] or ''
            time=int(stamp[1])*60+int(stamp[2])+(int(fraction)/10**len(fraction) if fraction else 0)+offset
            rows.append((max(0,time),words))
    rows.sort(key=lambda row:row[0])
    return rows

def read_lrc(path):
    return parse_lrc(lyrics_text(path))

def line_at(rows,seconds):
    index=bisect.bisect_right(rows,seconds,key=lambda row:row[0])-1
    return rows[index][1] if index>=0 else ''
