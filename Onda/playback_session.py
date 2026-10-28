"""Local playback snapshots; restoring never starts a decoder or audio output."""
import json
import math
from pathlib import Path

FIELDS = ('effectsQueue','effectsQueueIndex','effectsSource','effectsRecord','effectsCover',
          'position','duration','speed','reverb','keep_pitch','effectsVolume','effectsRepeat','effectsShuffle')

def save(workspace,strict=False):
    bridge=workspace.bridge
    data={'version':1,'unified':True,'effectsEnabled':workspace.options.get('effectsEnabled',False),'effects':{key:workspace.options[key] for key in FIELDS},
          'jukebox':{'queue':bridge.playlist,'index':bridge.queue_index,'model':bridge.model,
                     'position':bridge.position,'phase':bridge.phase,'params':bridge._params,'repeat':bridge.queue_repeat,'shuffle':bridge.queue_shuffle}}
    target=workspace.store.path.with_name('playback-session.json')
    try:
        raw=json.dumps(data,ensure_ascii=False,allow_nan=False)
        if not strict and raw==getattr(workspace,'_saved_playback',None):return
        temporary=target.with_suffix('.tmp');temporary.write_text(raw,encoding='utf-8');temporary.replace(target)
        workspace._saved_playback=raw
    except (OSError,TypeError,ValueError) as error:
        if strict:raise ValueError('Não foi possível salvar a sessão antes de reiniciar.') from error

def restore(workspace):
    try:
        data=json.loads(workspace.store.path.with_name('playback-session.json').read_text(encoding='utf-8'))
        if data.get('version')!=1:return
        effects=data['effects'];bridge=workspace.bridge;jukebox=data['jukebox']
        if not isinstance(effects,dict) or not isinstance(jukebox,dict):return
        for key in FIELDS:
            if key not in effects:continue
            value=effects[key];default=workspace.options[key]
            if type(default) in (int,float):
                if type(value) not in (int,float):return
            elif not isinstance(value,type(default)):return
            if isinstance(value,(int,float)) and not math.isfinite(value):return
        rows=[row for row in effects.get('effectsQueue',[]) if isinstance(row,dict)
              and isinstance(row.get('source'),str) and Path(row['source']).is_file()
              and isinstance(row.get('record'),dict) and isinstance(row.get('duration'),(int,float))
              and math.isfinite(row['duration']) and row['duration']>0]
        source=effects.get('effectsSource','')
        if isinstance(source,str) and Path(source).is_file():
            workspace.options.update({key:effects[key] for key in FIELDS if key in effects})
            workspace.options['position']=max(0,min(float(effects.get('position',0)),float(effects.get('duration',0))))
        workspace.options.update(effectsQueue=rows,effectsQueueIndex=next((i for i,r in enumerate(rows) if r['source']==source),-1),effectsPaused=True,previewActive=False)
        old_queue=[row for row in jukebox.get('queue',[]) if isinstance(row,dict)]
        old_index=int(jukebox.get('index',-1));current_id=old_queue[old_index].get('id') if 0<=old_index<len(old_queue) else None
        bridge.playlist=[dict(row,analysis='pending') for row in old_queue if row.get('id') and (row.get('kind')=='catalog' and isinstance(row.get('record'),dict) or row.get('kind')=='file' and isinstance(row.get('source'),str) and Path(row['source']).is_file())]
        legacy_records={row.get('source'):row.get('record') for row in effects.get('effectsQueue',[]) if isinstance(row,dict) and isinstance(row.get('record'),dict)}
        if source and effects.get('effectsRecord'):legacy_records[source]=effects['effectsRecord']
        for entry in bridge.playlist:
            if entry.get('kind')=='file' and not entry.get('record') and entry.get('source') in legacy_records:
                entry['record']=dict(legacy_records[entry['source']]);bridge.queue_info(entry,entry['record'])
        bridge.queue_index=next((i for i,row in enumerate(bridge.playlist) if row['id']==current_id),-1)
        if not 0<=bridge.queue_index<len(bridge.playlist):bridge.queue_index=-1
        bridge.setQueueRepeat(jukebox.get('repeat','Desativada'));bridge.setQueueShuffle(bool(jukebox.get('shuffle',False)))
        model=jukebox.get('model')
        if isinstance(model,dict) and (Path(model.get('cache',''))/'analysis.json').is_file():
            bridge.handle_event(bridge.revision,'result',model)
            position=float(jukebox.get('position',0));phase=float(jukebox.get('phase',0))
            bridge._position=max(0,min(position,max(0,len(model.get('beats',[]))-2))) if math.isfinite(position) else 0
            bridge._phase=max(0,min(phase,1)) if math.isfinite(phase) else 0
            params=jukebox.get('params')
            if isinstance(params,list) and len(params)==4 and all(isinstance(v,(int,float,bool)) and math.isfinite(v) for v in params):bridge._params=tuple(params)
            bridge.update_state(status=__import__('i18n').tr('Sessão restaurada. Toque em reproduzir.'),playing=False,paused=False)
            bridge.positionChanged.emit()
            if bridge.queue_index>=0:bridge._prepared[bridge.playlist[bridge.queue_index]['id']]=model
        workspace.options['effectsEnabled']=data.get('effectsEnabled',False) is True
        if not data.get('unified'):
            import uuid
            # Merge once. The original effects snapshot is retained for recovery.
            candidates=list(effects.get('effectsQueue',[]))
            if source and not any(row.get('source')==source for row in candidates):candidates.insert(0,dict(source=source,record=effects.get('effectsRecord',{})))
            for row in candidates:
                if not isinstance(row,dict):continue
                path=row.get('source','');record=row.get('record') or {}
                if Path(path).is_file():
                    entry=dict(id=uuid.uuid4().hex,kind='file',source=path,record=dict(record),title=record.get('title') or Path(path).stem,analysis='pending')
                    if path==source:entry['restore_seconds']=max(0,float(effects.get('position',0)))
                    bridge.queue_info(entry,record);bridge.playlist.append(entry)
                elif record.get('source_url'):
                    entry=dict(id=uuid.uuid4().hex,kind='catalog',record=record,title=record.get('title') or path,analysis='pending')
                    bridge.queue_info(entry,record);bridge.playlist.append(entry)
            if not bridge.model and Path(source).is_file():
                # Restoration stays silent; preparation starts only on an explicit play.
                bridge.queue_index=next((i for i,row in enumerate(bridge.playlist) if row.get('source')==source),-1)
                bridge.update_state(title=effects.get('effectsRecord',{}).get('title') or Path(source).stem,status='Sessão restaurada. Toque em reproduzir.')
                bridge._params=bridge._params[:3]+(True,)
                bridge._params=bridge._params[:2]+(effects.get('effectsVolume',80),True)
                bridge.setQueueRepeat(effects.get('effectsRepeat','Desativada'));bridge.setQueueShuffle(bool(effects.get('effectsShuffle',False)))
                workspace.options['effectsEnabled']=True
        workspace.optionsChanged.emit();bridge.queueChanged.emit()
    except (OSError,ValueError,TypeError,KeyError,AttributeError):return
