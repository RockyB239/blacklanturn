"""One public shelf request per picker, shared only with the exact selected row."""
import threading
import time

DWELL_SECONDS = 0.35
_slot = threading.BoundedSemaphore(1)


class GenreLookahead:
    def __init__(self, paths, fetch, cached=lambda path: False, clock=time.monotonic):
        self.paths = paths
        self.fetch = fetch
        self.cached = cached
        self.clock = clock
        self.focus = None
        self.since = 0.
        self.path = None
        self.done = threading.Event()
        self.closed = threading.Event()
        self.used = False
        self.items = None

    def observe(self, choice):
        if self.closed.is_set() or self.path is not None:
            return
        now = self.clock()
        if choice != self.focus:
            self.focus, self.since = choice, now
            return
        path = self.paths.get(choice)
        if not path or now - self.since < DWELL_SECONDS or not _slot.acquire(False):
            return
        self.path = path
        def work():
            try:
                if not self.closed.is_set() and not self.cached(path):
                    self.items = self.fetch(path)
            except Exception:
                pass  # The usual foreground provider handles retries and errors.
            finally:
                self.done.set()
                _slot.release()
        try:
            threading.Thread(target=work, name='BlackLanturnGenreShelf', daemon=True).start()
        except RuntimeError:
            self.done.set()
            _slot.release()

    def close(self):
        self.closed.set()

    def take(self, path, current):
        if path != self.path or self.used:
            return None
        self.used = True
        # This is the foreground request for the same route, already running.
        # Starting a second copy after an arbitrary deadline competes with it.
        while current():
            if self.done.wait(.05):
                return self.items if current() else None
        return None
