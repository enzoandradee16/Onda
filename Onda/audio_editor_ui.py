"""Inline local audio editor, shared by the tab and history."""
from i18n import tr
from tkinter import ttk, filedialog, messagebox

class MetadataPane(ttk.Frame):
    def __init__(self,parent,app):
        super().__init__(parent)
        self.app=app;self.editor=None;self.batch_editor=None
        self.welcome=ttk.Frame(self,padding=(16,20));self.welcome.pack(fill="both",expand=True)
        ttk.Label(self.welcome,text=tr("Edite os metadados da sua música."),font=("Segoe UI",21,"bold"),anchor="center").pack(fill="x")
        ttk.Label(self.welcome,text=tr("Escolha um arquivo de áudio do computador, mesmo que não esteja no histórico."),anchor="center",style="Muted.TLabel",wraplength=700).pack(fill="x",pady=10)
        ttk.Button(self.welcome,text=tr("Escolher arquivo de áudio"),command=self.choose,style="Accent.TButton").pack(pady=16)
        ttk.Label(self.welcome,text=tr("MP3, M4A, FLAC, WAV, OGG e OPUS. Edite música, artistas, álbum, gênero, data, capa e letra."),wraplength=700,anchor="center").pack(fill="x")
        ttk.Label(self.welcome,text=tr("Salve uma cópia ou ative Sobrescrever arquivo original."),anchor="center",style="Muted.TLabel").pack(fill="x",pady=10)
        ttk.Button(self.welcome,text=tr("Editar metadados em lote"),command=self.open_batch).pack(pady=8)
    def open_batch(self, sources=()):
        if self.busy:return
        from batch_metadata_ui import BatchMetadataEditor
        if self.batch_editor is not None and self.batch_editor.winfo_exists():
            self.batch_editor.lift();return
        self.batch_editor=BatchMetadataEditor(self,self.app,sources)
    @property
    def busy(self):return bool((self.editor is not None and self.editor.busy) or (self.batch_editor is not None and self.batch_editor.winfo_exists() and self.batch_editor.busy))
    def choose(self):
        if self.busy:
            self.editor.status.set("Aguarde o processamento terminar antes de escolher outro arquivo.");return
        path=filedialog.askopenfilename(parent=self.app,title=tr("Escolher arquivo de áudio"),filetypes=[(tr("Áudio"),"*.mp3 *.m4a *.flac *.wav *.ogg *.opus"),(tr("Todos os arquivos"),"*.*")])
        if path:
            try:self.open_file(path)
            except Exception as error:messagebox.showerror(tr("Editar metadados"),tr(str(error)),parent=self.app)
    def open_file(self,path):
        if self.busy:
            self.editor.status.set("Aguarde o processamento terminar antes de escolher outro arquivo.");return False
        from advanced_ui import AudioEditor
        editor=AudioEditor(self,self.app,path,self.choose)
        if self.editor is not None:
            self.editor.shutdown();self.editor.destroy()
        self.welcome.pack_forget();self.editor=editor
        editor.pack(fill="both",expand=True)
        if hasattr(self.app,"theme_manager"):self.app.theme_manager.walk(editor)
        self.after_idle(lambda:self.app.metadata_page._scroller.canvas.yview_moveto(0))
        return True
    def stop_preview(self):
        if self.editor is not None:self.editor.stop_preview()
    def shutdown(self):
        if self.editor is not None:self.editor.shutdown()
