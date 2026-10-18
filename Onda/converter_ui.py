"""Video conversion runs off Tk's thread with bounded process cancellation."""
from pathlib import Path
import os
import queue
import threading
import tkinter as tk
from tkinter import ttk,filedialog
from i18n import tr
from i18n_tk import TranslatedCombobox
from video_converter import FORMATS,QUALITIES,RESOLUTIONS,convert_video,ConversionCancelled,VIDEO_BITRATES,AUDIO_BITRATES,FRAME_RATES,AUDIO_MODES,AUDIO_FORMATS,OUTPUT_FORMATS

class ConverterPane(ttk.Frame):
    def __init__(self,parent,app):
        super().__init__(parent,padding=16)
        self.app=app;self.busy=False;self.closed=False;self.cancelled=threading.Event();self.events=queue.Queue();self.thread=None
        self.source=tk.StringVar();self.format=tk.StringVar(value='MP4');self.quality=tk.StringVar(value='Equilibrada');self.resolution=tk.StringVar(value='Original')
        self.status=tk.StringVar(value=tr('Escolha um vídeo para converter.'))
        ttk.Label(self,text=tr('Conversor de vídeos'),font=('Segoe UI',20,'bold')).pack(anchor='w',pady=(0,8))
        ttk.Label(self,text=tr('Converta vídeos locais sem alterar o arquivo original.'),style='Muted.TLabel').pack(anchor='w',pady=(0,12))
        ttk.Entry(self,textvariable=self.source,state='readonly').pack(fill='x')
        self.choose_button=ttk.Button(self,text=tr('Escolher vídeo'),command=self.choose);self.choose_button.pack(anchor='w',pady=8)
        self.preview_button=ttk.Button(self,text=tr('Prévia do original'),command=self.preview);self.preview_button.pack(anchor='w',pady=(0,8))
        self.bitrate=tk.StringVar(value='Automático');self.audio_bitrate=tk.StringVar(value='192k');self.fps=tk.StringVar(value='Original');self.audio=tk.StringVar(value='Manter áudio')
        self.options=[];self.option_cells=[]
        self.options_grid=ttk.Frame(self);self.options_grid.pack(fill="x",pady=(0,6))
        self.options_grid.bind("<Configure>",self.layout_options)
        for label,var,values in (('Formato',self.format,OUTPUT_FORMATS),('Qualidade',self.quality,QUALITIES),('Resolução máxima',self.resolution,RESOLUTIONS),('Bitrate de vídeo',self.bitrate,VIDEO_BITRATES),('Bitrate de áudio',self.audio_bitrate,AUDIO_BITRATES),('Quadros por segundo (FPS)',self.fps,FRAME_RATES),('Áudio',self.audio,AUDIO_MODES)):
            cell=ttk.Frame(self.options_grid);self.option_cells.append(cell)
            caption=ttk.Label(cell,text=tr(label));caption.pack(anchor='w')
            if var is self.audio_bitrate:self.audio_caption=caption
            combo=TranslatedCombobox(cell,textvariable=var,values=values,state='readonly',width=20);combo.pack(fill='x',pady=(4,0));self.options.append(combo)
        self.format.trace_add("write",lambda *_:self.layout_options())
        self.layout_options()
        self.video_help=[]
        help_label=ttk.Label(self,text=tr('Bitrate automático usa a qualidade escolhida; bitrate fixo usa a taxa selecionada.'),wraplength=650)
        help_label.pack(anchor='w',pady=6)
        self.video_help.append(help_label)
        help_label=ttk.Label(self,text=tr('H.264 e AAC. Preserva a proporção e não amplia o vídeo.'),style='Muted.TLabel',wraplength=650)
        help_label.pack(anchor='w',pady=6)
        self.video_help.append(help_label)
        help_label=ttk.Label(self,text=tr('Exporta o vídeo e a primeira faixa de áudio; legendas e outras faixas não são incluídas.'),style='Muted.TLabel',wraplength=650)
        help_label.pack(anchor='w')
        self.video_help.append(help_label)
        row=ttk.Frame(self);row.pack(fill='x',pady=12)
        self.start_button=ttk.Button(row,text=tr('Converter vídeo'),style='Accent.TButton',command=self.start);self.start_button.pack(side='left')
        self.cancel_button=ttk.Button(row,text=tr('Cancelar'),command=self.cancel,state='disabled');self.cancel_button.pack(side='left',padx=8)
        self.progress=ttk.Progressbar(self,maximum=100);self.progress.pack(fill='x',pady=8)
        ttk.Label(self,textvariable=self.status,wraplength=680).pack(anchor='w')
        self.timer=self.after(100,self.poll)
    def layout_options(self,event=None):
        self.audio_caption.configure(text=tr('Qualidade do áudio (kbps)' if self.format.get() in AUDIO_FORMATS else 'Bitrate de áudio'))
        for label in getattr(self,'video_help',[]):
            if self.format.get() in AUDIO_FORMATS:label.pack_forget()
            elif not label.winfo_manager():label.pack(anchor='w',pady=6,before=self.start_button.master)
        width=event.width if event else 900
        columns=3 if width>=650 else 2 if width>=420 else 1
        for index in range(3):self.options_grid.columnconfigure(index,weight=1 if index<columns else 0)
        cells=[self.option_cells[i] for i in (0,4)] if self.format.get() in AUDIO_FORMATS else self.option_cells
        for cell in self.option_cells:cell.grid_remove()
        for index,cell in enumerate(cells):
            cell.grid(row=index//columns,column=index%columns,sticky='ew',padx=(0,12 if index%columns<columns-1 else 0),pady=(0,12))
    def choose(self):
        value=filedialog.askopenfilename(parent=self.app,title=tr('Escolher vídeo'),filetypes=[(tr('Vídeo'),'*.mp4 *.mkv *.mov *.avi *.webm *.m4v *.mpeg *.mpg *.ts *.mts *.m2ts *.3gp *.flv *.wmv')])
        if value:self.source.set(value)
    def preview(self):
        if not Path(self.source.get()).is_file():self.status.set(tr('Escolha um vídeo para converter.'));return
        try:os.startfile(str(Path(self.source.get()).resolve()))
        except OSError:self.status.set(tr('Não foi possível abrir o vídeo no aplicativo padrão.'))
    def start(self):
        if self.busy:return
        source=Path(self.source.get())
        if not source.is_file():self.status.set(tr('Escolha um vídeo para converter.'));return
        mode=self.format.get();target=filedialog.asksaveasfilename(parent=self.app,title=tr('Salvar vídeo convertido'),initialdir=self.app.folder.get(),initialfile=source.stem+' - convertido.'+mode.lower(),defaultextension='.'+mode.lower(),filetypes=[(mode,'*.'+mode.lower())])
        if not target:return
        config={'source':str(source),'output':target,'ffmpeg':self.app.ffmpeg.get(),'video_format':mode,'video_quality':self.quality.get(),'video_resolution':self.resolution.get(),'video_bitrate':self.bitrate.get(),'audio_bitrate':self.audio_bitrate.get(),'video_fps':self.fps.get(),'video_audio':self.audio.get()}
        from performance import snapshot
        config.update(snapshot(self.app))
        self.busy=True;self.cancelled.clear();self.progress['value']=0;self.status.set(tr('Convertendo vídeo…'));self.choose_button.configure(state='disabled');self.start_button.configure(state='disabled');self.cancel_button.configure(state='normal')
        for combo in self.options:combo.configure(state='disabled')
        def work():
            try:
                result=convert_video(config,lambda kind,**data:self.events.put((kind,data)),self.cancelled.is_set)
                self.events.put(('finished',result))
            except ConversionCancelled:self.events.put(('error',{'message':'Conversão cancelada.'}))
            except Exception as error:self.events.put(('error',{'message':str(error)}))
        self.thread=threading.Thread(target=work,daemon=True);self.thread.start()
    def poll(self):
        while not self.events.empty():
            kind,data=self.events.get()
            if kind=='progress':self.progress['value']=data['percent']
            elif kind=='stage':self.status.set(tr(data['message']))
            else:
                self.busy=False;self.choose_button.configure(state='normal');self.start_button.configure(state='normal');self.cancel_button.configure(state='disabled')
                for combo in self.options:combo.configure(state='readonly')
                self.status.set(tr('Vídeo convertido: {path}').replace('{path}',data['path']) if kind=='finished' else tr(data['message']))
        if not self.closed:self.timer=self.after(100,self.poll)
    def cancel(self):self.cancelled.set()
    def shutdown(self):
        self.closed=True;self.cancel()
        if self.timer:self.after_cancel(self.timer);self.timer=None
