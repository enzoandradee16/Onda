"""Desktop completion policy and one bounded native-shell timer."""

import os, queue, time, subprocess
import tkinter as tk
from tkinter import ttk, messagebox
from i18n import tr
from i18n_tk import TranslatedCombobox

FINISH_ACTIONS = ('Nenhuma', 'Som', 'Notificação', 'Som e notificação', 'Desligar PC')
CLOSE_BEHAVIORS = ('Encerrar', 'Minimizar para a bandeja')


def settings_controls(app, parent):
    ttk.Label(parent, text=tr('Ação ao terminar a fila')).pack(anchor='w', pady=(12, 4))
    TranslatedCombobox(
        parent,
        textvariable=app.finish_action,
        values=FINISH_ACTIONS,
        state='readonly',
        width=30,
    ).pack(anchor='w')
    ttk.Checkbutton(
        parent,
        text=tr('Mostrar progresso na barra de tarefas'),
        variable=app.taskbar_progress,
    ).pack(anchor='w', pady=8)


def close_controls(app, parent):
    ttk.Label(parent, text=tr('Ao fechar o ONDA')).pack(anchor='w', pady=(12, 4))
    TranslatedCombobox(
        parent,
        textvariable=app.close_behavior,
        values=CLOSE_BEHAVIORS,
        state='readonly',
        width=30,
    ).pack(anchor='w')


def queue_progress(app):
    parallel = app.parallel
    keys = set(parallel.attempted) | {
        key
        for key, job in app.jobs.items()
        if job['state'] == 'Na fila'
        and (parallel.scope is None or key in parallel.scope)
    }
    if not keys:
        return 0
    total = 0.0
    for key in keys:
        job = app.jobs.get(key, {})
        if job.get('state') in ('Concluído', 'Falhou', 'Cancelado'):
            total += 1
        elif key in parallel.workers:
            total += min(0.99, max(0, job.get('_queue_percent', 0) / 100))
    return min(99, total / len(keys) * 100)


class DailyDesktop:
    def __init__(self, app):
        self.app = app
        self.shell = None
        self.timer = None
        self.hidden = False
        self.balloon_until = 0
        self.signature = None
        self.shutdown_window = None
        self.shutdown_timer = None
        self.closed = False
        if os.name == 'nt':
            try:
                from windows_shell import WindowsShell

                self.shell = WindowsShell(app)
            except OSError as error:
                app.status.set('Windows: ' + str(error))
        self.menu = tk.Menu(app, tearoff=False)
        self.menu.add_command(label=tr('Abrir ONDA'), command=self.restore)
        self.menu.add_command(label=tr('Baixar fila'), command=app.start)
        self.menu.add_command(label=tr('Parar fila'), command=app.cancel)
        self.menu.add_separator()
        self.menu.add_command(
            label=tr('Sair'), command=lambda: app.close(force_exit=True)
        )
        self.timer = app.after(500, self.poll)

    def hide(self):
        if not self.shell:
            return False
        self.shell.theme_icon(self.app.theme_manager.colors)
        if not self.shell.add():
            return False
        self.hidden = True
        self.app.withdraw()
        return True

    def restore(self):
        self.hidden = False
        self.app.deiconify()
        self.app.lift()
        self.app.focus_force()
        if self.shell and time.monotonic() > self.balloon_until:
            self.shell.remove()

    def poll(self):
        self.timer = None
        if self.closed:
            return
        if self.shell:
            current = self.shell.user.GetAncestor(self.app.winfo_id(), 2)
            if current != self.shell.hwnd:
                self.shell.close()
                from windows_shell import WindowsShell

                self.shell = WindowsShell(self.app)
                self.signature = None
                if self.hidden:
                    self.shell.add()
            self.shell.theme_icon(self.app.theme_manager.colors)
            for _ in range(8):
                try:
                    event = self.shell.events.get_nowait()
                except queue.Empty:
                    break
                if event == 'open':
                    self.restore()
                elif event == 'menu':
                    self.menu.tk_popup(
                        self.app.winfo_pointerx(), self.app.winfo_pointery()
                    )
                    self.menu.grab_release()
                elif event == 'restart' and self.hidden:
                    self.shell.add()
            running = self.app.running or bool(self.app.parallel.workers)
            value = queue_progress(self.app) if running else None
            paused = (
                self.app.parallel.memory_wait is not None
                and not self.app.parallel.workers
            )
            signature = (
                value,
                paused,
                self.app.taskbar_progress.get(),
                self.shell.ready,
            )
            if signature != self.signature:
                self.signature = (
                    signature
                    if self.shell.progress(
                        value, paused, self.app.taskbar_progress.get()
                    )
                    else None
                )
            if self.hidden and self.app.state() != 'withdrawn':
                self.hidden = False
            if self.hidden:
                self.shell.add(
                    'ONDA · ' + str(int(value or 0)) + '%' if running else 'ONDA'
                )
            elif time.monotonic() > self.balloon_until:
                self.shell.remove()
        if self.shutdown_window is not None and self.busy():
            self.cancel_shutdown()
        self.timer = self.app.after(500, self.poll)

    def busy(self):
        return (
            self.app.running
            or bool(self.app.parallel.workers)
            or any(
                getattr(self.app, name).busy
                for name in (
                    'converter_page',
                    'effects_page',
                    'metadata_page',
                    'playlist_page',
                )
            )
            or any(job['state'] == 'Na fila' for job in self.app.jobs.values())
        )

    def finished(self, attempted):
        if not attempted:
            return
        action = self.app.finish_action.get()
        completed = sum(
            self.app.jobs.get(key, {}).get('state') == 'Concluído' for key in attempted
        )
        message = (
            tr('Fila finalizada: {done}/{total} concluídos.')
            .replace('{done}', str(completed))
            .replace('{total}', str(len(attempted)))
        )
        if action in ('Som', 'Som e notificação'):
            if os.name == 'nt':
                import winsound

                winsound.PlaySound(
                    'SystemNotification',
                    winsound.SND_ALIAS | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
                )
        if action in ('Notificação', 'Som e notificação') and self.shell:
            if self.shell.notify('ONDA', message):
                self.balloon_until = time.monotonic() + 20
        if action == 'Desligar PC' and completed == len(attempted) and not self.busy():
            self.restore()
            if messagebox.askyesno(
                tr('Desligar PC'),
                tr('A fila terminou. Desligar o PC após 60 segundos?'),
                parent=self.app,
            ):
                self.begin_shutdown()

    def begin_shutdown(self):
        self.cancel_shutdown()
        window = tk.Toplevel(self.app)
        self.shutdown_window = window
        window.title(tr('Desligar PC'))
        window.transient(self.app)
        body = ttk.Frame(window, padding=20)
        body.pack(fill='both', expand=True)
        text = tk.StringVar()
        ttk.Label(body, textvariable=text).pack()
        ttk.Button(
            body, text=tr('Cancelar desligamento'), command=self.cancel_shutdown
        ).pack(pady=12)
        window.protocol('WM_DELETE_WINDOW', self.cancel_shutdown)
        deadline = time.monotonic() + 60

        def tick():
            self.shutdown_timer = None
            if self.busy():
                self.cancel_shutdown()
                return
            remaining = max(0, int(deadline - time.monotonic() + 0.99))
            text.set(
                tr('O PC será desligado em {seconds} segundos.').replace(
                    '{seconds}', str(remaining)
                )
            )
            if remaining:
                self.shutdown_timer = self.app.after(1000, tick)
            else:
                self.cancel_shutdown()
                try:
                    subprocess.run(
                        ['shutdown.exe', '/s', '/t', '0'],
                        check=True,
                        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
                    )
                except (OSError, subprocess.SubprocessError) as error:
                    messagebox.showerror(tr('Desligar PC'), str(error), parent=self.app)

        tick()

    def cancel_shutdown(self):
        if self.shutdown_timer:
            self.app.after_cancel(self.shutdown_timer)
            self.shutdown_timer = None
        if self.shutdown_window is not None:
            if self.shutdown_window.winfo_exists():
                self.shutdown_window.destroy()
            self.shutdown_window = None

    def close(self):
        self.closed = True
        self.cancel_shutdown()
        if self.timer:
            self.app.after_cancel(self.timer)
            self.timer = None
        if self.shell:
            self.shell.close()
        self.menu.destroy()
