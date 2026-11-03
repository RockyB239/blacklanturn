"""Device-local baselines for public movie and show shelves."""
from collections import OrderedDict
from hashlib import sha256
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
import json
import re
import threading

from live_runtime import write_controller_config
from provider_work import LatestWorker
from public_rows import public_path

MAX_BYTES = 128 * 1024
MAX_SHELVES = 96
MAX_TITLES = 40
TITLE = re.compile(r'(?:movie|tv):[1-9][0-9]{0,11}')
SHELF = re.compile(r'[a-f0-9]{64}')
_worker = LatestWorker(paused=lambda: False)


def title_key(item):
    path = item.get('file', '')
    if item.get('_page_control') or not public_path(path, item=True):
        return None
    query = parse_qs(urlsplit(path).query)
    if query.get('info', [''])[0] not in ('play', 'details', 'seasons', 'flatseasons'):
        return None
    if {'season', 'episode'} & query.keys():
        return None
    key = query.get('tmdb_type', [''])[0] + ':' + query.get('tmdb_id', [''])[0]
    return key if TITLE.fullmatch(key) else None


class ShelfVisits:
    def __init__(self, path, submit=None):
        self.path = Path(path)
        self.submit = submit or (lambda save: _worker.submit(str(self.path), save))
        self.lock = threading.Lock()
        self.rows = OrderedDict()
        try:
            with self.path.open('rb') as stream:
                raw = stream.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                return
            document = json.loads(raw)
            if not isinstance(document, dict) or document.get('version') != 1:
                return
            rows = document.get('shelves', {})
            if isinstance(rows, dict) and len(rows) <= MAX_SHELVES:
                for key, values in rows.items():
                    if (SHELF.fullmatch(key) and isinstance(values, list)
                        and 0 < len(values) <= MAX_TITLES
                        and all(isinstance(value, str) and TITLE.fullmatch(value) for value in values)):
                        self.rows[key] = values
        except (OSError, ValueError, RecursionError):
            pass

    def visit(self, shelf, items):
        titles = list(dict.fromkeys(key for item in items if (key := title_key(item))))[:MAX_TITLES]
        if not titles:
            return set()
        key = sha256(shelf.encode('utf-8')).hexdigest()
        with self.lock:
            previous = self.rows.get(key)
            if previous != titles:
                self.rows[key] = titles
                self.rows.move_to_end(key)
                while len(self.rows) > MAX_SHELVES:
                    self.rows.popitem(last=False)
        if previous != titles:
            self.submit(self._save)
        return set(titles) - set(previous) if previous else set()

    def _save(self):
        with self.lock:
            snapshot = dict(self.rows)
        try:
            write_controller_config(self.path, {'version': 1, 'shelves': snapshot})
        except OSError:
            pass
