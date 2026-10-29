"""Non-blocking version choice while the worker waits for a JSON reply."""

from i18n import tr
from i18n_tk import display_var
import tkinter as tk
from tkinter import ttk
import webbrowser


def duration_label(seconds):
    if not isinstance(seconds, (int, float)):
        return "—"
    minutes, seconds = divmod(int(seconds), 60)
    return f"{minutes}:{seconds:02d}"


class VersionPicker(tk.Toplevel):
    def __init__(self, parent, event, on_select, on_cancel):
        super().__init__(parent)
        self.title(tr("Onda • Escolha a versão"))
        self.configure(bg="#101419")
        self.geometry("960x470")
        self.minsize(760, 420)
        self.transient(parent)
        self.provider = event.get("audio_provider", "YouTube")
        self.record = event
        self.on_select = on_select
        self.confirmed = False
        from audio_tools import PreviewPlayer

        self.player = PreviewPlayer()
        self.ffmpeg = parent.ffmpeg.get() if hasattr(parent, "ffmpeg") else ""
        self.preview_status = tk.StringVar()
        self.preview_after = None
        self.candidates = {str(i): row for i, row in enumerate(event["candidates"])}
        body = ttk.Frame(self, padding=22)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(2, weight=1, minsize=80)
        ttk.Label(
            body, text=tr("Qual versão você prefere?"), font=("Segoe UI", 20, "bold")
        ).grid(row=0, column=0, sticky="w")
        target_duration = duration_label(
            event["duration_ms"] / 1000 if event.get("duration_ms") else None
        )
        subtitle = ttk.Label(
            body,
            text=tr(
                f"{event['title']} · {', '.join(event.get('artists', []))} · Catálogo: {target_duration}"
            ),
            style="Muted.TLabel",
            wraplength=680,
        )
        subtitle.grid(row=1, column=0, sticky="ew", pady=(6, 16))
        panel = ttk.Frame(body)
        panel.grid(row=2, column=0, sticky="nsew")
        self.table = ttk.Treeview(
            panel,
            columns=("title", "channel", "duration", "score"),
            show="headings",
            selectmode="browse",
        )
        from list_context import bind_version

        bind_version(self, on_cancel)
        for key, label, width in (
            ("title", "VERSÃO NO " + self.provider.upper(), 420),
            ("channel", "ARTISTA" if self.provider == "Monochrome" else "CANAL", 240),
            ("duration", "DURAÇÃO", 90),
            ("score", "SIMILARIDADE", 110),
        ):
            self.table.heading(key, text=tr(label))
            self.table.column(
                key, width=width, minwidth=65, stretch=key in ("title", "channel")
            )
        self.table.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(panel, command=self.table.yview)
        scroll.pack(side="right", fill="y")
        self.table.configure(yscrollcommand=scroll.set)
        for key, row in self.candidates.items():
            self.table.insert(
                "",
                "end",
                iid=key,
                values=(
                    row.get("title"),
                    row.get("channel") or row.get("uploader") or "—",
                    duration_label(row.get("duration")),
                    (
                        tr("Conferir")
                        if row.get("manual_review")
                        else f"{row['match_score']:.0%}"
                    ),
                ),
            )
        instruction = (
            "Correspondência incerta: confira duração e versão. Abra no YouTube antes de confirmar."
            if any(row.get("manual_review") for row in self.candidates.values())
            else "Selecione e confirme, ou dê dois cliques na versão desejada."
        )
        ttk.Label(
            body, text=tr(instruction), style="Muted.TLabel", wraplength=680
        ).grid(row=3, column=0, sticky="w", pady=12)
        controls = ttk.Frame(body)
        controls.grid(row=4, column=0, sticky="ew")
        self.open_button = ttk.Button(
            controls,
            text=tr(
                "Abrir na fonte"
                if self.provider == "Monochrome"
                else "Abrir no YouTube"
            ),
            command=self.open_video,
            state="disabled",
        )
        self.open_button.pack(side="left")
        self.preview_button = ttk.Button(
            controls,
            text=tr("Ouvir / parar prévia"),
            command=self.preview,
            state="disabled",
        )
        self.preview_button.pack(side="left", padx=8)
        self.remember_choice = tk.BooleanVar(value=False)
        self.remember_check = ttk.Checkbutton(
            body,
            text=tr('Lembrar esta escolha após verificar novamente'),
            variable=self.remember_choice,
        )
        self.remember_check.grid(row=6, column=0, sticky='w')
        self.reset_choice = ttk.Button(
            body,
            text=tr('Desfazer escolhas e rejeições salvas'),
            command=self.clear_choices,
        )
        self.reset_choice.grid(row=7, column=0, sticky='w')
        self.reject_button = ttk.Button(
            controls, text=tr('Versão errada'), command=self.reject
        )
        self.reject_button.pack(side='left')
        self.select_button = ttk.Button(
            controls,
            text=tr("Baixar esta versão"),
            style="Accent.TButton",
            command=self.choose,
            state="disabled",
        )
        self.select_button.pack(side="right")
        ttk.Button(controls, text=tr("Cancelar"), command=on_cancel).pack(
            side="right", padx=8
        )
        ttk.Label(
            body,
            textvariable=display_var(self.preview_status),
            style="Muted.TLabel",
            wraplength=680,
        ).grid(row=5, column=0, sticky="w", pady=(8, 0))
        self.table.bind("<<TreeviewSelect>>", self.selected)
        self.table.bind("<Double-1>", self.double_click)
        self.table.bind("<Return>", lambda _: self.choose())
        body.bind(
            "<Configure>",
            lambda event: subtitle.configure(wraplength=max(400, event.width - 44)),
        )
        self.protocol("WM_DELETE_WINDOW", on_cancel)
        self.lift()
        self.preview_after = self.after(100, self.poll_preview)

    def selected(self, _=None):
        state = (
            "normal" if self.table.selection() and not self.confirmed else "disabled"
        )
        self.open_button.configure(state=state)
        self.select_button.configure(state=state)
        self.preview_button.configure(state=state)
        self.player.stop()
        row = (
            self.candidates[self.table.selection()[0]] if self.table.selection() else {}
        )
        self.preview_status.set(
            '; '.join(tr(reason) for reason in row.get('match_reasons') or [])
        )

    def choose(self):
        if not self.confirmed and self.table.selection():
            self.confirmed = True
            self.select_button.configure(state="disabled")
            selected = self.candidates[self.table.selection()[0]]["id"]
            self.on_select(
                {'selected_id': selected, 'remember_choice': True}
                if self.remember_choice.get()
                else selected
            )

    def reject(self):
        if self.table.selection():
            from search_choices import ChoiceStore

            key = self.table.selection()[0]
            ChoiceStore().set(self.record, self.candidates[key]['id'], False)
            self.table.delete(key)
            self.selected()
            self.preview_status.set(
                tr('Versão rejeitada. Use Desfazer para permitir novamente.')
            )

    def clear_choices(self):
        from search_choices import ChoiceStore

        ChoiceStore().clear(self.record)
        self.preview_status.set(
            tr(
                'Escolhas salvas removidas. Faça uma nova busca para restaurar os resultados.'
            )
        )

    def double_click(self, event):
        row = self.table.identify_row(event.y)
        if row:
            self.table.selection_set(row)
            self.choose()
        return "break"

    def open_video(self):
        if self.table.selection():
            row = self.candidates[self.table.selection()[0]]
            webbrowser.open(
                row["source_url"]
                if self.provider == "Monochrome"
                else "https://www.youtube.com/watch?v=" + row["id"]
            )

    def preview(self):
        if self.player.active:
            self.player.stop()
            self.preview_status.set("Prévia parada.")
            return
        if self.table.selection():
            row = self.candidates[self.table.selection()[0]]
            self.preview_status.set("Preparando a prévia…")
            self.player.play(
                (
                    row["source_url"]
                    if self.provider == "Monochrome"
                    else "https://www.youtube.com/watch?v=" + row["id"]
                ),
                self.ffmpeg,
                youtube=self.provider != "Monochrome",
            )

    def poll_preview(self):
        for message in self.player.messages():
            self.preview_status.set(message)
        self.preview_after = self.after(100, self.poll_preview)

    def destroy(self):
        self.player.close()
        if self.preview_after:
            self.after_cancel(self.preview_after)
            self.preview_after = None
        super().destroy()
