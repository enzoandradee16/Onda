"""Search settings labels, descriptions and their real categories in the UI language."""
from functools import lru_cache
import json
from pathlib import Path
import unicodedata
from i18n import tr,normalize_language

def fold(value):
    return ''.join(c for c in unicodedata.normalize('NFD',str(value).casefold()) if not unicodedata.combining(c))

@lru_cache(maxsize=1)
def search_terms():
    return json.loads((Path(__file__).parent/'settings_schema/search_terms.json').read_text(encoding='utf-8'))

@lru_cache(maxsize=512)
def indexed_text(label,values,language):
    aliases=search_terms().get(label,{})
    return fold(' '.join(list(values)+[tr(value,language) for value in values]+list(aliases.values())))

def matches(query,field,language=None):
    import i18n
    selected=normalize_language(language or i18n._language)
    values=tuple(str(field.get(key) or '') for key in ('label','category','hint'))
    # Include canonical labels as well as translated labels, never stored values.
    indexed=indexed_text(field.get('label',''),values,selected)
    return all(term in indexed for term in fold(query).split())
