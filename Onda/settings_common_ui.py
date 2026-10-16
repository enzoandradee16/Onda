from tkinter import ttk
from i18n import tr
from i18n_tk import TranslatedCombobox

def format_controls(app,parent):
    from engine import MODES,HEIGHTS,FPS_OPTIONS,MP3_QUALITIES,M4A_QUALITIES
    frame=ttk.Frame(parent);frame.pack(fill='x',pady=(0,12))
    ttk.Label(frame,text=tr('Formato')).pack(anchor='w')
    combo=TranslatedCombobox(frame,textvariable=app.mode,values=tuple(MODES),state='readonly');combo.pack(fill='x',pady=(4,8))
    options=ttk.Frame(frame);options.pack(fill='x')
    def refresh(*_):
        for child in options.winfo_children():child.destroy()
        mode=MODES[app.mode.get()]
        fields=[]
        if mode=='mp3':fields=[('Qualidade de áudio',app.mp3_quality,MP3_QUALITIES)]
        elif mode=='m4a':fields=[('Qualidade de áudio',app.m4a_quality,M4A_QUALITIES)]
        elif mode in ('video','mp4','social'):fields=[('Resolução máxima',app.height,HEIGHTS),('FPS máximo',app.fps,FPS_OPTIONS)]
        for label,var,values in fields:
            ttk.Label(options,text=tr(label)).pack(anchor='w')
            TranslatedCombobox(options,textvariable=var,values=tuple(values),state='readonly').pack(fill='x',pady=(4,8))
    trace=app.mode.trace_add('write',refresh)
    frame.bind('<Destroy>',lambda e:app.mode.trace_remove('write',trace) if e.widget is frame else None)
    refresh()

def image_controls(app,parent):
    from image_output import FORMATS,IMAGE_SIZES
    for label,var,values in (('Formato',app.image_format,FORMATS),('Tamanho máximo',app.image_size,IMAGE_SIZES)):
        ttk.Label(parent,text=tr(label)).pack(anchor='w')
        TranslatedCombobox(parent,textvariable=var,values=tuple(values),state='readonly').pack(fill='x',pady=(4,10))
    custom=ttk.Frame(parent)
    ttk.Label(custom,text=tr('Largura × altura (px)')).pack(anchor='w')
    row=ttk.Frame(custom);row.pack(fill='x',pady=(4,8))
    for label,var in (('Largura',app.image_width),('Altura',app.image_height)):
        ttk.Label(row,text=tr(label)).pack(side='left',padx=(0,4));ttk.Entry(row,textvariable=var,width=10).pack(side='left',padx=(0,12))
    keep=ttk.Checkbutton(parent,text=tr('Manter proporção (sem ampliar ou distorcer)'),variable=app.image_keep_ratio);keep.pack(anchor='w')
    def refresh(*_):
        if app.image_size.get()=='Personalizado':custom.pack(fill='x',before=keep)
        else:custom.pack_forget()
    trace=app.image_size.trace_add('write',refresh)
    custom.bind('<Destroy>',lambda e:app.image_size.trace_remove('write',trace) if e.widget is custom else None)
    refresh()


def tab_order_controls(app,parent):
    ttk.Label(parent,text=tr('Ordem das abas'),font=('Segoe UI',12,'bold')).pack(anchor='w',pady=(12,6))
    tree=ttk.Treeview(parent,columns=('name',),show='headings',height=5,selectmode='browse');tree.heading('name',text=tr('Ordem das abas'));tree.pack(fill='x')
    def refresh(*_):
        selected=tree.selection();tree.delete(*tree.get_children())
        for key in app.tab_order.get():
            page=app.tab_reorder.pages[key]
            tree.insert('', 'end',iid=key,values=(app.pages.tab(str(page),'text'),))
        if selected and tree.exists(selected[0]):tree.selection_set(selected)
    def move(direction):
        selected=tree.selection()
        if not selected:return
        order=list(app.tab_order.get());index=order.index(selected[0]);target=index+direction
        if 0<=target<len(order):
            order[index],order[target]=order[target],order[index]
            app.tab_reorder.apply(order);app.tab_order.set(tuple(order));tree.see(selected[0])
    row=ttk.Frame(parent);row.pack(fill='x',pady=4)
    ttk.Button(row,text=tr('Mover para cima'),command=lambda:move(-1)).pack(side='left')
    ttk.Button(row,text=tr('Mover para baixo'),command=lambda:move(1)).pack(side='left',padx=6)
    ttk.Button(row,text=tr('Restaurar ordem das abas'),command=app.tab_reorder.reset).pack(side='left')
    trace=app.tab_order.trace_add('write',refresh)
    tree.bind('<Destroy>',lambda e:app.tab_order.trace_remove('write',trace) if e.widget is tree else None)
    refresh()

def account_controls(app,parent):
    import webbrowser
    from tkinter import filedialog
    from i18n_tk import display_var
    for label,var,secret in (('Client ID',app.spotify_client_id,False),('Client Secret · opcional',app.spotify_client_secret,True)):
        ttk.Label(parent,text=tr(label)).pack(anchor='w')
        ttk.Entry(parent,textvariable=var,show='•' if secret else '').pack(fill='x',pady=(4,8))
    ttk.Button(parent,text=tr('Salvar neste computador'),command=app.save_spotify_credentials).pack(anchor='w')
    ttk.Button(parent,text=tr('Esquecer credenciais'),command=app.forget_spotify_credentials).pack(anchor='w',pady=4)
    ttk.Label(parent,textvariable=display_var(app.credential_status),style='Muted.TLabel',wraplength=480).pack(anchor='w')
    ttk.Button(parent,text=tr('Conectar'),command=lambda:app.playlist_page.connect_spotify()).pack(anchor='w',pady=6)
    ttk.Button(parent,text=tr('Abrir Spotify Developers'),command=lambda:webbrowser.open('https://developer.spotify.com/dashboard')).pack(anchor='w')
    def disconnect():
        app.spotify_account.disconnect()
        page=app.playlist_page._content
        if page is not None:page.spotify_button.configure(text=tr('Conectar Spotify'))
    ttk.Button(parent,text=tr('Desconectar'),command=disconnect).pack(anchor='w',pady=6)
    def choose(variable):
        path=filedialog.askopenfilename(parent=app.settings_window,title=tr('Cookies no formato Netscape'),filetypes=[('Cookies','*.txt')])
        if path:variable.set(path)
    ttk.Separator(parent).pack(fill='x',pady=12)
    ttk.Button(parent,text=tr('Importar cookies do YouTube'),command=lambda:choose(app.youtube_cookies)).pack(anchor='w')
    ttk.Button(parent,text=tr('Importar cookies.txt'),command=lambda:choose(app.social_cookies)).pack(anchor='w',pady=6)
    ttk.Button(parent,text=tr('Remover cookies'),command=lambda:app.social_cookies.set('')).pack(anchor='w')
    ttk.Button(parent,text=tr('Remover sessão do YouTube'),command=lambda:app.youtube_cookies.set('')).pack(anchor='w',pady=6)
    ttk.Label(parent,text=tr('No PC, os arquivos de cookies são usados apenas nesta sessão.'),style='Muted.TLabel',wraplength=480).pack(anchor='w')

def verify_tools(app,parent):
    import queue,threading,subprocess
    events=queue.Queue()
    button=ttk.Button(parent,text=tr('Verificar ferramentas'));button.pack(anchor='w',pady=8)
    def run():
        button.configure(state='disabled')
        folder=app.ffmpeg.get()
        def worker():
            from audio_tools import executable,process_options
            try:
                for name in ('ffmpeg','ffprobe'):
                    subprocess.run([executable(name,folder),'-version'],check=True,capture_output=True,timeout=15,**process_options())
                events.put('Ferramentas verificadas.')
            except Exception:events.put('Não foi possível verificar as ferramentas. Confira a configuração do FFmpeg.')
        threading.Thread(target=worker,daemon=True).start()
        def poll():
            try:message=events.get_nowait()
            except queue.Empty:
                if button.winfo_exists():button.after(100,poll)
                return
            if button.winfo_exists():button.configure(state='normal');app.update_status.set(message)
        button.after(100,poll)
    button.configure(command=run)
