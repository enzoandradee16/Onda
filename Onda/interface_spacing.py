"""Live layout density without scaling fonts, icons or minimum control sizes."""
import tkinter as tk
from tkinter import ttk

SPACING_MODES = ('Compacto', 'Padrão', 'Confortável')

def spacing_scale(value):
    return {'Compacto': .8, 'Padrão': 1.0, 'Confortável': 1.25}.get(value, 1.0)

def _pixels(widget, value):
    parts = value if isinstance(value, (tuple, list)) else widget.tk.splitlist(str(value))
    return tuple(widget.winfo_pixels(part) for part in parts)

def apply_spacing(widget, scale):
    # Keep original values so repeated preference/theme changes never accumulate.
    # Rebase when another component explicitly changes a layout margin.
    try:
        manager = widget.winfo_manager()
        if manager not in ('pack', 'grid'):
            return
        info = widget.pack_info() if manager == 'pack' else widget.grid_info()
        cache = getattr(widget, '_onda_spacing_base', {})
        changes = {}
        for key in ('padx', 'pady'):
            raw = info.get(key, 0)
            values = _pixels(widget, raw) or (0,)
            previous = cache.get((manager, key))
            base = previous[0] if previous and values == previous[1] else values
            target = tuple(max(1, round(value * scale)) if value else 0 for value in base)
            cache[(manager, key)] = (base, target)
            if target != values:
                changes[key] = target
        widget._onda_spacing_base = cache
        if changes:
            (widget.pack_configure if manager == 'pack' else widget.grid_configure)(**changes)
        if isinstance(widget, ttk.Frame):
            raw = _pixels(widget, widget.cget('padding'))
            previous = getattr(widget, '_onda_spacing_padding', None)
            base = previous[0] if previous and raw == previous[1] else raw
            target = tuple(max(1, round(value * scale)) if value else 0 for value in base)
            widget._onda_spacing_padding = (base, target)
            if raw != target:widget.configure(padding=target)
    except tk.TclError:
        pass
