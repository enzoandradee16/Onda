"""Optional dismissal of status text without discarding operation state."""

import time

NOTICE_DURATIONS = {
    'Fechar manualmente': 0,
    **{f'Após {n} segundos': n for n in (3, 5, 10, 15, 30, 60)},
}


class StatusNotice:
    def __init__(self, app):
        self.app = app
        self.pending = None
        self.closed = False
        self.deadline = None
        self.animation_after = None
        self.traces = [
            (v, v.trace_add('write', self.changed))
            for v in (app.status, app.notice_duration)
        ]
        option = getattr(app, "notice_animation", None)
        if option is not None:
            self.traces.append((option, option.trace_add("write", self.changed)))
        self.changed()

    def changed(self, *_):
        if self.pending:
            self.app.after_cancel(self.pending)
            self.pending = None
        self.deadline = None
        self.app.notice_display.set(self.app.status.get())
        self.animate()
        self.check()

    def animate(self):
        if self.animation_after:
            self.app.after_cancel(self.animation_after)
            self.animation_after = None
        option = getattr(self.app, "notice_animation", None)
        if option is None or not option.get() or not self.app.notice_display.get():
            return
        from tkinter import ttk

        labels = [
            getattr(self.app, name, None)
            for name in ("status_label", "link_status_label")
        ]
        labels = [label for label in labels if label is not None]
        style = ttk.Style(self.app)
        colors = []
        for label in labels:
            name = label.cget("style") or "TLabel"
            fg = style.lookup(name, "foreground") or "#eef3f8"
            bg = style.lookup(name, "background") or "#101419"
            colors.append((label, fg, self.app.winfo_rgb(bg), self.app.winfo_rgb(fg)))

        def frame(step):
            self.animation_after = None
            for label, original, bg, fg in colors:
                rgb = [round((a + (b - a) * step / 8) / 257) for a, b in zip(bg, fg)]
                label.configure(
                    foreground=(
                        (
                            ttk.Style(self.app).lookup(
                                label.cget('style') or 'TLabel', 'foreground'
                            )
                            or original
                        )
                        if step == 8
                        else "#" + "".join(f"{v:02x}" for v in rgb)
                    )
                )
            if step < 8 and not self.closed:
                self.animation_after = self.app.after(22, lambda: frame(step + 1))

        frame(0)

    def check(self):
        self.pending = None
        if self.closed:
            return
        seconds = NOTICE_DURATIONS.get(self.app.notice_duration.get(), 0)
        if not seconds or not self.app.notice_display.get():
            return
        if getattr(self.app, 'active', False):
            self.deadline = None
            self.pending = self.app.after(250, self.check)
            return
        if self.deadline is None:
            self.deadline = time.monotonic() + seconds
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            self.dismiss()
        else:
            self.pending = self.app.after(max(1, round(remaining * 1000)), self.check)

    def dismiss(self):
        if self.pending:
            self.app.after_cancel(self.pending)
            self.pending = None
        self.app.notice_display.set('')

    def shutdown(self):
        self.closed = True
        self.dismiss()
        if self.animation_after:
            self.app.after_cancel(self.animation_after)
            self.animation_after = None
        for variable, trace in self.traces:
            variable.trace_remove('write', trace)
