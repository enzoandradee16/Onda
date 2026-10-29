"""Reuse the working selection controls for a catalog match, before YouTube."""

from i18n import tr
import webbrowser
from version_picker import VersionPicker, duration_label


class CatalogPicker(VersionPicker):
    def __init__(self, parent, event, on_select, on_cancel):
        super().__init__(parent, event, on_select, on_cancel)
        self.title(tr("Onda • Confirme os metadados"))
        self.select_button.configure(text=tr("Usar estes metadados"))
        self.open_button.configure(text=tr("Abrir no catálogo"))
        self.preview_button.pack_forget()
        self.remember_check.grid_remove()
        self.reset_choice.grid_remove()
        self.reject_button.pack_forget()
        self.table.configure(columns=("title", "artist", "album", "duration"))
        for key, label, width in (
            ("title", "MÚSICA / VERSÃO", 300),
            ("artist", "ARTISTA / CATÁLOGO", 240),
            ("album", "ÁLBUM", 240),
            ("duration", "DURAÇÃO", 80),
        ):
            self.table.heading(key, text=tr(label))
            self.table.column(key, width=width, minwidth=65, stretch=key != "duration")
        for key, row in self.candidates.items():
            artist = ", ".join(row.get("artists", [])) + " · " + row.get("platform", "")
            self.table.item(
                key,
                values=(
                    row.get("title"),
                    artist,
                    row.get("album") or "—",
                    duration_label(row.get("duration")),
                ),
            )

    def open_video(self):
        if self.table.selection():
            webbrowser.open(self.candidates[self.table.selection()[0]]["source_url"])
