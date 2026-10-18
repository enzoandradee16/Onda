"""Validate dropped media and links before handing them to existing workflows."""
from pathlib import Path
from clipboard_links import recognize_link
from video_converter import VIDEO_EXTENSIONS,AUDIO_INPUT_EXTENSIONS
from audio_library import AUDIO_TYPES

def dropped_files(paths):
    if len(paths)>1000:return []
    return list(dict.fromkeys(str(Path(path).resolve()) for path in paths if Path(path).is_file() and Path(path).suffix.lower() in VIDEO_EXTENSIONS|AUDIO_INPUT_EXTENSIONS))

def dropped_links(text):
    if len(text)>1024*1024:return []
    result={}
    for line in text.splitlines():
        candidate=recognize_link(line)
        if candidate:result[candidate['key']]=candidate['url']
        if len(result)>=1000:break
    return list(result.values())

def receive(app,payload):
    import tkinter as tk
    from tkinter import ttk,messagebox
    from i18n import tr
    if app.grab_current() is not None:return
    links=dropped_links(payload.get('text',''))
    if links:
        if messagebox.askyesno(tr('Adicionar à fila'),tr('Adicionar os links recebidos à fila?')+'\n\n'+'\n'.join(links[:10]),parent=app):
            app.add(lines=links);app.show_queue()
        return
    files=dropped_files(payload.get('files',[]))
    if not files:
        app.status.set(tr('Nenhum arquivo ou link compatível.'));return
    if app.converter_page.busy or app.metadata_page.busy or app.effects_page.busy:
        app.status.set(tr('Aguarde o processamento terminar antes de escolher outro arquivo.'));return
    window=tk.Toplevel(app);window.title(tr('Abrir arquivos no ONDA'));window.transient(app)
    body=ttk.Frame(window,padding=16);body.pack(fill='both',expand=True)
    ttk.Label(body,text=str(len(files))+' · '+tr('Arquivos selecionados')).pack(anchor='w',pady=8)
    action=tk.StringVar(value='converter')
    choices=[('converter','Conversor')]
    if all(Path(path).suffix.lower() in AUDIO_TYPES for path in files):
        choices.append(('metadata','Editar metadados'))
        if len(files)==1:choices.append(('effects','Slowed / Sped Up'))
    for value,label in choices:ttk.Radiobutton(body,text=tr(label),value=value,variable=action).pack(anchor='w',pady=4)
    def accept():
        selected=action.get();window.destroy()
        if selected=='converter':
            pane=app.converter_page.ensure_ready();pane.set_sources(files)
            if Path(files[0]).suffix.lower() in AUDIO_INPUT_EXTENSIONS:pane.format.set('MP3')
            app.pages.select(app.converter_page)
        elif selected=='metadata':
            pane=app.metadata_page.ensure_ready();app.pages.select(app.metadata_page)
            if len(files)==1:pane.open_file(files[0])
            else:pane.open_batch(files)
        else:
            app.effects_page.ensure_ready().use_file(files[0]);app.pages.select(app.effects_page)
    ttk.Button(body,text=tr('Abrir'),command=accept).pack(side='left',pady=12)
    ttk.Button(body,text=tr('Cancelar'),command=window.destroy).pack(side='left',padx=8)
    window.grab_set()
