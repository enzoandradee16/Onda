"""Script-aware lookup forms. Search variants are not recording identity evidence."""

import re
import unicodedata as ud
from functools import lru_cache


@lru_cache(maxsize=2048)
def normalize(value):
    text = ud.normalize('NFKC', str(value or '')).casefold()
    parts = []
    latin_base = False
    for char in text:
        if ud.category(char) == 'Cf':
            continue
        if ud.category(char).startswith('M') and latin_base:
            continue
        if not ud.category(char).startswith('M'):
            latin_base = 'LATIN' in ud.name(char, '')
        if 'LATIN' in ud.name(char, ''):
            char = ''.join(c for c in ud.normalize('NFD', char) if not ud.combining(c))
        parts.append(char)
    # Preserve dakuten, Cyrillic breve and Indic vowel signs; only Latin accents fold.
    text = ud.normalize('NFC', ''.join(parts))
    return ''.join(chr(ord(c) - 0x60) if '\u30a1' <= c <= '\u30f6' else c for c in text)


_KANA = dict(
    zip(
        'あいうえおかきくけこがぎぐげごさしすせそざじずぜぞたちつてとだぢづでどなにぬねのはひふへほばびぶべぼぱぴぷぺぽまみむめもやゆよらりるれろわをんゔぁぃぅぇぉゃゅょゎ',
        'a i u e o ka ki ku ke ko ga gi gu ge go sa shi su se so za ji zu ze zo ta chi tsu te to da ji zu de do na ni nu ne no ha hi fu he ho ba bi bu be bo pa pi pu pe po ma mi mu me mo ya yu yo ra ri ru re ro wa o n vu a i u e o ya yu yo wa'.split(),
    )
)
_DIGRAPHS = {}
for base, stem in [
    ('き', 'ky'),
    ('ぎ', 'gy'),
    ('し', 'sh'),
    ('じ', 'j'),
    ('ち', 'ch'),
    ('に', 'ny'),
    ('ひ', 'hy'),
    ('び', 'by'),
    ('ぴ', 'py'),
    ('み', 'my'),
    ('り', 'ry'),
]:
    for small, vowel in [('ゃ', 'a'), ('ゅ', 'u'), ('ょ', 'o')]:
        _DIGRAPHS[base + small] = stem + vowel
_DIGRAPHS.update(
    {
        'てぃ': 'ti',
        'でぃ': 'di',
        'ふぁ': 'fa',
        'ふぃ': 'fi',
        'ふぇ': 'fe',
        'ふぉ': 'fo',
        'しぇ': 'she',
        'ちぇ': 'che',
        'じぇ': 'je',
        'うぃ': 'wi',
        'うぇ': 'we',
        'うぉ': 'wo',
        'とぅ': 'tu',
        'どぅ': 'du',
        'ゔぁ': 'va',
        'ゔぃ': 'vi',
        'ゔぇ': 've',
        'ゔぉ': 'vo',
    }
)


def romanize_kana(value):
    text = normalize(value)
    # Kanji readings are ambiguous: do not invent one or partially romanize a title.
    if re.search(r'[\u3400-\u9fff]', text):
        return None
    output = []
    geminate = False
    index = 0
    while index < len(text):
        char = text[index]
        if char == 'っ':
            geminate = True
            index += 1
            continue
        if char == 'ー':
            previous = ''.join(output)
            if previous and previous[-1] in 'aeiou':
                output.append(previous[-1])
            else:
                return None
            index += 1
            continue
        pair = text[index : index + 2]
        syllable = _DIGRAPHS.get(pair) or _KANA.get(char)
        if syllable:
            if geminate:
                if syllable[0] in 'aeioun':
                    return None
                output.append('t' if syllable.startswith('ch') else syllable[0])
            output.append(syllable)
            geminate = False
            index += 2 if pair in _DIGRAPHS else 1
        else:
            if geminate or ud.category(char).startswith('M'):
                return None
            output.append(char)
            index += 1
    return None if geminate else ''.join(output)


def macron_forms(value):
    text = ud.normalize('NFKC', str(value or '')).casefold()
    if not any(c in text for c in 'āīūēō'):
        return []
    return [
        text.translate(
            str.maketrans({'ā': 'aa', 'ī': 'ii', 'ū': 'uu', 'ē': 'ee', 'ō': long_o})
        )
        for long_o in ('ou', 'oo')
    ]


def variants(value, limit=5):
    original = ' '.join(str(value or '').split())
    canonical = ud.normalize('NFKC', original)
    hira = normalize(canonical)
    kata = ''.join(chr(ord(c) + 0x60) if '\u3041' <= c <= '\u3096' else c for c in hira)
    roman = romanize_kana(original) if re.search(r'[\u3040-\u30ff]', original) else None
    result, seen = [], set()
    loose = ''.join(
        (
            ''.join(c for c in ud.normalize('NFD', char) if not ud.combining(c))
            if 'GREEK' in ud.name(char, '')
            else char
        )
        for char in canonical
    )
    loose = (
        re.sub(r'[\u0640\u064b-\u065f\u0670]', '', loose)
        .replace('ё', 'е')
        .replace('Ё', 'Е')
    )
    for value in (
        original,
        canonical,
        hira,
        kata,
        roman,
        *macron_forms(original),
        loose,
    ):
        if value and value.casefold() not in seen:
            result.append(value)
            seen.add(value.casefold())
    return result[:limit]


def comparison_keys(value):
    forms = [normalize(value), *macron_forms(value)]
    roman = romanize_kana(value)
    if roman:
        forms.append(roman)
    return {''.join(tokens(form)) for form in forms if form}


def equivalent(left, right):
    return bool(comparison_keys(left) & comparison_keys(right))


def tokens(value):
    text = re.sub(r"(?<=\w)[’'ʼ](?=\w)", '', normalize(value or ''))
    found, current = [], []
    for char in text:
        if ud.category(char)[0] in 'LNM':
            current.append(char)
        elif current:
            found.append(''.join(current))
            current = []
    if current:
        found.append(''.join(current))
    return found


def contains_terms(needle, haystack):
    """Discovery only: CJK titles need not contain spaces around a search fragment."""

    def loose(value):
        text = normalize(value or '')
        text = ''.join(
            (
                ''.join(c for c in ud.normalize('NFD', char) if not ud.combining(c))
                if 'GREEK' in ud.name(char, '')
                else char
            )
            for char in text
        )
        return re.sub(r'[\u0640\u064b-\u065f\u0670]', '', text).replace('ё', 'е')

    wanted, found = tokens(loose(needle)), tokens(loose(haystack))
    return bool(wanted) and all(
        term in found
        or (
            len(term) >= 2
            and re.search(r'[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]', term)
            and any(term in value for value in found)
        )
        for term in wanted
    )
