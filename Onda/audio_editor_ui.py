"""Local file selection independent of download history."""
from tkinter import ttk, filedialog, messagebox

class MetadataPane(ttk.Frame):
    def __init__(self,parent,app):
        super().__init__(parent,padding=(16,20))
        self.app=app
        self.editor=None
        ttk.Label(self,text="Edite os metadados da sua música.",font=("Segoe UI",21,"bold"),anchor="center").pack(fill="x")
        ttk.Label(self,text="Escolha um arquivo de áudio do computador, mesmo que não esteja no histórico.",anchor="center",style="Muted.TLabel").pack(fill="x",pady=10)
        ttk.Button(self,text="Escolher arquivo de áudio",command=self.choose,style="Accent.TButton").pack(pady=16)
        ttk.Label(self,text="MP3, M4A, FLAC, WAV, OGG e OPUS. Edite música, artistas, álbum, gênero, data, capa e letra.",wraplength=700,anchor="center").pack(fill="x")
        ttk.Label(self,text="Salve uma cópia ou ative Sobrescrever arquivo original.",anchor="center",style="Muted.TLabel").pack(fill="x",pady=10)
    def choose(self):
        if self.editor is not None and self.editor.winfo_exists():
            self.editor.lift();return
        path=filedialog.askopenfilename(parent=self.app,title="Escolher arquivo de áudio",filetypes=[("Áudio","*.mp3 *.m4a *.flac *.wav *.ogg *.opus"),("Todos os arquivos","*.*")])
        if not path:return
        try:
            from advanced_ui import AudioEditor
            self.editor=AudioEditor(self.app,path)
        except Exception as error:messagebox.showerror("Editar metadados",str(error),parent=self.app)
