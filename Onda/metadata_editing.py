"""Shared, explicit metadata previews and batch text operations."""
from pathlib import Path
import base64
import io

LABELS = dict(title='Título', artists='Artista', album='Álbum', genre='Gênero',
              release_date='Data de lançamento', track_number='Faixa', disc_number='Disco',
              isrc='ISRC', album_artist='Artista do álbum', composer='Compositor', comment='Comentário')


def entries(config):
    from audio_library import read_audio
    source_rows = config.get('sources') or [dict(source=config['source'],output_name=config.get('output_name',''))]
    result, seen = [], set()
    actions = config.get('batch_actions') or {}
    targets = actions.get('fields') or ['title']
    if not isinstance(targets, list) or any(key not in ('title','artists','album','album_artist','composer','genre') for key in targets):
        raise ValueError('Campo de edição em lote inválido.')
    mode = actions.get('case', 'none')
    if mode not in ('none','title','upper','lower'):
        raise ValueError('Ajuste de texto inválido.')
    find, replacement = actions.get('find', ''), actions.get('replace', '')
    if not isinstance(find, str) or not isinstance(replacement, str) or max(len(find), len(replacement)) > 4096:
        raise ValueError('Texto de substituição inválido.')
    start = actions.get('start', 1)
    if type(start) is not int or not 1 <= start <= 9999:
        raise ValueError('Informe um número inicial de 1 a 9999.')
    for row in source_rows:
        source = str(Path(row['source']).resolve())
        if source in seen:
            continue
        seen.add(source)
        before = read_audio(source)
        if before.get('title')==Path(source).stem and (row.get('output_name') or config.get('output_name')):
            before=dict(before,title=row.get('output_name') or config['output_name'])
        changes = dict(row.get('changes', {}), **config.get('changes', {}))
        for key in targets:
            if not find and mode == 'none':
                continue
            value = changes.get(key, before.get(key, [] if key=='artists' else ''))
            def transform(text):
                text = text.replace(find, replacement) if find else text
                return getattr(text, mode)() if mode != 'none' else text
            changes[key] = [transform(v) for v in value] if isinstance(value, list) else transform(value)
        if actions.get('number_tracks'):
            changes['track_number'] = str(start + len(result))
        result.append(dict(row, source=source, changes=changes, before=before))
    return result


def text(value):
    return '; '.join(value) if isinstance(value, list) else str(value or '')


def thumbnail(value):
    if not value:
        return ''
    if value.startswith(('https://','http://')):
        return value
    from PIL import Image
    stream = io.BytesIO(base64.b64decode(value.split(',',1)[1])) if value.startswith('data:image/') else value
    with Image.open(stream) as image:
        image.thumbnail((160,160))
        output=io.BytesIO();image.convert('RGB').save(output,'JPEG',quality=80)
    return 'data:image/jpeg;base64,'+base64.b64encode(output.getvalue()).decode('ascii')


def preview(config, cancelled=lambda:False):
    from audio_library import cover_preview
    from tag_transfer import decode, encode
    transfer = config.get('tag_transfer')
    if config.get('tag_transfer_path'):
        transfer = decode(Path(config['tag_transfer_path']).read_text(encoding='utf8'))
    if transfer:
        transfer=decode(encode(transfer))
    rows=[]
    for row in entries(config):
        if cancelled():
            raise InterruptedError('Operação cancelada.')
        fields=[dict(key=key,label=LABELS[key],before=text(row['before'].get(key)),after=text(value))
                for key,value in row['changes'].items() if key in LABELS and row['before'].get(key)!=value]
        cover=config.get('cover_path') or config.get('cover_url') or row.get('cover_url') or ''
        if not cover and transfer and config.get('tag_transfer_cover',True) and transfer.get('artwork'):
            image=transfer['artwork'][0];cover='data:'+image['mime']+';base64,'+image['data']
        previous_cover=''
        if cover:
            previous_cover=cover_preview(row['source']) or ''
            if previous_cover:previous_cover='data:image/png;base64,'+previous_cover
            fields.append(dict(key='__cover__',label='Capa',before='Capa atual' if previous_cover else 'Sem capa',after='Capa selecionada'))
        if transfer:
            fields.append(dict(key='__extras__',label='Outras tags e letras',before='Tags atuais',after='Tags copiadas'))
        if config.get('lyrics_path'):
            fields.append(dict(key='__lyrics__',label='Letra',before='Letra atual',after='Letra selecionada'))
        if config.get('normalize_volume'):
            fields.append(dict(key='__normalize__',label='Normalizar volume',before='Volume original',after='Volume normalizado'))
        stat=Path(row['source']).stat()
        rows.append(dict(name=row.get('output_name') or Path(row['source']).name,source=row['source'],fields=fields,signature=[stat.st_size,stat.st_mtime_ns],
                         before_cover=previous_cover,after_cover=thumbnail(cover)))
    return dict(entries=rows,overwrite_original=bool(config.get('overwrite_original')),
                message='Confira as alterações. Desmarque o que deseja preservar.')


def select(config, report, reply):
    selection=reply.get('selected')
    if not isinstance(selection,dict):
        raise ValueError('Confirme as alterações antes de salvar.')
    rows=entries(config);chosen={};selected_rows=[];signatures={}
    for index,row in enumerate(rows):
        allowed={field['key'] for field in report['entries'][index]['fields']}
        keys=selection.get(str(index),[])
        if not isinstance(keys,list) or any(key not in allowed for key in keys):
            raise ValueError('Seleção de metadados inválida.')
        if not keys:
            continue
        stat=Path(row['source']).stat()
        expected=report['entries'][index]['signature']
        if [stat.st_size,stat.st_mtime_ns]!=expected:raise ValueError('O arquivo mudou durante a revisão. Abra a prévia novamente.')
        signatures[row['source']]=expected
        chosen[row['source']]=keys
        selected_rows.append({key:value for key,value in row.items() if key!='before'})
    return dict(config,sources=selected_rows,changes=selected_rows[0]['changes'] if len(selected_rows)==1 else {},batch_actions={},preview_selection=chosen,_preview_signatures=signatures,
                source=selected_rows[0]['source'] if selected_rows else config.get('source',''))
