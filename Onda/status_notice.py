"""Optional dismissal of status text without discarding operation state."""
import time

NOTICE_DURATIONS = {'Fechar manualmente':0, **{f'Após {n} segundos':n for n in (3,5,10,15,30,60)}}

class StatusNotice:
    def __init__(self, app):
        self.app=app;self.pending=None;self.closed=False;self.deadline=None
        self.traces=[(v,v.trace_add('write',self.changed)) for v in (app.status,app.notice_duration)]
        self.changed()
    def changed(self,*_):
        if self.pending:self.app.after_cancel(self.pending);self.pending=None
        self.deadline=None
        self.app.notice_display.set(self.app.status.get())
        self.check()
    def check(self):
        self.pending=None
        if self.closed:return
        seconds=NOTICE_DURATIONS.get(self.app.notice_duration.get(),0)
        if not seconds or not self.app.notice_display.get():return
        if getattr(self.app,'active',False):
            self.deadline=None;self.pending=self.app.after(250,self.check);return
        if self.deadline is None:self.deadline=time.monotonic()+seconds
        remaining=self.deadline-time.monotonic()
        if remaining<=0:self.dismiss()
        else:self.pending=self.app.after(max(1,round(remaining*1000)),self.check)
    def dismiss(self):
        if self.pending:self.app.after_cancel(self.pending);self.pending=None
        self.app.notice_display.set('')
    def shutdown(self):
        self.closed=True;self.dismiss()
        for variable,trace in self.traces:variable.trace_remove('write',trace)
