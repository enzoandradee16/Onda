"""Session timing based on monotonic active time and observed successful jobs."""
import math
import time


def duration_text(seconds):
    seconds=max(0,int(seconds))
    hours,remainder=divmod(seconds,3600)
    minutes,seconds=divmod(remainder,60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"


class QueueTiming:
    def __init__(self, clock=time.monotonic):
        self.clock=clock
        self.reset()

    def reset(self):
        self.elapsed=0.0
        self.started=None
        self.completed=0

    def set_running(self, running):
        if running and self.started is None:
            self.started=self.clock()
        elif not running and self.started is not None:
            self.elapsed+=max(0,self.clock()-self.started)
            self.started=None

    def record_completion(self):
        if self.started is not None:
            self.completed+=1

    def snapshot(self, remaining, has_items=True):
        elapsed=self.elapsed+(max(0,self.clock()-self.started) if self.started is not None else 0)
        estimate=None
        if has_items and remaining==0:
            estimate=0
        elif self.started is not None and self.completed and elapsed>0:
            value=elapsed/self.completed*max(0,remaining)
            if math.isfinite(value):estimate=math.ceil(value)
        return int(elapsed),estimate
