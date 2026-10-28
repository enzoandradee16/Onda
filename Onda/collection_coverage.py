"""Explicit collection coverage; unknown totals never imply completeness."""
from collections import Counter
from duplicate_links import source_key
from pathlib import Path


def annotate(result, total=None, *, uncertain=False, capped=False, skipped=0):
    rows = result.get('tracks') or []
    if type(total) is not int or total < 0:
        total = None
    loaded = len(rows)
    partial = capped or skipped > 0 or total is not None and loaded < total
    result['coverage'] = dict(loaded=loaded, total=total, skipped=skipped,
                              state='partial' if partial else 'unknown' if uncertain or total is None else 'complete',
                              limit_reached=bool(capped))
    summary = f'Carregadas {loaded} de {total} faixas.' if total is not None else f'Carregadas {loaded} faixas; total da origem não confirmado.'
    if partial:
        summary += ' A lista está incompleta; confira o limite e os itens indisponíveis.'
    elif uncertain or total is None:
        summary += ' A fonte pode mostrar somente parte da coleção.'
    else:
        summary += ' Todas as faixas informadas pela origem foram carregadas.'
    result['coverage_summary'] = summary
    return result


def compare(loaded, reference):
    """Compare multiplicities by source identity, never claim title equivalence."""
    def keys(rows):
        return Counter(key for row in rows if (key := source_key(row.get('source_url', ''))))
    actual, expected = keys(loaded), keys(reference)
    missing, extra = sum((expected-actual).values()), sum((actual-expected).values())
    return {'matched': sum((actual & expected).values()), 'missing': missing, 'extra': extra,
            'message': f'Comparação por links: {sum((actual & expected).values())} correspondentes; {missing} ausentes; {extra} fora da referência. Catálogos diferentes podem usar links diferentes para a mesma música.'}


def compare_file(tracks, source):
    from playlist_files import load_csv
    from playlist_import import load_text
    path=Path(source)
    if path.stat().st_size>10*1024*1024:raise ValueError('Arquivo de lista acima do limite de 10 MB.')
    raw=path.read_text(encoding='utf-8-sig')
    reference=(load_csv if path.suffix.lower()=='.csv' else load_text)(raw,5000)
    result=compare(tracks,reference['tracks'])
    if reference.get('coverage',{}).get('state')!='complete':result['message']+=' A referência importada também está incompleta.'
    return result
