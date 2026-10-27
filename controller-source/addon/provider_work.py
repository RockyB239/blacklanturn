"""One serial provider worker with a bounded, replaceable foreground queue."""
from collections import OrderedDict
from contextlib import nullcontext
import threading

class LatestWorker:
    def __init__(self):
        self.condition=threading.Condition();self.jobs=OrderedDict();self.thread=None

    def submit(self,key,work):
        with self.condition:
            self.jobs.pop(key,None);self.jobs[key]=work
            # Different obsolete window owners must not grow an unbounded queue.
            while len(self.jobs)>4:self.jobs.popitem(last=False)
            if self.thread is None or not self.thread.is_alive():
                self.thread=threading.Thread(target=self._run,name='BlackLanturnProvider',daemon=True);self.thread.start()
            self.condition.notify()

    def cancel(self,key):
        with self.condition:self.jobs.pop(key,None)

    def pending_count(self):
        with self.condition:return len(self.jobs)

    def _run(self):
        while True:
            with self.condition:
                if not self.jobs:
                    self.thread=None;return
                key,work=self.jobs.popitem(last=True)
            try:work()
            except Exception:
                # Each owner reports its own failure. A failed retired owner
                # must never kill the shared worker or block current work.
                pass

_rows=LatestWorker()

def submit_latest(owner,work):
    def owned():
        cache=getattr(owner,'snapshot_cache',None)
        with getattr(owner,'youtube_saved_request',nullcontext)():
            with cache.batch() if cache is not None else nullcontext():work()
    _rows.submit('visible-rows',owned)
