"""Inline local audio editor, shared by the tab and history."""
from tkinter import ttk, filedialog, messagebox

class MetadataPane(ttk.Frame):
    def __init__(self,parent,app):
        super().__init__(parent)
        self.app=app;self.editor=None
        self.welcome=ttk.Frame(self,padding=(16,20));self.welcome.pack(fill="both",expand=True)
        ttk.Label(self.welcome,text="Edite os metadados da sua música.",font=("Segoe UI",21,"bold"),anchor="center").pack(fill="x")
        ttk.Label(self.welcome,text="Escolha um arquivo de áudio do computador, mesmo que não esteja no histórico.",anchor="center",style="Muted.TLabel",wraplength=700).pack(fill="x",pady=10)
        ttk.Button(self.welcome,text="Escolher arquivo de áudio",command=self.choose,style="Accent.TButton").pack(pady=16)
        ttk.Label(self.welcome,text="MP3, M4A, FLAC, WAV, OGG e OPUS. Edite música, artistas, álbum, gênero, data, capa e letra.",wraplength=700,anchor="center").pack(fill="x")
        ttk.Label(self.welcome,text="Salve uma cópia ou ative Sobrescrever arquivo original.",anchor="center",style="Muted.TLabel").pack(fill="x",pady=10)
    @property
    def busy(self):return bool(self.editor is not None and self.editor.busy)
    def choose(self):
        if self.busy:
            self.editor.status.set("Aguarde o processamento terminar antes de escolher outro arquivo.");return
        path=filedialog.askopenfilename(parent=self.app,title="Escolher arquivo de áudio",filetypes=[("Áudio","*.mp3 *.m4a *.flac *.wav *.ogg *.opus"),("Todos os arquivos","*.*")])
        if path:
            try:self.open_file(path)
            except Exception as error:messagebox.showerror("Editar metadados",str(error),parent=self.app)
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
