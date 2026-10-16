"""Live light/dark palettes, accents and Windows app-theme following."""
import os
import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
from interface_fonts import font_family, DEFAULT_FONT, font_scale

THEME_MODES = ('Seguir o sistema', 'Escuro', 'Preto puro', 'Claro')
ACCENTS = {
    'Verde-Água': ('#79e2c4', '#087e69'),
    'Azul': ('#8dbbff', '#245fbe'),
    'Roxo': ('#c0a4ff', '#7544b8'),
    'Rosa': ('#f5a4cd', '#af286d'),
    'Laranja': ('#ffbd85', '#a6500b'),
    'Vermelho': ('#ffa2a2', '#b42f3b'),
    'Verde': ('#94dfa8', '#257342'),
    'Verde-limão': ('#c8ed83', '#537512'),
    'Amarelo': ('#f6e58d', '#806600'),
    'Dourado': ('#e9ca82', '#8c650f'),
    'Ciano': ('#8de1ed', '#07758a'),
    'Turquesa': ('#71d8d8', '#087575'),
    'Índigo': ('#a5afff', '#4856b9'),
    'Lilás': ('#dec1ff', '#865098'),
    'Coral': ('#ffae9b', '#b34332'),
    'Cinza': ('#bcc5d3', '#576475'),
}


def system_mode():
    if os.name == 'nt':
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                    r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize') as key:
                return 'Claro' if winreg.QueryValueEx(key, 'AppsUseLightTheme')[0] else 'Escuro'
        except OSError:
            pass
    return 'Escuro'


def blend(first, second, amount):
    values = [round(int(first[i:i+2], 16)*(1-amount) + int(second[i:i+2], 16)*amount) for i in (1,3,5)]
    return '#' + ''.join(f'{value:02x}' for value in values)


def palette(mode='Seguir o sistema', accent='Verde-Água', separators=False):
    mode = system_mode() if mode == 'Seguir o sistema' else mode
    light = mode == 'Claro'
    colors = dict(zip(('bg','surface','input','text','muted','line'),
        ('#f3f5f8','#ffffff','#e7edf4','#182335','#53647b','#cad3df') if light else
        ('#101419','#191f27','#222a35','#eef3f8','#91a0b3','#2a3441')))
    if mode == 'Preto puro':
        colors.update(bg='#000000', surface='#000000', input='#101010', line='#303030')
    colors['accent'] = ACCENTS.get(accent, ACCENTS['Verde-Água'])[int(light)]
    colors.update(mode=mode, accent_text='#ffffff' if light else '#101419',
                  error='#b12c3c' if light else '#f2a198')
    colors['hover'] = blend(colors['input'], colors['text'], .08)
    colors['accent_hover'] = blend(colors['accent'], '#000000' if light else '#ffffff', .12)
    colors['selected'] = blend(colors['surface'], colors['accent'], .19)
    colors['disabled'] = blend(colors['muted'], colors['surface'], .35)
    colors['flat_black'] = mode == 'Preto puro' and not separators
    if colors['flat_black']:
        colors.update(bg='#000000', surface='#000000', input='#000000', line='#000000', hover='#000000', selected='#000000')
    return colors


LEGACY = {
    '#101419':'bg', '#10151e':'bg', '#191f27':'surface', '#1a2230':'surface',
    '#222a35':'input', '#eef3f8':'text', '#eef3fa':'text', 'white':'text',
    '#91a0b3':'muted', '#a6b4c8':'muted', '#79e2c4':'accent', '#65dfbd':'accent',
    '#2a3441':'line', '#303d4d':'hover', '#566373':'disabled', '#a0edd7':'accent_hover',
    '#2b4841':'line', '#7eaa9e':'muted', '#2b3d47':'selected', '#345048':'selected',
    '#f2a198':'error',
}


class ThemeManager:
    def __init__(self, app):
        self.app = app
        self.colors = None
        self.font_name = None
        self.font_scale = None
        self.spacing = None
        self.closed = False
        self.generation = 0
        self.after_id = None
        self.traces = [(var, var.trace_add('write', self.changed)) for var in (app.theme_mode, app.theme_accent, app.interface_font, app.interface_font_size, app.interface_spacing, app.pure_black_separators)]
        self.map_binding = app.bind_all('<Map>', self.mapped, add='+')
        self.apply()
        self.after_id = app.after(1500, self.check_system)

    def changed(self, *_):
        self.apply()

    def apply(self):
        colors = palette(self.app.theme_mode.get(), self.app.theme_accent.get(), self.app.pure_black_separators.get())
        font_name = self.app.interface_font.get()
        scale = font_scale(self.app.interface_font_size.get())
        spacing = self.app.interface_spacing.get()
        if colors == self.colors and font_name == self.font_name and scale == self.font_scale and spacing == self.spacing:
            return
        self.colors = colors
        self.font_name = font_name
        self.font_scale = scale
        self.spacing = spacing
        self.resolved_font = font_family(self.app, font_name)
        self.generation += 1
        self.app._style()
        self.walk(self.app)

    def check_system(self):
        self.after_id = None
        if self.closed:
            return
        if self.app.theme_mode.get() == 'Seguir o sistema':
            self.apply()
        self.after_id = self.app.after(1500, self.check_system)

    def mapped(self, event):
        if not self.closed and isinstance(event.widget, tk.Misc):
            if getattr(event.widget, '_onda_theme_generation', None) == self.generation:
                return
            if isinstance(event.widget, (tk.Toplevel, tk.Tk)):
                self.walk(event.widget)
            else:
                self.widget(event.widget)

    def walk(self, widget):
        self.widget(widget)
        for child in widget.winfo_children():
            self.walk(child)

    def widget(self, widget):
        c = self.colors
        if not c or getattr(widget, '_onda_theme_generation', None) == self.generation:
            return
        try:
            from interface_spacing import apply_spacing, spacing_scale
            apply_spacing(widget, spacing_scale(self.spacing))
            self.apply_widget_font(widget)
            roles = getattr(widget, '_onda_color_roles', None)
            if roles is None:
                roles = {}
                for option in ('background','foreground','insertbackground','selectbackground','selectforeground','activebackground','activeforeground','highlightbackground'):
                    if option in widget.keys():
                        value = str(widget.cget(option)).lower()
                        if value in LEGACY:
                            roles[option] = LEGACY[value]
                if isinstance(widget, (tk.Toplevel, tk.Tk)):
                    roles['background'] = 'bg'
                if isinstance(widget, tk.Menu):
                    roles.update(background='input',foreground='text',activebackground='selected',activeforeground='text')
                widget._onda_color_roles = roles
            if roles:
                widget.configure(**{option:c[role] for option,role in roles.items()})
            if isinstance(widget, tk.Canvas):
                fills = getattr(widget, '_onda_fill_roles', {})
                for item in widget.find_all():
                    try:
                        if widget.type(item) == 'text':
                            self.apply_canvas_font(widget, item)
                        role = fills.get(item) or LEGACY.get(str(widget.itemcget(item,'fill')).lower())
                        if role:
                            fills[item] = role
                            widget.itemconfigure(item,fill=c[role])
                    except tk.TclError:
                        pass
                widget._onda_fill_roles = fills
            if isinstance(widget, ttk.Treeview):
                for tag, role in (('Concluído','accent'),('Falhou','error'),('Cancelado','muted')):
                    widget.tag_configure(tag,foreground=c[role])
            if isinstance(widget, ttk.Combobox):
                popup = widget.tk.call('ttk::combobox::PopdownWindow', widget)
                widget.tk.call(str(popup)+'.f.l','configure','-background',c['input'],'-foreground',c['text'],
                               '-selectbackground',c['selected'],'-selectforeground',c['text'],
                               '-font',(self.resolved_font, round(10 * self.font_scale)))
            if isinstance(widget, (tk.Toplevel, tk.Tk)):
                self.titlebar(widget)
                from window_icons import apply_window_icon
                apply_window_icon(widget,c)
            widget._onda_theme_generation = self.generation
        except tk.TclError:
            pass

    def apply_widget_font(self, widget):
        if 'font' not in widget.keys() or not str(widget.cget('font')):
            return  # Inherited ttk fonts follow the shared styles.
        base = getattr(widget, '_onda_base_font', None)
        if base is None:
            base = tkfont.Font(root=self.app, font=widget.cget('font')).actual()
            widget._onda_base_font = base
            widget._onda_live_font = tkfont.Font(root=self.app, **base)
        widget._onda_live_font.configure(family=base['family'] if self.font_name == DEFAULT_FONT else self.resolved_font, size=round(base['size'] * self.font_scale))
        widget.configure(font=widget._onda_live_font)

    def apply_canvas_font(self, canvas, item):
        fonts = getattr(canvas, '_onda_item_fonts', None)
        if fonts is None:
            fonts = canvas._onda_item_fonts = {}
        if item not in fonts:
            base = tkfont.Font(root=self.app, font=canvas.itemcget(item, 'font')).actual()
            fonts[item] = (base, tkfont.Font(root=self.app, **base))
        base, live = fonts[item]
        live.configure(family=base['family'] if self.font_name == DEFAULT_FONT else self.resolved_font, size=round(base['size'] * self.font_scale))
        canvas.itemconfigure(item, font=live)

    def titlebar(self, window):
        if os.name != 'nt':
            return
        try:
            import ctypes
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
            user32.GetAncestor.restype = wintypes.HWND
            handle = user32.GetAncestor(window.winfo_id(), 2)
            value = wintypes.BOOL(self.colors['mode'] in ('Escuro', 'Preto puro'))
            func = ctypes.windll.dwmapi.DwmSetWindowAttribute
            func.argtypes = [wintypes.HWND,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD]
            func(handle,20,ctypes.byref(value),ctypes.sizeof(value))
            flat=self.colors.get('flat_black',False)
            for attribute in (34,35):
                color=wintypes.DWORD(0 if flat else 0xffffffff)
                func(handle,attribute,ctypes.byref(color),ctypes.sizeof(color))
        except (OSError, AttributeError):
            pass

    def shutdown(self):
        self.closed = True
        for var, trace in self.traces:
            var.trace_remove('write',trace)
        if self.after_id:
            self.app.after_cancel(self.after_id)
            self.after_id = None
        # Remove only our callback; other Map handlers center windows and set icons.
        self.app._unbind(('bind','all','<Map>'), self.map_binding)
