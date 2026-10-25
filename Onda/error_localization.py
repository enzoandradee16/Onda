"""Localize external diagnostics without changing paths, URLs or error codes."""
from functools import lru_cache
import json
from pathlib import Path
import re

_PROTECTED = re.compile('(["\'])(?:[A-Za-z]:[\\\\/]|/|\\\\\\\\|\\.{1,2}[\\\\/])[^\\n]*?\\1|\\\\\\\\[^\\s<>"\']+|\\.{1,2}[\\\\/][^\\s<>"\']+|https?://[^\\s<>"\']+|(?:[A-Za-z]:[\\\\/]|/)[^\\s<>"\']+|\\b[^\\s<>"\']+\\.(?:mp3|m4a|flac|wav|ogg|opus|apk|exe|json|lrc|txt|mp4|webm)\\b', re.IGNORECASE)

@lru_cache(maxsize=1)
def rules():
    data=json.loads((Path(__file__).parent/'locales/technical_errors.json').read_text(encoding='utf-8'))
    phrases={}
    for row in data['phrases']:
        for phrase in row.values():phrases.setdefault(phrase.casefold(),row)
    expression=re.compile(r'(?<!\w)(?:'+'|'.join(re.escape(s) for s in sorted(phrases,key=len,reverse=True))+r')(?!\w)',re.IGNORECASE)
    return data,phrases,expression

def technical_text(text,language):
    if not isinstance(text,str) or not text:return text
    data,phrases,expression=rules()
    for heading in data["unknown"].values():
        if text.startswith(heading):text=data["unknown"][language]+text[len(heading):];break
    def replace(match):return phrases[match.group().casefold()][language]
    # Work only outside diagnostic values, never on a filename or a URL.
    output=[];start=0
    for match in _PROTECTED.finditer(text):
        output.extend((expression.sub(replace,text[start:match.start()]),match.group()))
        start=match.end()
    output.append(expression.sub(replace,text[start:]))
    return ''.join(output)

def error_text(text,language=None):
    from i18n import tr,normalize_language,_language,catalog
    selected=normalize_language(language or _language)
    raw=str(text)
    translated=technical_text(tr(raw,selected),selected)
    # Known diagnostics may already be in the requested language.
    _,_,expression=rules()
    if translated!=raw or expression.search(raw) or raw in catalog("en") or selected=='pt-BR' and re.search('[ãõçáéíóúâêô]',raw):return translated
    if not raw.strip():return raw
    heading=rules()[0]['unknown'][selected]
    if any(raw.startswith(value) for value in rules()[0]['unknown'].values()):
        return heading+raw[raw.index(':')+1:]
    return heading+'\n'+raw
