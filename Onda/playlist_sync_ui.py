"""Collection comparison controls using the existing playlist list and queue."""

import threading
from tkinter import ttk, filedialog
from i18n import tr

STATES = {
    'present': 'Presente',
    'missing': 'Ausente',
    'review': 'Revisar',
    'queued': 'Na fila',
}


def controls(pane, parent):
    row = ttk.Frame(parent)
    row.pack(fill='x', pady=(8, 0))
    pane.sync_result = None
    pane.sync_detail = ttk.Label(parent, wraplength=790, style="Muted.TLabel")
    pane.sync_buttons = []
    for label, callback in (
        ('Conferir arquivos locais', lambda: choose(pane)),
        ('Atualizar playlist baixada', lambda: choose(pane, True)),
        ('Adicionar ausentes à fila', lambda: add_missing(pane)),
    ):
        button = ttk.Button(row, text=tr(label), command=callback)
        button.pack(side='left', padx=(0, 8))
        pane.sync_buttons.append(button)


def choose(pane, reload=False):
    if pane.busy:
        return
    if reload and not pane.url.get().strip():
        pane.status.set('Informe o link da playlist para atualizar.')
        return
    if not reload and not pane.records:
        pane.status.set('Carregue um álbum ou playlist')
        return
    folder = filedialog.askdirectory(
        parent=pane.app,
        initialdir=pane.app.folder.get(),
        title=tr('Pasta para conferir os arquivos'),
    )
    if not folder:
        return
    if reload:
        pane.load(sync_folder=folder)
    else:
        start(pane, folder)


def start(pane, folder):
    if pane.closed:
        return
    from playlist_sync import scan_folder, compare_collection

    pane.sync_result = None
    tracks = list(pane.records.values())
    jobs = [dict(job) for job in pane.app.jobs.values()]
    source = getattr(pane, 'collection_url', '')
    generation = pane.generation
    pane.set_busy(True)
    pane.status.set('Conferindo arquivos locais…')

    def worker():
        try:
            inventory = scan_folder(
                folder,
                pane.app.library.comparison_history(),
                cancelled=lambda: pane.closed or generation != pane.generation,
            )
            result = compare_collection(
                tracks, inventory, jobs, source, pane.app.library.path
            )
            pane.events.put((generation, 'local_comparison', result))
        except Exception as error:
            pane.events.put((generation, 'error', str(error)))

    threading.Thread(target=worker, daemon=True).start()


def show(pane, result):
    pane.sync_result = result
    pane.filter_text.set('')
    pane.filter_records()
    missing = []
    for row in result['items']:
        key = str(row['index'])
        if not pane.table.exists(key):
            continue
        detail = tr(STATES[row['state']]) + ' · ' + tr(row['reason'])
        if row['paths']:
            detail += ' · ' + str(row['paths'][0])
        pane.table.set(key, 'match', detail)
        if row['state'] == 'missing':
            missing.append(key)
    if not getattr(pane, '_sync_detail_bound', False):
        pane.table.bind('<<TreeviewSelect>>', lambda _: show_detail(pane), add='+')
        pane._sync_detail_bound = True
    pane.table.selection_set(missing)
    pane.sync_detail.pack(fill='x', pady=(6, 0))
    show_detail(pane)
    c = result['counts']
    text = tr(
        'Presentes: {present} · Ausentes: {missing} · Revisar: {review} · Na fila: {queued}'
    ).format(**c)
    if result['has_previous']:
        text += ' · ' + tr('Novas na coleção: {count}').format(
            count=result['new_count']
        )
    pane.status.set(text)
    pane.set_busy(False)


def show_detail(pane):
    selected = pane.table.selection()
    rows = {str(row['index']): row for row in (pane.sync_result or {}).get('items', [])}
    row = rows.get(selected[0]) if selected else None
    text = tr(row['reason']) if row else ''
    if row and row['paths']:
        text += ' · ' + ' · '.join(row['paths'])
    pane.sync_detail.configure(text=text)


def add_missing(pane):
    if pane.busy or not pane.sync_result:
        return
    missing = [
        str(row['index'])
        for row in pane.sync_result['items']
        if row['state'] == 'missing'
    ]
    pane.filter_text.set('')
    pane.filter_records()
    pane.table.selection_set([key for key in missing if pane.table.exists(key)])
    if missing:
        pane.add()
        pane.sync_result = None
        pane.sync_detail.pack_forget()
        pane.set_busy(False)
