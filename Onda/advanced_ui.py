"""Desktop controls for queue policy, schedules and local library tools."""
import json
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
import webbrowser

def move_queue(app,direction):
    order=list(app.tree.get_children());selected=list(app.tree.selection())
    moving=[key for key in selected if app.jobs[key]['state']!='Em andamento']
    if direction==0:order=moving+[key for key in order if key not in moving]
    else:
        for key in moving if direction<0 else reversed(moving):
            index=order.index(key);other=index+direction
            if 0<=other<len(order) and order[other] not in moving:order[index],order[other]=order[other],order[index]
    for index,key in enumerate(order):app.tree.move(key,'',index)
    app.persist_queue()

def settings_tools(app,parent):
    from advanced_options import DEFAULTS
    ttk.Separator(parent).pack(fill='x',pady=12)
    ttk.Label(parent,text='Fila e agendamento',font=('Segoe UI',12,'bold')).pack(anchor='w')
    ttk.Label(parent,text='Downloads simultâneos (1 a 4)').pack(anchor='w',pady=(8,3))
    ttk.Combobox(parent,textvariable=app.concurrent_downloads,values=('1','2','3','4'),state='readonly',width=8).pack(anchor='w')
    for key,label in (('resume_downloads','Retomar arquivos interrompidos quando possível'),('resume_queue','Retomar fila ao abrir o ONDA'),('normalize_volume','Normalizar volume dos próximos downloads'),('schedule_enabled','Agendar downloads'),('check_updates','Verificar atualizações do ONDA ao abrir')):
        ttk.Checkbutton(parent,text=label,variable=getattr(app,key)).pack(anchor='w',pady=5)
    hours=ttk.Frame(parent);hours.pack(fill='x',pady=6)
    for key,label in (('schedule_start','Começar · HH:MM'),('schedule_stop','Parar · HH:MM')):
        panel=ttk.Frame(hours);panel.pack(side='left',padx=(0,16));ttk.Label(panel,text=label).pack(anchor='w');ttk.Entry(panel,textvariable=getattr(app,key),width=12).pack()
    ttk.Label(parent,text='O PC precisa estar ligado e o ONDA aberto. A janela pode atravessar a meia-noite.',wraplength=460,style='Muted.TLabel').pack(anchor='w')
    ttk.Button(parent,text='Exportar configurações…',command=lambda:transfer(app,False)).pack(anchor='w',pady=(12,5))
    ttk.Button(parent,text='Importar configurações…',command=lambda:transfer(app,True)).pack(anchor='w')
    ttk.Button(parent,text='Verificar atualização do ONDA',command=lambda:check_update(app,True)).pack(anchor='w',pady=8)
    ttk.Label(parent,text='A transferência não inclui contas, cookies nem caminhos de pastas.',wraplength=460,style='Muted.TLabel').pack(anchor='w')

def transfer(app,importing):
    from advanced_options import import_settings,export_settings
    try:
        if importing:
            path=filedialog.askopenfilename(parent=app.settings_window,filetypes=[('Configurações ONDA','*.json')])
            if not path:return
            if Path(path).stat().st_size>131072:raise ValueError('Arquivo muito grande.')
            from preferences import PreferenceStore
            values=PreferenceStore.clean(import_settings(json.loads(Path(path).read_text(encoding='utf-8')),'windows'))
            for key,value in values.items():
                if key in app.preference_fields:app.preference_fields[key].set(value)
            app.persist_preferences()
        else:
            path=filedialog.asksaveasfilename(parent=app.settings_window,initialfile='ONDA-configuracoes.json',defaultextension='.json')
            if not path:return
            Path(path).write_text(json.dumps(export_settings({k:v.get() for k,v in app.preference_fields.items()},'windows'),ensure_ascii=False,indent=2),encoding='utf-8')
        messagebox.showinfo('Configurações','Configurações importadas.' if importing else 'Configurações exportadas.',parent=app.settings_window)
    except Exception as error:messagebox.showerror('Configurações',str(error),parent=app.settings_window)

def check_update(app,manual=False):
    from advanced_options import release_update
    def worker():
        try:result=release_update('windows','1.0.0-beta.2')
        except Exception:result={'available':False,'message':'Não foi possível verificar atualizações. Confira sua conexão.'}
        app.events.put((None,{'type':'app_update','result':result,'manual':manual}))
    threading.Thread(target=worker,daemon=True).start()

def tick(app):
    from advanced_options import schedule_allowed,valid_time
    options={key:var.get() for key,var in app.preference_fields.items()}
    if app.schedule_enabled.get():
        valid=valid_time(options['schedule_start']) and valid_time(options['schedule_stop']) and options['schedule_start']!=options['schedule_stop']
        if not valid:app.status.set('Agendamento: informe horários diferentes no formato HH:MM.')
        elif schedule_allowed(options):
            if not app.active and any(job['state']=='Na fila' for job in app.jobs.values()):app._schedule_paused=False;app.start()
        elif app.active:
            app._schedule_paused=True;app.cancel()
    app._schedule_after=app.after(15000,lambda:tick(app))

class AudioEditor(tk.Toplevel):
    def __init__(self,app,path):
        from audio_library import read_audio
        record=read_audio(path)
        super().__init__(app)
        from audio_tools import PreviewPlayer
        self.app=app;self.source=Path(path);self.title('ONDA • Editar áudio');self.geometry('640x690');self.transient(app)
        self.player=PreviewPlayer();self.results=queue.Queue();self.busy=False;self.preview_path=None
        self.edit=tk.BooleanVar(value=True);self.normalize=tk.BooleanVar(value=False);self.fields={};self.cover='';self.lyrics=''
        body=ttk.Frame(self,padding=20);body.pack(fill='both',expand=True)
        ttk.Label(body,text=self.source.name,wraplength=570,font=('Segoe UI',13,'bold')).pack(fill='x',pady=8)
        ttk.Checkbutton(body,text='Editar metadados',variable=self.edit,command=self.toggle).pack(anchor='w')
        self.record=record
        self.entries=[]
        for key,label in (('title','Música'),('artists','Artistas (separados por ;)'),('album','Álbum'),('genre','Gênero'),('release_date','Data')):
            ttk.Label(body,text=label).pack(anchor='w',pady=(6,0));value=self.record.get(key,'');var=tk.StringVar(value='; '.join(value) if isinstance(value,list) else value);self.fields[key]=var
            entry=ttk.Entry(body,textvariable=var);entry.pack(fill='x');self.entries.append(entry)
        ttk.Button(body,text='Escolher outra capa…',command=self.pick_cover).pack(anchor='w',pady=6)
        self.lyrics_label=tk.StringVar(value='Letra opcional · TXT ou LRC')
        ttk.Button(body,textvariable=self.lyrics_label,command=self.pick_lyrics).pack(anchor='w')
        ttk.Checkbutton(body,text='Normalizar volume (−16 LUFS)',variable=self.normalize).pack(anchor='w',pady=12)
        actions=ttk.Frame(body);actions.pack(fill='x')
        ttk.Button(actions,text='Ouvir original',command=lambda:self.player.play(self.source,app.ffmpeg.get(),duration=20)).pack(side='left')
        ttk.Button(actions,text='Ouvir normalizado',command=lambda:self.run(True)).pack(side='left',padx=5)
        ttk.Button(actions,text='Parar',command=self.player.stop).pack(side='left')
        ttk.Button(body,text='Salvar cópia editada',style='Accent.TButton',command=lambda:self.run(False)).pack(anchor='e',pady=12)
        self.status=tk.StringVar(value='O arquivo original será preservado.');ttk.Label(body,textvariable=self.status,wraplength=570).pack(fill='x')
        self.protocol('WM_DELETE_WINDOW',self.close);self._poll=self.after(100,self.poll)

    def toggle(self):
        for entry in self.entries:entry.configure(state='normal' if self.edit.get() else 'disabled')
    def pick_cover(self):self.cover=filedialog.askopenfilename(parent=self,filetypes=[('Capas','*.png *.jpg *.jpeg')]) or self.cover
    def pick_lyrics(self):
        self.lyrics=filedialog.askopenfilename(parent=self,filetypes=[('Letras','*.lrc *.txt')]) or self.lyrics
        if self.lyrics:self.lyrics_label.set(Path(self.lyrics).name)
    def run(self,preview):
        if self.busy:return
        self.busy=True;self.status.set('Preparando prévia…' if preview else 'Salvando cópia…')
        self.player.stop()
        changes={k:v.get() for k,v in self.fields.items()};changes['artists']=[s.strip() for s in changes['artists'].split(';') if s.strip()]
        config={'source':str(self.source),'folder':str(self.source.parent),'ffmpeg':self.app.ffmpeg.get(),'edit_metadata':self.edit.get(),'changes':changes,'cover_path':self.cover,'lyrics_path':self.lyrics,'normalize_volume':self.normalize.get()}
        def worker():
            try:
                from audio_library import normalize_audio,edit_copy
                result={'preview':str(normalize_audio(self.source,config,preview=True))} if preview else edit_copy(config)
                self.results.put(result)
            except Exception as error:self.results.put({'error':str(error)})
        threading.Thread(target=worker,daemon=True).start()
    def poll(self):
        try:
            result=self.results.get_nowait();self.busy=False
            if result.get('error'):self.status.set(result['error'])
            elif result.get('preview'):
                self.preview_path=Path(result['preview']);self.player.play(self.preview_path,self.app.ffmpeg.get(),duration=20);self.status.set('Prévia normalizada · 20 segundos')
            else:
                self.app.record_history(result['path'],result['mode'].upper(),'');self.status.set('Salvo: '+result['path'])
        except queue.Empty:pass
        self._poll=self.after(100,self.poll)
    def close(self):
        if self.busy:self.status.set('Aguarde o processamento terminar antes de fechar.');return
        self.player.stop()
        if self.preview_path:self.preview_path.unlink(missing_ok=True)
        self.after_cancel(self._poll);self.destroy()
