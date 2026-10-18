"""Desktop controls for queue policy, schedules and local library tools."""
from i18n import tr
from i18n_tk import TranslatedCombobox, display_var
import json
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import ttk,filedialog,messagebox

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

def download_policy_controls(app,parent):
    ttk.Separator(parent).pack(fill='x',pady=12)
    ttk.Label(parent,text=tr('Fila e agendamento'),font=('Segoe UI',12,'bold')).pack(anchor='w')
    ttk.Label(parent,text=tr('Downloads simultâneos')).pack(anchor='w',pady=(8,3))
    TranslatedCombobox(parent,textvariable=app.concurrent_downloads,values=tuple(str(n) for n in range(1,16)),state='readonly',width=8).pack(anchor='w')
    ttk.Label(parent,text=tr('No PC, escolha de 1 a 15 downloads simultâneos.'),wraplength=460,style='Muted.TLabel').pack(anchor='w',pady=(4,0))
    ttk.Label(parent,text=tr('Aviso: muitos downloads simultâneos, especialmente de 10 a 15, podem pesar o app e aumentar o uso de memória, processador e internet. Reduza se notar lentidão.'),wraplength=460,style='Muted.TLabel').pack(anchor='w',pady=(6,8))
    for key,label in (('detect_duplicates','Detectar duplicatas na fila e no histórico'),('resume_downloads','Retomar arquivos interrompidos quando possível'),('resume_queue','Retomar fila ao abrir o ONDA'),('normalize_volume','Normalizar volume dos próximos downloads'),('schedule_enabled','Agendar downloads')):
        ttk.Checkbutton(parent,text=tr(label),variable=getattr(app,key)).pack(anchor='w',pady=5)
    hours=ttk.Frame(parent);hours.pack(fill='x',pady=6)
    for key,label in (('schedule_start','Começar · HH:MM'),('schedule_stop','Parar · HH:MM')):
        panel=ttk.Frame(hours);panel.pack(side='left',padx=(0,16));ttk.Label(panel,text=tr(label)).pack(anchor='w');ttk.Entry(panel,textvariable=getattr(app,key),width=12).pack()
    ttk.Label(parent,text=tr('O PC precisa estar ligado e o ONDA aberto. A janela pode atravessar a meia-noite.'),wraplength=460,style='Muted.TLabel').pack(anchor='w')
    from daily_desktop import settings_controls
    settings_controls(app,parent)

def preference_transfer_controls(app,parent):
    ttk.Separator(parent).pack(fill='x',pady=12)
    ttk.Button(parent,text=tr('Exportar configurações…'),command=lambda:transfer(app,False)).pack(anchor='w',pady=(0,5))
    ttk.Button(parent,text=tr('Importar configurações…'),command=lambda:transfer(app,True)).pack(anchor='w')
    ttk.Label(parent,text=tr('A transferência não inclui contas, cookies nem caminhos de pastas.'),wraplength=460,style='Muted.TLabel').pack(anchor='w',pady=(6,0))

def app_update_controls(app,parent):
    ttk.Separator(parent).pack(fill='x',pady=12)
    ttk.Label(parent,text=tr('Atualizações do ONDA'),font=('Segoe UI',12,'bold')).pack(anchor='w')
    ttk.Checkbutton(parent,text=tr('Verificar atualizações do ONDA ao abrir'),variable=app.check_updates).pack(anchor='w',pady=6)
    ttk.Button(parent,text=tr('Verificar atualização do ONDA'),command=lambda:check_update(app,True)).pack(anchor='w',pady=8)


def transfer(app,importing):
    from advanced_options import import_settings,export_settings
    try:
        if importing:
            path=filedialog.askopenfilename(parent=app.settings_window,filetypes=[(tr('Configurações ONDA'),'*.json')])
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
        messagebox.showinfo(tr('Importar configurações' if importing else 'Exportar configurações'),tr('Configurações importadas.' if importing else 'Configurações exportadas.'),parent=app.settings_window)
    except Exception as error:messagebox.showerror(tr('Importar configurações' if importing else 'Exportar configurações'),tr(str(error)),parent=app.settings_window)

def check_update(app,manual=False):
    from advanced_options import release_update
    def worker():
        try:result=release_update('windows','1.1.5')
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
            if not app.active and any(job['state']=='Na fila' for job in app.jobs.values()):app._schedule_paused=False;app.start(scheduled=True)
        elif app.active:
            app._schedule_paused=True;app.cancel()
    app._schedule_after=app.after(15000,lambda:tick(app))

class AudioEditor(ttk.Frame):
    def __init__(self,parent,app,path,on_choose):
        from audio_library import read_audio
        record=read_audio(path)
        super().__init__(parent)
        from audio_tools import PreviewPlayer
        self.app=app;self.source=Path(path);self.closed=False
        self.player=PreviewPlayer();self.results=queue.Queue();self.busy=False;self.preview_path=None
        self.edit=tk.BooleanVar(value=True);self.normalize=tk.BooleanVar(value=False);self.overwrite=tk.BooleanVar(value=False);self.fields={};self.cover='';self.lyrics=''
        import tempfile
        self.cover_temp=tempfile.TemporaryDirectory(prefix='onda-covers-')
        body=ttk.Frame(self,padding=16);body.pack(fill='both',expand=True)
        from audio_library import cover_preview
        self.original_cover=cover_preview(self.source)
        header=ttk.Frame(body);header.pack(fill='x',pady=6)
        details=ttk.Frame(header);details.pack(side='left',fill='x',expand=True)
        ttk.Label(details,text=self.source.name,wraplength=440,font=('Segoe UI',13,'bold')).pack(fill='x')
        ttk.Button(header,text=tr('Escolher outro arquivo'),style='Accent.TButton',command=on_choose).pack(side='right',padx=(12,0))
        ttk.Checkbutton(body,text=tr('Editar metadados'),variable=self.edit,command=self.toggle).pack(anchor='w')
        self.record=record
        self.entries=[]
        for key,label in (('title','Música'),('artists','Artistas (separados por ;)'),('album','Álbum'),('genre','Gênero'),('release_date','Data')):
            ttk.Label(body,text=tr(label)).pack(anchor='w',pady=(4,0));value=self.record.get(key,'');var=tk.StringVar(value='; '.join(value) if isinstance(value,list) else value);self.fields[key]=var
            entry=ttk.Entry(body,textvariable=var);entry.pack(fill='x');self.entries.append(entry)
        lower=ttk.Frame(body);lower.pack(fill='x',pady=(10,0))
        controls=ttk.Frame(lower);controls.pack(side='left',fill='both',expand=True)
        artwork=ttk.Frame(lower);artwork.pack(side='right',padx=(10,0))
        self.cover_image_label=ttk.Label(artwork,text=tr('Sem capa'),width=20,anchor='center')
        self.cover_image_label.pack()
        ttk.Button(artwork,text=tr('Escolher outra capa…'),command=self.pick_cover).pack(fill='x',pady=(6,0))
        self.crop_cover_button=ttk.Button(artwork,text=tr('Ajustar capa'),command=self.adjust_cover,state='disabled')
        self.crop_cover_button.pack(fill='x')
        self.undo_cover_button=ttk.Button(artwork,text=tr('Desfazer capa'),command=self.undo_cover,state='disabled')
        self.undo_cover_button.pack(fill='x')
        self.show_cover(self.original_cover)
        self.lyrics_label=tk.StringVar(value='Letra opcional · TXT ou LRC')
        ttk.Button(controls,textvariable=display_var(self.lyrics_label),command=self.pick_lyrics).pack(anchor='w')
        ttk.Checkbutton(controls,text=tr('Normalizar volume (−16 LUFS)'),variable=self.normalize).pack(anchor='w',pady=6)
        actions=ttk.Frame(controls);actions.pack(fill='x')
        ttk.Button(actions,text=tr('Ouvir original'),command=lambda:self.player.play(self.source,app.ffmpeg.get(),duration=20)).pack(side='left')
        ttk.Button(actions,text=tr('Ouvir normalizado'),command=lambda:self.run(True)).pack(side='left',padx=5)
        ttk.Button(actions,text=tr('Parar'),command=self.player.stop).pack(side='left')
        ttk.Checkbutton(controls,text=tr('Sobrescrever arquivo original'),variable=self.overwrite,command=self.save_mode).pack(anchor='w',pady=(4,0))
        self.save_text=tk.StringVar(value='Salvar cópia editada')
        ttk.Button(artwork,textvariable=display_var(self.save_text),style='Accent.TButton',command=lambda:self.run(False)).pack(fill='x',pady=(6,0))
        self.status=tk.StringVar(value='O arquivo original será preservado.');ttk.Label(body,textvariable=display_var(self.status),wraplength=570).pack(fill='x')
        self._poll=self.after(100,self.poll)

    def save_mode(self):
        self.save_text.set('Salvar no original' if self.overwrite.get() else 'Salvar cópia editada')
        if not self.busy:self.status.set('O arquivo original será substituído, mantendo o nome e a pasta.' if self.overwrite.get() else 'O arquivo original será preservado.')
    def toggle(self):
        for entry in self.entries:entry.configure(state='normal' if self.edit.get() else 'disabled')
    def show_cover(self,data):
        from PIL import Image,ImageTk
        import base64,io
        self.cover_photo=None
        if data:
            with Image.open(io.BytesIO(base64.b64decode(data))) as image:
                image.thumbnail((180,180));self.cover_photo=ImageTk.PhotoImage(image.copy(),master=self)
        self.cover_image_label.configure(image=self.cover_photo or '',text=tr('' if self.cover_photo else 'Sem capa'))
    def undo_cover(self):
        if self.busy:return
        if self.cover:Path(self.cover).unlink(missing_ok=True)
        self.cover='';self.show_cover(self.original_cover);self.undo_cover_button.configure(state='disabled');self.crop_cover_button.configure(state='disabled')
    def pick_cover(self):
        if self.busy:return
        path=filedialog.askopenfilename(parent=self.winfo_toplevel(),filetypes=[(tr('Capas'),'*.png *.jpg *.jpeg')])
        if not path:return
        try:
            from review import local_cover
            import base64,uuid
            data=local_cover(path)[0]
            destination=Path(self.cover_temp.name)/(uuid.uuid4().hex+Path(path).suffix.lower())
            destination.write_bytes(data)
            self.show_cover(base64.b64encode(data))
            if self.cover:Path(self.cover).unlink(missing_ok=True)
            self.cover=str(destination)
            self.undo_cover_button.configure(state='normal');self.crop_cover_button.configure(state='normal')
        except Exception as error:messagebox.showerror(tr('Escolher outra capa'),tr(str(error)),parent=self.winfo_toplevel())
    def adjust_cover(self):
        if self.busy or not self.cover:return
        try:
            from cover_crop_ui import CoverCropper
            import uuid
            destination=Path(self.cover_temp.name)/(uuid.uuid4().hex+'.png')
            def accepted(cropped):
                import base64
                if self.cover:Path(self.cover).unlink(missing_ok=True)
                self.cover=cropped;self.show_cover(base64.b64encode(Path(cropped).read_bytes()))
                self.undo_cover_button.configure(state='normal')
            CoverCropper(self,self.cover,destination,accepted)
        except Exception as error:messagebox.showerror(tr('Ajustar capa'),tr(str(error)),parent=self.winfo_toplevel())
    def pick_lyrics(self):
        self.lyrics=filedialog.askopenfilename(parent=self.winfo_toplevel(),filetypes=[(tr('Letras'),'*.lrc *.txt')]) or self.lyrics
        if self.lyrics:self.lyrics_label.set(Path(self.lyrics).name)
    def run(self,preview):
        if self.busy:return
        self.busy=True;self.status.set('Preparando prévia…' if preview else 'Salvando no original…' if self.overwrite.get() else 'Salvando cópia…')
        self.player.stop()
        changes={k:v.get() for k,v in self.fields.items()};changes['artists']=[s.strip() for s in changes['artists'].split(';') if s.strip()]
        config={'source':str(self.source),'folder':str(self.source.parent),'ffmpeg':self.app.ffmpeg.get(),'edit_metadata':self.edit.get(),'changes':changes,'cover_path':self.cover,'lyrics_path':self.lyrics,'normalize_volume':self.normalize.get(),'overwrite_original':self.overwrite.get()}
        def worker():
            try:
                from audio_library import normalize_audio,edit_copy
                result={'preview':str(normalize_audio(self.source,config,preview=True))} if preview else edit_copy(config)
                self.results.put(result)
            except Exception as error:self.results.put({'error':str(error)})
        threading.Thread(target=worker,daemon=True).start()
    def poll(self):
        if self.closed:return
        try:
            result=self.results.get_nowait();self.busy=False
            if result.get('error'):self.status.set(result['error'])
            elif result.get('preview'):
                self.preview_path=Path(result['preview']);self.player.play(self.preview_path,self.app.ffmpeg.get(),duration=20);self.status.set('Prévia normalizada · 20 segundos')
            else:
                if result.get('overwritten'):
                    self.app.history_page.refresh()
                    from audio_library import cover_preview
                    self.original_cover=cover_preview(self.source);self.cover='';self.show_cover(self.original_cover)
                    self.crop_cover_button.configure(state='disabled')
                    self.undo_cover_button.configure(state='disabled')
                else:self.app.record_history(result['path'],result['mode'].upper(),'')
                self.status.set('Salvo: '+result['path'])
        except queue.Empty:pass
        self._poll=self.after(100,self.poll)
    def stop_preview(self):
        self.player.stop()
    def shutdown(self):
        if self.closed:return
        self.closed=True;self.player.stop()
        if self.preview_path:self.preview_path.unlink(missing_ok=True)
        self.cover_temp.cleanup()
        if self._poll:self.after_cancel(self._poll);self._poll=None
