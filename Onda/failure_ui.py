"""Post-run failures with export and a catalog search tied to the failed item."""

import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from i18n import tr
from i18n_tk import TranslatedCombobox
from failure_report import failed_rows, report_text, replace_metadata, AUDIO_MODES
from metadata import MetadataClient


class FailureWindow(tk.Toplevel):
    def __init__(self, app, ids=None):
        super().__init__(app)
        self.app = app
        self.rows = failed_rows(app.jobs, ids)
        self.results = []
        self.messages = queue.Queue()
        self.generation = 0
        self.closed = False
        self.title(tr("Falhas da fila"))
        self.geometry("920x680")
        self.minsize(800, 620)
        self.protocol("WM_DELETE_WINDOW", self.close)
        body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(2, weight=1, minsize=70)
        body.rowconfigure(5, weight=1, minsize=70)
        ttk.Label(
            body,
            text=tr("{count} downloads falharam").format(count=len(self.rows)),
            font=("Segoe UI", 15, "bold"),
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            body,
            text=tr(
                "Salve a lista ou escolha outros metadados para os itens de áudio. Depois, tente novamente."
            ),
            wraplength=740,
        ).grid(row=1, column=0, sticky="ew", pady=(6, 10))
        panel = ttk.Frame(body)
        panel.grid(row=2, column=0, sticky="nsew")
        self.table = ttk.Treeview(
            panel,
            columns=("title", "reason"),
            show="headings",
            selectmode="browse",
            height=4,
        )
        self.table.heading("title", text=tr("Música"))
        self.table.heading("reason", text=tr("Motivo"))
        self.table.column("title", width=330)
        self.table.column("reason", width=410)
        self.table.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(panel, command=self.table.yview)
        scroll.pack(side="right", fill="y")
        self.table.configure(yscrollcommand=scroll.set)
        for row in self.rows:
            self.table.insert(
                "", "end", iid=row['id'], values=(row['title'], tr(row['reason']))
            )
        self.table.bind("<<TreeviewSelect>>", self.selected)
        self.reason = tk.StringVar()
        reason_panel = ttk.Frame(body)
        reason_panel.grid(row=3, column=0, sticky="ew", pady=8)
        style = ttk.Style(self)
        self.reason_text = tk.Text(
            reason_panel,
            height=3,
            wrap="word",
            relief="flat",
            state="disabled",
            background=style.lookup('TFrame', 'background') or '#10151e',
            foreground=style.lookup('TLabel', 'foreground') or '#eef3fa',
        )
        self.reason_text.pack(side="left", fill="x", expand=True)
        reason_scroll = ttk.Scrollbar(reason_panel, command=self.reason_text.yview)
        reason_scroll.pack(side="right", fill="y")
        self.reason_text.configure(yscrollcommand=reason_scroll.set)

        def show_reason(*_):
            self.reason_text.configure(state="normal")
            self.reason_text.delete('1.0', 'end')
            self.reason_text.insert('1.0', self.reason.get())
            self.reason_text.configure(state="disabled")

        self.reason.trace_add('write', show_reason)
        search = ttk.Frame(body)
        search.grid(row=4, column=0, sticky="ew")
        self.query = tk.StringVar()
        self.entry = ttk.Entry(search, textvariable=self.query)
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", lambda _: self.search())
        self.provider = tk.StringVar(value="Deezer")
        TranslatedCombobox(
            search,
            textvariable=self.provider,
            values=("Deezer", "Apple / iTunes"),
            state="readonly",
            width=16,
        ).pack(side="left", padx=8)
        self.search_button = ttk.Button(
            search, text=tr("Pesquisar metadados"), command=self.search
        )
        self.search_button.pack(side="left")
        results_panel = ttk.Frame(body)
        results_panel.grid(row=5, column=0, sticky="nsew", pady=8)
        self.results_table = ttk.Treeview(
            results_panel,
            columns=("title", "artist", "album"),
            show="headings",
            height=4,
            selectmode="browse",
        )
        for key, label in (
            ("title", "Música"),
            ("artist", "Artista"),
            ("album", "Álbum"),
        ):
            self.results_table.heading(key, text=tr(label))
            self.results_table.column(key, width=220)
        self.results_table.pack(side="left", fill="both", expand=True)
        results_scroll = ttk.Scrollbar(results_panel, command=self.results_table.yview)
        results_scroll.pack(side="right", fill="y")
        self.results_table.configure(yscrollcommand=results_scroll.set)
        self.results_table.bind(
            "<<TreeviewSelect>>",
            lambda _: self.use.configure(
                state="normal" if self.results_table.selection() else "disabled"
            ),
        )
        self.use = ttk.Button(
            body, text=tr("Usar estes metadados"), command=self.apply, state="disabled"
        )
        self.use.grid(row=6, column=0, sticky="w")
        ttk.Label(
            body,
            text=tr(
                "A escolha substituirá a fonte de metadados deste item; formato e pasta serão mantidos."
            ),
            wraplength=740,
        ).grid(row=7, column=0, sticky="ew", pady=6)
        self.buttons = buttons = ttk.Frame(body)
        buttons.grid(row=8, column=0, sticky="ew", pady=(6, 0))
        ttk.Button(buttons, text=tr("Salvar lista"), command=self.save).pack(
            side="left"
        )
        ttk.Button(buttons, text=tr("Tentar novamente"), command=self.retry).pack(
            side="left", padx=8
        )
        ttk.Button(buttons, text=tr("Fechar"), command=self.close).pack(side="right")
        if self.rows:
            self.table.selection_set(self.rows[0]['id'])
        self.poll_id = self.after(100, self.poll)

    def selected(self, _=None):
        self.generation += 1
        self.results = []
        self.results_table.delete(*self.results_table.get_children())
        self.use.configure(state="disabled")
        ids = self.table.selection()
        row = next((x for x in self.rows if ids and x['id'] == ids[0]), None)
        self.query.set(row['title'] if row else "")
        self.reason.set(tr(row['reason']) if row else "")
        job = self.app.jobs.get(ids[0], {}) if ids else {}
        self.search_button.configure(
            state=(
                "normal"
                if job.get('mode') in AUDIO_MODES and not job.get('playlist')
                else "disabled"
            )
        )

    def search(self):
        if str(self.search_button.cget('state')) == 'disabled':
            return
        query = self.query.get().strip()
        selected = self.table.selection()
        if not selected or len(query) < 2:
            return
        self.generation += 1
        generation = self.generation
        provider = self.provider.get()
        self.reason.set(tr("Consultando o catálogo…"))
        self.search_button.configure(state="disabled")
        self.results = []
        self.results_table.delete(*self.results_table.get_children())
        self.use.configure(state="disabled")

        def worker():
            client = MetadataClient()
            try:
                self.messages.put((generation, client.search(query, provider), None))
            except Exception as error:
                self.messages.put((generation, [], str(error)))
            finally:
                client.close()

        threading.Thread(target=worker, daemon=True).start()

    def poll(self):
        while not self.messages.empty():
            generation, rows, error = self.messages.get()
            if generation != self.generation:
                continue
            self.results = rows
            self.search_button.configure(state="normal")
            self.reason.set(
                tr(error) if error else tr("Escolha uma música nos resultados")
            )
            for index, row in enumerate(rows):
                self.results_table.insert(
                    "",
                    "end",
                    iid=str(index),
                    values=(
                        row.get('title'),
                        ', '.join(row.get('artists') or []),
                        row.get('album') or '—',
                    ),
                )
        self.poll_id = self.after(100, self.poll)

    def apply(self):
        selected = self.table.selection()
        result = self.results_table.selection()
        if not selected or not result:
            return
        item = selected[0]
        job = self.app.jobs.get(item)
        if (
            not job
            or item in self.app.parallel.workers
            or job.get('state') not in ('Falhou', 'Na fila')
        ):
            return
        if replace_metadata(job, self.results[int(result[0])]):
            self.app.tree.set(item, 'name', job['display_name'])
            self.app.set_state(item, 'Na fila')
            self.app.refresh_queue()
            self.app.persist_queue()
            self.table.set(item, 'title', job['display_name'])
            self.table.set(item, 'reason', tr("Metadados escolhidos"))
            self.reason.set(tr("Metadados escolhidos"))

    def retry(self):
        ids = [
            row['id']
            for row in self.rows
            if self.app.jobs.get(row['id'], {}).get('state') in ('Falhou', 'Na fila')
            and row['id'] not in self.app.parallel.workers
        ]
        if not ids:
            return
        for item in ids:
            self.app.jobs[item]['state'] = 'Na fila'
            self.app.tree.set(item, 'status', tr('Na fila'))
            self.app.tree.item(item, tags=('Na fila',))
        self.app.refresh_queue()
        self.app.persist_queue()
        self.close()
        if self.app.running:
            self.app.parallel.extend(ids)
        else:
            self.app.parallel.start(ids)

    def save(self):
        path = filedialog.asksaveasfilename(
            parent=self,
            title=tr("Salvar lista"),
            defaultextension='.txt',
            initialfile='ONDA-falhas.txt',
            filetypes=[('TXT', '*.txt')],
        )
        if path:
            try:
                from pathlib import Path

                Path(path).write_text(report_text(self.rows), encoding='utf-8')
            except OSError as error:
                messagebox.showerror(tr("Salvar lista"), str(error), parent=self)

    def close(self):
        self.closed = True
        self.generation += 1
        self.after_cancel(self.poll_id)
        self.destroy()


def show_failures(app, ids=None):
    if not failed_rows(app.jobs, ids):
        return
    previous = getattr(app, 'failure_window', None)
    if previous is not None and previous.winfo_exists():
        previous.close()
    app.failure_window = FailureWindow(app, ids)
