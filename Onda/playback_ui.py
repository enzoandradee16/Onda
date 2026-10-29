"""One stable effects tab, with independent internal workspaces and shared file input."""

from tkinter import ttk
from i18n import tr
from effects_ui import EffectsPane
from jukebox_ui import JukeboxPane


class PlaybackPane(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=(0, 12, 0, 0))
        self.app = app
        ttk.Label(
            self,
            text=tr('Reprodução e efeitos'),
            font=('Segoe UI', 23, 'bold'),
            anchor='center',
        ).pack(fill='x')
        ttk.Label(
            self,
            text=tr('Sua música, de um novo jeito.'),
            style='Muted.TLabel',
            anchor='center',
        ).pack(fill='x', pady=(5, 12))
        self.modes = ttk.Notebook(self, style="Playback.TNotebook")
        self.modes.pack(fill='both', expand=True)
        self.effects = EffectsPane(self.modes, app, heading=False)
        self.jukebox = JukeboxPane(self.modes, app, self.use_file)
        self.modes.add(self.effects, text=tr('Efeitos'))
        self.modes.add(self.jukebox, text=tr('Jukebox infinito'))
        self.modes.bind('<<NotebookTabChanged>>', self.switched)

    @property
    def busy(self):
        return self.effects.busy or self.jukebox.busy

    @busy.setter
    def busy(self, value):
        self.effects.busy = value

    def switched(self, _=None):
        if self.modes.select() == str(self.jukebox):
            self.effects.stop_preview()
            source = self.effects.source.get()
            if (
                source
                and (source != self.jukebox.source or not self.jukebox.model)
                and not self.jukebox.computing
            ):
                self.jukebox.set_source(source)
        else:
            self.jukebox.stop_preview()
            if self.jukebox.model and self.jukebox.source != self.effects.source.get():
                self.effects.use_file(self.jukebox.source)

    def use_file(self, path, mode='effects'):
        self.stop_preview()
        self.jukebox.model = None
        self.jukebox.source = ""
        self.effects.use_file(path)
        self.modes.select(self.jukebox if mode == 'jukebox' else self.effects)
        if mode == 'jukebox':
            self.jukebox.set_source(path)

    def stop_preview(self):
        self.effects.stop_preview()
        self.jukebox.stop_preview()

    def cancel(self):
        self.effects.cancel()
        self.jukebox.cancel()

    def shutdown(self):
        self.effects.shutdown()
        self.jukebox.shutdown()

    def __setattr__(self, name, value):
        effects = self.__dict__.get('effects')
        legacy = {
            'lyric_rows',
            'lyric_text',
            'source',
            'speed',
            'reverb',
            'keep_pitch',
            'preset',
            'start_time',
            'mode',
            'status',
            'player',
            'process',
            'preview_active',
            'playback_mode',
            'duration',
            'position',
            'time_label',
            'dragging',
            'resume_mode',
            'probe_generation',
            'render_temp',
            'output_folder',
        }
        if effects is not None and name in legacy:
            setattr(effects, name, value)
        else:
            super().__setattr__(name, value)

    def __getattr__(self, name):
        effects = self.__dict__.get('effects')
        if effects is not None:
            return getattr(effects, name)
        raise AttributeError(name)
