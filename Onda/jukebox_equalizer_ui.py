"""Compact, live parametric equalizer editor for the desktop Jukebox."""

import json
import tkinter as tk
from tkinter import ttk
from i18n import tr
from jukebox_equalizer import clean, presets, preset_name


class EqualizerWindow(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title(tr('Equalizador'))
        self.transient(app)
        self.resizable(True, False)
        self.columnconfigure(0, weight=1)
        area = ttk.Frame(self, padding=16)
        area.grid(sticky='nsew')
        area.columnconfigure(2, weight=1)
        value = clean(app.jukebox_equalizer.get())
        self.enabled = tk.BooleanVar(value=value['enabled'])
        self.preamp = tk.DoubleVar(value=value['preamp'])
        ttk.Checkbutton(
            area,
            text=tr('Ativar equalizador'),
            variable=self.enabled,
            command=self.save,
        ).grid(row=0, column=0, columnspan=4, sticky='w', pady=(0, 10))
        self.preset_var = tk.StringVar(value=tr(preset_name(value)))
        ttk.Label(area, text=tr('Preset')).grid(row=1, column=0, sticky='w')
        selector = ttk.Combobox(
            area,
            textvariable=self.preset_var,
            state='readonly',
            values=[tr(name) for name in (*presets(), 'Personalizado')],
        )
        selector.grid(row=1, column=1, columnspan=3, sticky='ew', pady=(0, 8))
        selector.bind('<<ComboboxSelected>>', self.apply_preset)
        ttk.Label(area, text=tr('Pré-amplificação')).grid(
            row=2, column=0, columnspan=2, sticky='w'
        )
        ttk.Scale(area, from_=-24, to=0, variable=self.preamp, command=self.save).grid(
            row=2, column=2, sticky='ew', padx=8
        )
        self.preamp_label = ttk.Label(area, width=8)
        self.preamp_label.grid(row=2, column=3)
        bank = ttk.Frame(area)
        bank.grid(row=3, column=0, columnspan=4, sticky='ew', pady=(14, 0))
        ttk.Label(bank, text=tr('Ganho (dB)')).grid(row=0, column=0, sticky='w')
        ttk.Label(bank, text='+12 / 0 / −12').grid(row=1, column=0, sticky='w')
        ttk.Label(bank, text=tr('Frequência (Hz)')).grid(
            row=2, column=0, sticky='w', padx=(0, 8)
        )
        ttk.Label(bank, text='Q').grid(row=3, column=0, sticky='w')
        self.bands = []
        self.gain_labels = []
        self.gain_sliders = []
        for i, band in enumerate(value['bands']):
            col = i + 1
            bank.columnconfigure(col, weight=1)
            frequency = tk.StringVar(value=f"{band['frequency']:g}")
            gain = tk.DoubleVar(value=band['gain'])
            q = tk.StringVar(value=f"{band['q']:g}")
            self.bands.append((frequency, gain, q))
            label = ttk.Label(bank, width=5, anchor='center')
            label.grid(row=0, column=col)
            self.gain_labels.append(label)
            slider = ttk.Scale(
                bank,
                orient='vertical',
                from_=12,
                to=-12,
                variable=gain,
                command=self.save,
                length=190,
            )
            slider.grid(row=1, column=col, pady=8)
            self.gain_sliders.append(slider)
            for row, var, lo, hi, step in (
                (2, frequency, 20, 20000, 1),
                (3, q, 0.1, 10, 0.1),
            ):
                entry = ttk.Spinbox(
                    bank,
                    from_=lo,
                    to=hi,
                    increment=step,
                    textvariable=var,
                    width=6,
                    command=self.save,
                )
                entry.grid(row=row, column=col, padx=3, pady=4)
                entry.bind('<Return>', self.save)
                entry.bind('<FocusOut>', self.save)
        ttk.Label(
            area,
            text=tr(
                'Q menor: banda mais larga. Reduza a pré-amplificação ao aumentar os ganhos.'
            ),
            wraplength=590,
            style='Muted.TLabel',
        ).grid(row=4, column=0, columnspan=4, sticky='w', pady=10)
        ttk.Button(area, text=tr('Restaurar'), command=self.reset).grid(
            row=5, column=0, columnspan=2, sticky='w'
        )
        ttk.Button(area, text=tr('Pronto'), command=self.finish).grid(
            row=5, column=3, sticky='e'
        )
        self.protocol('WM_DELETE_WINDOW', self.finish)
        self.labels()

    def apply_preset(self, *_):
        name = next(
            (name for name in presets() if tr(name) == self.preset_var.get()), None
        )
        if name is None:
            self.preset_var.set(tr(preset_name(self.app.jukebox_equalizer.get())))
            return
        value = presets()[name]
        self.enabled.set(True)
        self.preamp.set(value['preamp'])
        for (f, g, q), band in zip(self.bands, value['bands']):
            f.set(f"{band['frequency']:g}")
            g.set(band['gain'])
            q.set(f"{band['q']:g}")
        self.save()

    def labels(self):
        self.preset_var.set(tr(preset_name(self.app.jukebox_equalizer.get())))
        self.preamp_label.configure(text=f'{self.preamp.get():+.1f} dB')
        for label, (_, gain, _) in zip(self.gain_labels, self.bands):
            label.configure(text=f'{gain.get():+.1f}')

    def save(self, *_):
        try:
            bands = [
                {
                    'frequency': float(f.get().replace(',', '.')),
                    'gain': g.get(),
                    'q': float(q.get().replace(',', '.')),
                }
                for f, g, q in self.bands
            ]
        except (ValueError, tk.TclError):
            return
        value = clean(
            {'enabled': self.enabled.get(), 'preamp': self.preamp.get(), 'bands': bands}
        )
        for (f, g, q), band in zip(self.bands, value['bands']):
            f.set(f"{band['frequency']:g}")
            q.set(f"{band['q']:g}")
        self.app.jukebox_equalizer.set(json.dumps(value))
        self.labels()

    def reset(self):
        for (f, g, q), band in zip(self.bands, clean()['bands']):
            f.set(f"{band['frequency']:g}")
            g.set(0)
            q.set('1.4')
        self.preamp.set(-6)
        self.save()

    def finish(self):
        self.save()
        self.destroy()
