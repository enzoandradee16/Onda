"""Translate rendered Tk labels and choices while retaining canonical values."""

import tkinter as tk
from tkinter import ttk
from i18n import tr


def display_var(variable):
    cached = getattr(variable, "_i18n_display", None)
    if cached is not None:
        return cached
    translated = tk.StringVar(master=variable._root, value=tr(variable.get()))

    def update(*_):
        try:
            translated.set(tr(variable.get()))
        except tk.TclError:
            pass

    variable.trace_add("write", update)
    variable._i18n_display = translated
    return translated


class TranslatedCombobox(ttk.Combobox):
    """Display translated options; get/set/textvariable always use stable keys."""

    def __init__(self, master=None, **kwargs):
        self._canonical = kwargs.pop("textvariable", None)
        if self._canonical is None:
            self._canonical = tk.StringVar(master=master)
        self._choices = tuple(kwargs.pop("values", ()))
        self._display = tk.StringVar(master=master)
        self._updating = False
        super().__init__(
            master,
            textvariable=self._display,
            values=self._translated_choices(),
            **kwargs,
        )
        self._source_trace = self._canonical.trace_add("write", self._from_source)
        self._display_trace = self._display.trace_add("write", self._from_display)
        self.bind("<Destroy>", self._cleanup, add="+")
        self._from_source()

    def _translated_choices(self):
        return tuple(self._label(value) for value in self._choices)

    @staticmethod
    def _label(value):
        if value == "Áudio · MP3 (320 kbps)":
            value = "Áudio · MP3"
        return {"pt-BR": "Português (Brasil)", "es": "Español", "en": "English"}.get(
            value, tr(value)
        )

    def _from_source(self, *_):
        if not self._updating:
            self._updating = True
            try:
                self._display.set(self._label(self._canonical.get()))
            finally:
                self._updating = False

    def _from_display(self, *_):
        if not self._updating:
            value = self._display.get()
            canonical = next(
                (
                    str(choice)
                    for choice in self._choices
                    if self._label(choice) == value
                ),
                value,
            )
            self._updating = True
            try:
                self._canonical.set(canonical)
            finally:
                self._updating = False

    def cget(self, key):
        if key == 'textvariable':
            return str(self._canonical)
        return super().cget(key)

    def get(self):
        return self._canonical.get()

    def set(self, value):
        self._canonical.set(value)

    def configure(self, cnf=None, **kwargs):
        if cnf is not None and not isinstance(cnf, dict):
            return super().configure(cnf, **kwargs)
        options = dict(cnf or {}, **kwargs)
        if "textvariable" in options:
            self._canonical.trace_remove("write", self._source_trace)
            self._canonical = options["textvariable"]
            self._source_trace = self._canonical.trace_add("write", self._from_source)
            options["textvariable"] = self._display
        if "values" in options:
            self._choices = tuple(options["values"])
            options["values"] = self._translated_choices()
        result = super().configure(**options) if options else super().configure()
        if options:
            self._from_source()
        return result

    config = configure

    def _cleanup(self, event):
        if event.widget is self:
            self._canonical.trace_remove("write", self._source_trace)
            self._display.trace_remove("write", self._display_trace)
