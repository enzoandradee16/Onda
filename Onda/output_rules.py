"""Bounded filename and folder presets shared by desktop and Android downloads."""
import re
from pathlib import Path

FILENAME_TEMPLATES = ('Original', 'Artista - Música', 'Faixa - Música',
                      'Faixa - Artista - Música', 'Disco-Faixa - Música')
EXTRA_ORGANIZATIONS = ('Álbum', 'Artista / Ano - Álbum', 'Gênero / Artista / Álbum',
                       'Formato / Artista / Álbum')


def positive_number(value, default=0):
    try:
        number = int(str(value).split('/')[0])
        return number if 0 < number <= 9999 else default
    except (ValueError, TypeError):
        return default


def fields(record=None, info=None):
    record, info = record or {}, info or {}
    artists = record.get('artists') or []
    return {
        'artist': artists[0] if artists else info.get('artist') or info.get('uploader') or 'Artista desconhecido',
        'album': record.get('album') or info.get('album') or 'Álbum não informado',
        'title': record.get('title') or info.get('track') or info.get('title') or 'Música',
        'genre': record.get('genre') or info.get('genre') or 'Gênero não informado',
        'year': str(record.get('release_date') or info.get('release_date') or info.get('upload_date') or '')[:4],
        'track': positive_number(record.get('track_number') or info.get('track_number') or info.get('playlist_index')),
        'disc': positive_number(record.get('disc_number') or info.get('disc_number'), 1),
    }


def folder_parts(organization, mode, record=None, info=None):
    from file_output import component
    data = fields(record, info)
    year = data['year'] if re.fullmatch(r'\d{4}', data['year']) else 'Ano não informado'
    parts = {
        'Álbum': [data['album']],
        'Artista / Ano - Álbum': [data['artist'], year + ' - ' + data['album']],
        'Gênero / Artista / Álbum': [data['genre'], data['artist'], data['album']],
        'Formato / Artista / Álbum': [str(mode or 'Áudio').upper(), data['artist'], data['album']],
    }.get(organization)
    return [component(part) for part in parts] if parts is not None else None


def output_filename(source, config, record=None, info=None):
    from file_output import component
    template = config.get('filename_template', 'Original')
    if template not in FILENAME_TEMPLATES:
        raise ValueError('Modelo de nome de arquivo inválido.')
    if template == 'Original':
        return Path(source).name
    data = fields(record, info)
    # Unavailable track numbers are omitted rather than inventing a track order.
    number = f"{data['track']:02d} - " if data['track'] else ''
    names = {
        'Artista - Música': data['artist'] + ' - ' + data['title'],
        'Faixa - Música': number + data['title'],
        'Faixa - Artista - Música': number + data['artist'] + ' - ' + data['title'],
        'Disco-Faixa - Música': (f"{data['disc']}-{data['track']:02d} - " if data['track'] else '') + data['title'],
    }
    return component(names[template]) + Path(source).suffix


def preview_path(config, translate=lambda value: value):
    from file_output import destination
    record = {'artists': ['Artista'], 'album': 'Álbum', 'title': 'Música', 'genre': 'Gênero',
              'release_date': '2026', 'track_number': 1, 'disc_number': 1, 'platform': 'Deezer', 'id': '123'}
    record.update(artists=[translate('Artista')], album=translate('Álbum'), title=translate('Música'), genre=translate('Gênero'))
    folder = destination(dict(config, folder=str(Path.cwd())), record)
    name = output_filename('Artista - Música.mp3', config, record)
    return (folder.relative_to(Path.cwd().resolve()) / name).as_posix()
