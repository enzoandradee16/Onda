"""Shared, conservative edition evidence for catalogs and audio sources."""
import math
import re
from datetime import date


def finite_positive(value):
    return type(value) in (int, float) and math.isfinite(value) and value > 0


def recording_title(record):
    title = record.get('title') or ''
    version = record.get('version') or record.get('title_version') or ''
    return title + (' (' + version + ')' if isinstance(version, str) and version and version.casefold() not in title.casefold() else '')


def date_parts(value):
    match = re.fullmatch(r'(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?(?:T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z)?', str(value or ''))
    if not match:
        return ()
    parts = tuple(int(part) for part in match.groups() if part is not None)
    try:
        date(parts[0], parts[1] if len(parts) > 1 else 1, parts[2] if len(parts) > 2 else 1)
    except ValueError:
        return ()
    return parts


def same_release(left, right):
    a, b = date_parts(left.get('release_date')), date_parts(right.get('release_date'))
    # Partial dates are useful for ranking, never proof of the same release.
    return len(a) == len(b) == 3 and a == b


def edition_details(record):
    from matching import matching_tokens
    title = recording_title(record)
    parts = re.findall(r'\(([^()]*)\)|\[([^\[\]]*)\]', title)
    labels = [' '.join(part for part in group if part) for group in parts]
    suffix=re.split(r'\s[-–—]\s',title)
    if len(suffix)>1 and not re.search(r'[()\[\]]',suffix[-1]):
        labels.append(suffix[-1])
    result = {}
    # Years immediately beside a remaster label matter even without punctuation.
    remaster = r'(?:remaster(?:ed|izado|izada)?(?:\s+version)?)'
    years = re.findall(remaster + r'\s*[-:]?\s*((?:19|20)\d{2})|((?:19|20)\d{2})\s*' + remaster, title, re.I)
    if years:
        result['remaster_year'] = {a or b for a, b in years}
    for label in labels:
        tokens = matching_tokens(label)
        if 'remix' in tokens:
            name = tokens - {'remix', 'version', 'mix', 'the'}
            if name:
                result.setdefault('remixer', set()).update(name)
        if 'live' in tokens:
            context = tokens - {'live', 'at', 'in', 'from', 'the', 'version'}
            if context:
                result.setdefault('performance', set()).update(context)
        if 'edit' in tokens:
            kind = tokens & {'radio', 'single', 'album', 'original'}
            if kind:
                result['edit'] = kind
    return result


def edition_conflicts(left, right):
    a, b = edition_details(left), edition_details(right)
    labels = {'remaster_year': 'Ano da remasterização diferente', 'remixer': 'Remix diferente',
              'performance': 'Apresentação ao vivo diferente', 'edit': 'Edição diferente'}
    return [labels[key] for key in a.keys() & b.keys() if a[key] != b[key]]


def differences(anchor, other, *, video=False):
    from matching import version_signature
    from record_identity import normalized_isrc
    from search_evidence import explicit_conflict
    reasons = edition_conflicts(anchor, other)
    if version_signature(recording_title(anchor)) != version_signature(recording_title(other)):
        reasons.append('Tipo de versão diferente')
    if explicit_conflict(anchor, other):
        reasons.append('Conteúdo explícito/censurado diferente')
    a, b = normalized_isrc(anchor.get('isrc')), normalized_isrc(other.get('isrc'))
    if a and b and a != b:
        reasons.append('ISRC diferente')
    a, b = anchor.get('duration_ms'), other.get('duration_ms')
    if video:
        seconds = other.get('duration')
        b = seconds * 1000 if finite_positive(seconds) else None
    if finite_positive(a) and finite_positive(b):
        tolerance = max(6000, min(15000, a * .04)) if video else max(4000, min(10000, min(a,b) * .03))
        if abs(a-b) > tolerance:
            reasons.append('Duração incompatível')
    elif finite_positive(a):
        reasons.append('Duração não informada')
    return reasons
