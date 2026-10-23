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
    return re.sub(r'<\d{1,3}:[0-5]\d(?:[.:]\d{1,3})?>','',rows[index][1]) if index>=0 else ''


def karaoke_at(rows,seconds):
    import html
    index=bisect.bisect_right(rows,seconds,key=lambda row:row[0])-1
    raw=rows[index][1] if index>=0 else ''
    stamps=list(re.finditer(r'<(\d{1,3}):([0-5]\d)(?:[.:](\d{1,3}))?>',raw))
    if not stamps:return html.escape(raw)
    parts=[html.escape(raw[:stamps[0].start()])]
    for index,stamp in enumerate(stamps):
        fraction=stamp[3] or ''
        at=int(stamp[1])*60+int(stamp[2])+(int(fraction)/10**len(fraction) if fraction else 0)
        word=html.escape(raw[stamp.end():stamps[index+1].start() if index+1<len(stamps) else len(raw)])
        parts.append('<b>'+word+'</b>' if seconds>=at else word)
    return ''.join(parts)
