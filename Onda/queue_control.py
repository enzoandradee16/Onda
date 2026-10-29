"""Queue-only ordering, live activity and conservative storage estimates."""

import math
from pathlib import Path
import shutil
import tkinter as tk
from tkinter import ttk, messagebox
from i18n import tr
from i18n_tk import TranslatedCombobox

ORDERS = (
    'Ordem original',
    'Título',
    'Menor duração',
    'Maior duração',
    'Menor tamanho estimado',
)


def positive(value):
    try:
        number = float(value)
        return number if math.isfinite(number) and number > 0 else None
    except (TypeError, ValueError):
        return None


def duration(job):
    info = job.get('catalog_record') or job.get('queue_info') or {}
    return (
        positive(info.get('duration_ms')) / 1000
        if positive(info.get('duration_ms'))
        else positive(info.get('duration'))
    )


def estimated_bytes(job):
    if job.get('playlist'):
        return None
    known = positive(job.get('_queue_estimate'))
    if known:
        return int(known)
    if job.get('mode') not in ('mp3', 'm4a'):
        return None
    from size_estimate import estimate_size

    try:
        return estimate_size({'duration': duration(job)}, job)[0]
    except (ValueError, KeyError, TypeError, OverflowError):
        return None


def sorted_keys(keys, jobs, order):
    if order == 'Ordem original':
        return sorted(keys, key=lambda key: jobs[key].get('queue_original', 0))
    if order == 'Título':
        return sorted(
            keys,
            key=lambda key: str(
                jobs[key].get('display_name') or jobs[key].get('url', '')
            ).casefold(),
        )
    measure = estimated_bytes if order == 'Menor tamanho estimado' else duration

    def value(key):
        size = measure(jobs[key])
        return (
            size is None,
            -size if size is not None and order == 'Maior duração' else size or 0,
        )

    return sorted(keys, key=value)


def replace_pending(keys, jobs, pending):
    iterator = iter(pending)
    return [
        next(iterator) if jobs[key].get('state') == 'Na fila' else key for key in keys
    ]


def storage_report(jobs, limit=1, *, check_space=True):
    groups = {}
    unknown = 0
    total = 0
    for job in jobs:
        size = estimated_bytes(job)
        if size is None:
            unknown += 1
            continue
        total += size
        folder = Path(job.get('folder') or '.').absolute()
        key = folder.anchor.casefold()
        group = groups.setdefault(key, {'folder': folder, 'sizes': []})
        group['sizes'].append(size)
    low = False
    required = 0
    for group in groups.values():
        need = sum(group['sizes']) + 2 * sum(
            sorted(group['sizes'], reverse=True)[: max(1, limit)]
        )
        required += need
        if not check_space:
            continue
        folder = group['folder']
        while not folder.exists() and folder.parent != folder:
            folder = folder.parent
        try:
            low = low or shutil.disk_usage(folder).free < need
        except OSError:
            pass
    return total, unknown, required, low


def summary(total, unknown, required):
    from app import readable_bytes

    return (
        tr(
            'Espaço estimado: {size} · Com temporários: {required} · Sem estimativa: {unknown}'
        )
        .replace('{size}', readable_bytes(total))
        .replace('{required}', readable_bytes(required))
        .replace('{unknown}', str(unknown))
    )


def activity(job, app):
    state = job.get('state', 'Na fila')
    if state == 'Na fila':
        from advanced_options import schedule_allowed

        options = {
            key: getattr(app, key).get()
            for key in ('schedule_enabled', 'schedule_start', 'schedule_stop')
        }
        if options['schedule_enabled'] and not schedule_allowed(options):
            return tr('Aguardando horário')
        if app.parallel.memory_wait is not None:
            return tr('Aguardando memória livre')
        return tr('Aguardando vaga' if app.running else 'Aguardando início')
    if state == 'Em andamento':
        return tr(job.get('_queue_activity') or 'Consultando a plataforma…')
    return tr(state)


def observe(app, key, event):
    job = app.jobs.get(key)
    if not job:
        return
    kind = event.get('type')
    if kind == 'estimate' and not event.get('playlist'):
        job['_queue_estimate'] = event.get('size')
    if kind == 'stage':
        job['_queue_activity'] = event.get('message', '')
    elif kind == 'done':
        job['_queue_activity'] = 'Finalizando arquivo…'
    elif kind == 'processing':
        job['_queue_activity'] = 'Convertendo arquivo…'
    elif kind == 'progress':
        job['_queue_percent'] = (
            min(100, event.get('downloaded', 0) / event['total'] * 100)
            if positive(event.get('total'))
            else 0
        )
        if event.get('status') == 'finished':
            job['_queue_activity'] = 'Preparando o arquivo…'
        else:
            percent = (
                event.get('downloaded', 0) / event['total'] * 100
                if positive(event.get('total'))
                else None
            )
            job['_queue_activity'] = tr('Baixando arquivo…') + (
                f' {min(100,percent):.0f}%' if percent is not None else ''
            )
    elif kind.startswith('choose_') or kind == 'review_metadata':
        job['_queue_activity'] = 'Aguardando sua escolha'
    if job.get('state') == 'Em andamento':
        app.tree.set(key, 'status', activity(job, app))


class QueueControl:
    def __init__(self, app, parent):
        self.app = app
        self.drag = None
        self.last_summary = 0
        self.statuses = {}
        self.order = tk.StringVar(value=ORDERS[0])
        self.space = tk.StringVar()
        row = ttk.Frame(parent)
        row.pack(fill='x', pady=6)
        ttk.Label(row, text=tr('Ordenar pendentes')).pack(side='left')
        TranslatedCombobox(
            row, textvariable=self.order, values=ORDERS, state='readonly', width=25
        ).pack(side='left', padx=8)
        ttk.Button(row, text=tr('Aplicar'), command=self.sort).pack(side='left')
        ttk.Button(row, text='↑', command=lambda: self.move_selection(-1)).pack(
            side='left', padx=(8, 0)
        )
        ttk.Button(row, text='↓', command=lambda: self.move_selection(1)).pack(
            side='left'
        )
        ttk.Label(
            parent, textvariable=self.space, style='Muted.TLabel', wraplength=850
        ).pack(anchor='w')
        self.bind_drag(app.tree, tree=app.tree)
        app.tree.bind('<Alt-Up>', lambda _: self.move_selection(-1))
        app.tree.bind('<Alt-Down>', lambda _: self.move_selection(1))

    def apply(self, pending):
        app = self.app
        keys = app.tree.get_children()
        eligible = [key for key in keys if app.jobs[key]['state'] == 'Na fila']
        if len(pending) != len(eligible) or set(pending) != set(eligible):
            return
        for index, key in enumerate(replace_pending(keys, app.jobs, pending)):
            app.tree.move(key, '', index)
        app.persist_queue()
        app.queue_filter.changed()
        app.refresh_queue()

    def sort(self):
        keys = [
            key
            for key in self.app.tree.get_children()
            if self.app.jobs[key]['state'] == 'Na fila'
        ]
        self.apply(sorted_keys(keys, self.app.jobs, self.order.get()))

    def move_before(self, key, target):
        keys = [
            k
            for k in self.app.tree.get_children()
            if self.app.jobs[k]['state'] == 'Na fila'
        ]
        if key not in keys or target not in keys or key == target:
            return
        old = keys.index(key)
        position = keys.index(target)
        keys.pop(old)
        keys.insert(position, key)
        self.apply(keys)

    def move_selection(self, direction):
        pending = [
            key
            for key in self.app.tree.get_children()
            if self.app.jobs[key]['state'] == 'Na fila'
        ]
        selected = set(self.app.tree.selection())
        indices = (
            range(len(pending)) if direction < 0 else range(len(pending) - 1, -1, -1)
        )
        for index in indices:
            target = index + direction
            if (
                pending[index] in selected
                and 0 <= target < len(pending)
                and pending[target] not in selected
            ):
                pending[index], pending[target] = pending[target], pending[index]
        self.apply(pending)
        return 'break'

    def bind_drag(self, widget, key=None, tree=None):
        def press(event):
            value = key if key is not None else tree.identify_row(event.y)
            self.drag = (value, event.y_root, False)

        def motion(event):
            if not self.drag:
                return
            value, start, moved = self.drag
            if abs(event.y_root - start) > 6:
                self.drag = (value, start, True)
            if tree and self.drag[2]:
                if event.y < 20:
                    tree.yview_scroll(-1, 'units')
                elif event.y > tree.winfo_height() - 20:
                    tree.yview_scroll(1, 'units')

        def release(event):
            previous = self.drag
            self.drag = None
            if not previous or not previous[2]:
                return
            if tree:
                target = tree.identify_row(event.y)
            else:
                target = next(
                    (
                        k
                        for k, row in self.app.queue_cards.rows.items()
                        if row[0].winfo_rooty()
                        <= event.y_root
                        < row[0].winfo_rooty() + row[0].winfo_height()
                    ),
                    None,
                )
            if target:
                self.move_before(previous[0], target)

        widget.bind('<ButtonPress-1>', press, add='+')
        widget.bind('<B1-Motion>', motion, add='+')
        widget.bind('<ButtonRelease-1>', release, add='+')

    def refresh(self):
        import time

        now = time.monotonic()
        if now - self.last_summary < 1:
            return
        self.last_summary = now
        for key, job in self.app.jobs.items():
            text = activity(job, self.app)
            if self.statuses.get(key) != text:
                self.app.tree.set(key, 'status', text)
                self.statuses[key] = text
        self.statuses = {
            key: value for key, value in self.statuses.items() if key in self.app.jobs
        }
        jobs = [
            job
            for job in self.app.jobs.values()
            if job['state'] in ('Na fila', 'Em andamento')
        ]
        report = storage_report(
            jobs, int(self.app.concurrent_downloads.get()), check_space=False
        )
        text = summary(*report[:3])
        if self.space.get() != text:
            self.space.set(text)

    def confirm(self, scope, scheduled=False):
        jobs = [
            job
            for key, job in self.app.jobs.items()
            if job['state'] == 'Na fila' and (scope is None or key in scope)
        ]
        report = storage_report(jobs, int(self.app.concurrent_downloads.get()))
        if report[3]:
            signature = tuple((job.get('url'), job.get('mode')) for job in jobs)
            if scheduled and getattr(self, 'rejected_space', None) == signature:
                return False
            accepted = messagebox.askyesno(
                tr('Espaço possivelmente insuficiente'),
                summary(*report[:3]) + '\n\n' + tr('Continuar mesmo assim?'),
                parent=self.app,
            )
            self.rejected_space = None if accepted else signature
            return accepted
        return True
