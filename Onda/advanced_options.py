"""Portable non-secret preferences, schedule windows and release discovery."""
from datetime import datetime
import re

DEFAULTS={'finish_action':'Notificação','close_behavior':'Encerrar','taskbar_progress':True,'wifi_only':False,'wifi_loss':'Pausar downloads','notification_controls':True,'synced_lyrics':False,'clipboard_links':True,'auto_select_media':True,'simple_download_ui':False,'social_best_quality':True,'concurrent_downloads':'1','detect_duplicates':True,'auto_metadata':False,'resume_downloads':True,'resume_queue':False,'normalize_volume':False,
          'schedule_enabled':False,'schedule_start':'22:00','schedule_stop':'07:00','check_updates':True,'notice_animation':True,'queue_actions_at_top':True,'confirm_version':False}

ANDROID_ONLY=frozenset(('wifi_only','wifi_loss','notification_controls'))
PC_DEFAULTS={key:value for key,value in DEFAULTS.items() if key not in ANDROID_ONLY}

DAILY_CHOICES={'finish_action':('Nenhuma','Som','Notificação','Som e notificação','Desligar PC'),'close_behavior':('Encerrar','Minimizar para a bandeja'),'wifi_loss':('Pausar downloads','Concluir downloads ativos')}

def valid_time(value):return isinstance(value,str) and re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',value) is not None

def schedule_allowed(options,now=None):
    if not options.get('schedule_enabled'):return True
    start,stop=options.get('schedule_start',''),options.get('schedule_stop','')
    if not valid_time(start) or not valid_time(stop) or start==stop:return False
    clock=(now or datetime.now()).strftime('%H:%M')
    return start<=clock<stop if start<stop else clock>=start or clock<stop

def clean_advanced(options):
    result={}
    for key,default in DEFAULTS.items():
        value=options.get(key)
        if type(default) is bool and type(value) is bool:result[key]=value
        elif key in DAILY_CHOICES and value in DAILY_CHOICES[key]:result[key]=value
        elif key=='concurrent_downloads' and str(value) in tuple(str(n) for n in range(1,16)):result[key]=str(value)
        elif key in ('schedule_start','schedule_stop') and valid_time(value):result[key]=value
    return result

COMMON={'interface_spacing','notice_animation','queue_view','queue_card_size','language','history_card_size','pure_black_separators','history_view','theme','accent','interface_font','notice_duration','mode','audio_quality','height','fps','auto_match','review_metadata','organization','filename_template','playlist_limit',*DEFAULTS}
ALIASES={'theme_mode':'theme','theme_accent':'accent','mp3_quality':'audio_quality'}

def export_settings(options,platform):
    values={ALIASES.get(k,k):v for k,v in options.items() if ALIASES.get(k,k) in COMMON}
    if platform=='windows':
        from engine import MODES,HEIGHTS,FPS_OPTIONS
        values['mode']=MODES.get(options.get('mode'),'mp3')
        quality=options.get('m4a_quality' if values['mode']=='m4a' else 'mp3_quality')
        if quality:values['audio_quality']=quality
        values['height']=HEIGHTS.get(options.get('height'),1080)
        values['fps']=FPS_OPTIONS.get(options.get('fps'))
    return {'schema':'onda-preferences','version':1,'settings':values}

def import_settings(payload,platform):
    if not isinstance(payload,dict) or payload.get('schema')!='onda-preferences' or payload.get('version')!=1 or not isinstance(payload.get('settings'),dict):
        raise ValueError('Arquivo de configurações ONDA inválido.')
    source={k:v for k,v in payload['settings'].items() if k in COMMON}
    # Only simple preference values; never import secrets, local paths or URIs.
    if any(not isinstance(v,(str,int,float,bool,type(None))) for v in source.values()):raise ValueError('Configuração inválida.')
    result={k:v for k,v in source.items() if k not in DEFAULTS}
    for key in ('auto_match','review_metadata','pure_black_separators','notice_animation'):
        if key in result and type(result[key]) is not bool:result.pop(key)
    from engine import MODES,HEIGHTS,FPS_OPTIONS
    choices={'interface_spacing':{'Compacto','Padrão','Confortável'},'queue_view':{'Compacto','Completa'},'queue_card_size':{'Pequeno','Médio','Grande'},'language':{'pt-BR','es','en'},'history_card_size':{'Pequeno','Médio','Grande'},'history_view':{'Compacto','Completa'},'mode':set(MODES.values()),'height':set(HEIGHTS.values()),'fps':set(FPS_OPTIONS.values()),
             'theme':{'Claro','Escuro','Preto puro','Seguir o sistema','Alto contraste'},
             'audio_quality':{'320 kbps','256 kbps','192 kbps','128 kbps','96 kbps','64 kbps','Melhor disponível'},
             'organization':{'Catálogo','Pasta de destino','Artista','Artista / Álbum'}}
    from file_output import ORGANIZATIONS
    from output_rules import FILENAME_TEMPLATES
    choices['organization'] = set(ORGANIZATIONS)
    choices['filename_template'] = set(FILENAME_TEMPLATES)
    for key,allowed in choices.items():
        if key in result and (type(result[key]) is bool or result[key] not in allowed):result.pop(key)
    from status_notice import NOTICE_DURATIONS
    if 'notice_duration' in result and (not isinstance(result['notice_duration'],str) or result['notice_duration'] not in NOTICE_DURATIONS):result.pop('notice_duration')
    for key in ('accent','interface_font'):
        if key in result and (not isinstance(result[key],str) or len(result[key])>80):result.pop(key)
    if 'playlist_limit' in result:
        try:result['playlist_limit']=max(1,min(5000,int(result['playlist_limit'])))
        except (ValueError,TypeError,OverflowError):result.pop('playlist_limit')
    result.update(clean_advanced(source))
    if platform=='windows':
        from engine import MODES,HEIGHTS,FPS_OPTIONS
        result={next((a for a,b in ALIASES.items() if b==k),k):v for k,v in result.items()}
        for key,choices in (('mode',MODES),('height',HEIGHTS),('fps',FPS_OPTIONS)):
            if key in result:result[key]=next((label for label,value in choices.items() if value==result[key]),next(iter(choices)))
        if result.get('mode')=='Áudio · M4A (AAC)' and 'mp3_quality' in result:result['m4a_quality']=result.pop('mp3_quality')
        if 'playlist_limit' in result:result['playlist_limit']=str(result['playlist_limit'])
    else:
        if 'playlist_limit' in result:result['playlist_limit']=max(1,min(5000,int(result['playlist_limit'])))
    return result

def version_key(value):
    match=re.search(r'(\d+)\.(\d+)(?:\.(\d+))?(?:[-.]?(alpha|beta|rc)[.-]?(\d+))?',value,re.I)
    if not match:return (-1,)
    return tuple(int(match[i] or 0) for i in (1,2,3))+({'alpha':0,'beta':1,'rc':2,None:3}[match[4].lower() if match[4] else None],int(match[5] or 0))

def release_update(platform,current,releases=None):
    if releases is None:
        import requests
        response=requests.get('https://api.github.com/repos/enzoandradee16/Onda/releases',headers={'Accept':'application/vnd.github+json'},params={'per_page':30},timeout=(5,15))
        response.raise_for_status();releases=response.json()
    if not isinstance(releases,list):raise ValueError('Resposta de atualização inválida.')
    matches=[]
    for release in releases:
        if release.get('draft'):continue
        for asset in release.get('assets',[]):
            name=asset.get('name','')
            if (platform=='android' and name.lower().endswith('.apk')) or (platform=='windows' and 'setup' in name.lower() and name.lower().endswith('.exe')):
                version=name if version_key(name)!=(-1,) else release.get('tag_name','')
                url=asset.get('browser_download_url','')
                if url.startswith('https://github.com/enzoandradee16/Onda/releases/download/'):
                    matches.append((version_key(version),release,asset))
    if not matches:return {'available':False,'message':'Nenhuma atualização publicada para esta plataforma.'}
    key,release,asset=max(matches,key=lambda entry:entry[0])
    available=key>version_key(current)
    return {'available':available,'message':('Nova versão disponível: ' if available else 'Você está na versão mais recente publicada: ')+asset['name'],
            'url':asset['browser_download_url'],'page':release.get('html_url',''),'version':release.get('tag_name','')}
