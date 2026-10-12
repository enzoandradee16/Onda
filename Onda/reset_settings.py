"""Reviewable, selective preference resets; user data and accounts stay intact."""
import tkinter as tk
from tkinter import ttk, messagebox

GROUPS = {
    'Aparência': {'theme_mode':'Modo claro, escuro ou sistema', 'theme_accent':'Cor de destaque'},
    'Geral': {'tab_order':'Ordem das abas', 'remember_settings':'Lembrar configurações'},
    'Downloads': {'folder':'Pasta de destino', 'organization':'Organização por pastas', 'duplicates':'Tratamento de arquivos duplicados', 'review_metadata':'Revisão de metadados', 'auto_match':'Escolha automática da versão', 'playlist_limit':'Limite de itens de playlists'},
    'Links e fila': {'mode':'Formato', 'height':'Resolução máxima', 'fps':'FPS máximo', 'mp3_quality':'Qualidade MP3', 'm4a_quality':'Qualidade M4A', 'playlist':'Baixar playlist de vídeo'},
    'Playlists': {'playlist_mode':'Formato da playlist', 'playlist_height':'Resolução da playlist', 'playlist_fps':'FPS da playlist', 'playlist_mp3_quality':'Qualidade MP3 da playlist', 'playlist_m4a_quality':'Qualidade M4A da playlist'},
    'Imagens': {'image_format':'Formato da imagem', 'image_size':'Tamanho máximo', 'image_width':'Largura personalizada', 'image_height':'Altura personalizada', 'image_keep_ratio':'Manter proporção'},
    'Áudio': {'effects_keep_pitch':'Manter tom nos efeitos', 'background_preview':'Continuar prévia em outras abas', 'effects_preview_duration':'Duração da prévia dos efeitos', 'search_preview_duration':'Duração da prévia nas pesquisas'},
    'Catálogo': {'catalog_provider':'Plataforma de pesquisa de músicas'},
    'Ferramentas e sessão': {'ffmpeg':'Pasta do FFmpeg', 'social_cookies':'Arquivo de cookies desta sessão'},
}


def apply_defaults(app, names):
    names=set(names)
    known=set(app.preference_defaults)|{'remember_settings','social_cookies'}
    if names-known:
        raise ValueError('Configuração desconhecida.')
    # Avoid writing intermediate combinations while resetting several fields.
    remembering=app.remember_settings.get()
    app.remember_settings.set(False)
    if app._preference_after is not None:
        app.after_cancel(app._preference_after)
        app._preference_after=None
    try:
        for name in names & set(app.preference_defaults):
            app.preference_fields[name].set(app.preference_defaults[name])
        if 'tab_order' in names:
            app.tab_reorder.cancel()
            app.tab_reorder.apply(app.tab_order.get())
        if 'social_cookies' in names:
            app.social_cookies.set('')
        app.playlist_page.format_changed()
        if 'background_preview' in names:
            app.tab_changed()
    finally:
        app.remember_settings.set(False if 'remember_settings' in names else remembering)
    if 'remember_settings' in names:
        app.toggle_remember_settings()
    elif remembering:
        app.persist_preferences()


class ResetSettingsWindow(tk.Toplevel):
    def __init__(self, app, select_all=False):
        super().__init__(app)
        self.app=app
        self.title('Onda • Restaurar configurações')
        self.geometry('620x660')
        self.minsize(560,520)
        self.transient(app.settings_window)
        body=ttk.Frame(self,padding=18)
        body.pack(fill='both',expand=True)
        ttk.Label(body,text='Restaurar configurações',font=('Segoe UI',18,'bold')).pack(anchor='w')
        ttk.Label(body,text='Marque as opções que devem voltar ao padrão. As demais ficam como estão.',wraplength=520,style='Muted.TLabel').pack(anchor='w',pady=(6,8))
        ttk.Label(body,text='Contas conectadas, credenciais, fila, histórico e arquivos baixados são mantidos.',wraplength=520,style='Muted.TLabel').pack(anchor='w',pady=(0,12))
        tools=ttk.Frame(body)
        tools.pack(fill='x',pady=(0,8))
        ttk.Button(tools,text='Selecionar todas',command=lambda:self.select(True)).pack(side='left')
        ttk.Button(tools,text='Desmarcar todas',command=lambda:self.select(False)).pack(side='left',padx=8)
        bottom=ttk.Frame(body)
        bottom.pack(side='bottom',fill='x',pady=(12,0))
        ttk.Button(bottom,text='Cancelar',command=self.destroy).pack(side='right')
        self.apply_button=ttk.Button(bottom,text='Restaurar selecionadas',style='Accent.TButton',command=self.restore)
        self.apply_button.pack(side='right',padx=8)
        self.count=tk.StringVar()
        ttk.Label(bottom,textvariable=self.count,style='Muted.TLabel').pack(side='left')
        from settings_scroll import SettingsCategory
        from ui import BG
        scroller=SettingsCategory(body,BG)
        scroller.pack(fill='both',expand=True)
        self.bind('<MouseWheel>',scroller.wheel)
        self.choices={}
        for group,fields in GROUPS.items():
            ttk.Label(scroller.content,text=group,font=('Segoe UI',11,'bold')).pack(anchor='w',pady=(12,6))
            for name,label in fields.items():
                var=tk.BooleanVar(value=select_all)
                self.choices[name]=var
                ttk.Checkbutton(scroller.content,text=label,variable=var).pack(anchor='w',pady=3)
                if name == 'remember_settings':
                    ttk.Label(scroller.content,text='Restaurar esta opção desativa o salvamento e remove as preferências salvas.',style='Muted.TLabel',wraplength=450).pack(anchor='w',pady=(0,6))
                var.trace_add('write',self.refresh)
        self.refresh()
        self.bind('<Escape>',lambda _:self.destroy())

    def select(self,value):
        for var in self.choices.values():var.set(value)

    def refresh(self,*_):
        count=sum(var.get() for var in self.choices.values())
        self.count.set(f'{count} selecionadas')
        self.apply_button.configure(state='normal' if count else 'disabled')

    def restore(self):
        names=[name for name,var in self.choices.items() if var.get()]
        if not names:return
        if not messagebox.askyesno('Restaurar configurações',f'Restaurar {len(names)} configurações selecionadas ao padrão?',parent=self):return
        try:
            apply_defaults(self.app,names)
        except (ValueError,OSError) as exc:
            messagebox.showerror('Restaurar configurações',str(exc),parent=self)
            return
        self.app.preference_status.set('Configurações selecionadas restauradas ao padrão.' + (' Salvamento automático ativado.' if self.app.remember_settings.get() else ' Lembrar configurações está desativado.'))
        self.destroy()


def show_reset(app, select_all=False):
    window=getattr(app,'reset_settings_window',None)
    if window is not None and window.winfo_exists():
        window.select(select_all)
        window.lift()
        return window
    app.reset_settings_window=ResetSettingsWindow(app,select_all)
    return app.reset_settings_window
