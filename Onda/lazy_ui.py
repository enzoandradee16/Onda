"""Notebook containers which create their content only when needed."""

from importlib import import_module
from tkinter import ttk


class LazyPane(ttk.Frame):
    def __init__(self, parent, app, module, name):
        self._content = None
        self._factory = (module, name)
        self._app = app
        super().__init__(parent)
        from settings_scroll import SettingsCategory
        from ui import BG

        self._scroller = SettingsCategory(self, BG, fill_viewport=True, padding=0)
        self._scroller.pack(fill="both", expand=True)

    def ensure_ready(self):
        if self._content is None:
            module, name = self._factory
            content = getattr(import_module(module), name)(
                self._scroller.content, self._app
            )
            self._content = content
            content.pack(fill="both", expand=True)
            manager = getattr(self._app, "theme_manager", None)
            if manager is not None:
                manager.walk(content)
        return self._content

    @property
    def busy(self):
        return self._content.busy if self._content is not None else False

    def stop_preview(self):
        if self._content is not None:
            self._content.stop_preview()

    def shutdown(self):
        if self._content is not None:
            self._content.shutdown()

    def refresh(self):
        # Downloads must not construct a hidden history page.
        if self._content is not None:
            self._content.refresh()

    # Widget geometry belongs to the notebook container; pane data and actions
    # belong to the content, even when a name (e.g. size) is also a ttk method.
    _container_names = frozenset(
        {
            "tk",
            "master",
            "children",
            "widgetName",
            "ensure_ready",
            "busy",
            "stop_preview",
            "shutdown",
            "refresh",
            "destroy",
            "configure",
            "config",
            "cget",
            "keys",
            "bind",
            "bind_all",
            "bindtags",
            "unbind",
            "unbind_all",
            "pack",
            "pack_forget",
            "grid",
            "grid_forget",
            "place",
            "place_forget",
            "after",
            "after_idle",
            "after_cancel",
            "register",
            "nametowidget",
        }
    )

    def __getattribute__(self, name):
        if (
            name.startswith("_")
            or name.startswith("winfo_")
            or name in LazyPane._container_names
        ):
            return super().__getattribute__(name)
        return getattr(self.ensure_ready(), name)

    def __setattr__(self, name, value):
        if name.startswith("_") or name in ("tk", "master", "children", "widgetName"):
            super().__setattr__(name, value)
        else:
            setattr(self.ensure_ready(), name, value)

    def __delattr__(self, name):
        if name.startswith("_"):
            super().__delattr__(name)
        else:
            delattr(self.ensure_ready(), name)

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return getattr(self.ensure_ready(), name)
