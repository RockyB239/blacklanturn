"""Short-lived streaming availability snapshots, loaded only on demand."""
import re
from urllib.parse import parse_qs, urlsplit

from public_rows import PublicRowSnapshots, _item_path, _items


def _query(path):
    if not isinstance(path, str):
        return {}
    try:
        url = urlsplit(path)
        if (url.scheme, url.netloc, url.path) != ('plugin', 'plugin.video.themoviedb.helper', '/') or url.fragment:
            return {}
        fields = parse_qs(url.query, keep_blank_values=True)
        return {key: values[0] for key, values in fields.items()} if all(len(v) == 1 for v in fields.values()) else {}
    except ValueError:
        return {}


def _provider(fields, paging=False):
    if (fields.get('info') != 'discover' or fields.get('tmdb_type') not in ('movie', 'tv')
            or not re.fullmatch(r'[1-9][0-9]{0,8}', fields.get('with_watch_providers', ''))
            or not re.fullmatch(r'[A-Z]{2}', fields.get('watch_region', ''))
            or fields.get('with_id') != 'true' or fields.get('nextpage') != 'true'):
        return False
    allowed = {'info', 'tmdb_type', 'with_watch_providers', 'watch_region', 'with_id', 'nextpage', 'widget'}
    if not paging:
        return fields.get('widget') == 'false' and not fields.keys() - allowed
    return (not fields.keys() - allowed - {'page', 'cacheonly', 'plugin_category'}
            and re.fullmatch(r'[2-9]|[1-9][0-9]{1,2}', fields.get('page', ''))
            and fields.get('cacheonly', 'false').lower() in ('true', 'false')
            and fields.get('widget', 'false') == 'false'
            and len(fields.get('plugin_category', '')) <= 160)


def streaming_page_target(origin, target):
    before, after = _query(origin), _query(target)
    if not (_provider(before) or _provider(before, paging=True)):
        return target
    if 'widget' not in after and _provider(after, paging=True):
        return target + '&widget=false'
    return target


def _route(path):
    fields = _query(path)
    if fields.get('tmdb_type') not in ('movie', 'tv'):
        return None
    if (fields.get('info') == 'blacklanturn_streaming_services'
            and fields.get('nextpage') == fields.get('widget') == 'true'
            and fields.keys() == {'info', 'tmdb_type', 'nextpage', 'widget'}):
        return 'catalog'
    if _provider(fields):
        return 'titles'
    return None


def _title_path(path):
    fields = _query(path)
    if _provider(fields, paging=True):
        return path
    return _item_path(path) if fields.get('info') in ('play', 'details', 'seasons', 'episodes', 'flatseasons') else ''


class StreamingRows(PublicRowSnapshots):
    max_bytes = 768 * 1024
    max_rows = 8

    def __init__(self, directory, scope, mode, **kwargs):
        self.mode = mode
        self.max_age = 300 if mode == 'catalog' else 120
        super().__init__(directory / ('streaming-' + mode + '.json'), scope, **kwargs)

    @classmethod
    def for_route(cls, directory, scope, path, stores=None, **kwargs):
        mode = _route(path)
        if not scope or not mode:
            return None
        if stores is None:
            return cls(directory, scope, mode, **kwargs)
        store = stores.get(mode)
        if store is None or store.scope != scope:
            store = stores[mode] = cls(directory, scope, mode, **kwargs)
        return store

    def path_allowed(self, path):
        return _route(path) == self.mode

    def sanitize_items(self, files):
        if self.mode == 'catalog':
            items = _items(files, lambda path: path if _route(path) == 'titles' else '', max_items=512)
            if items and all(i.get('filetype') == 'directory' for i in items):
                return [dict(i, _streaming_provider=True) for i in items]
            return None
        return _items(files, _title_path)

    def _matches(self, path, files):
        source = _query(path)
        for item in files:
            if not isinstance(item, dict):
                return False
            target = _query(item.get('file'))
            if target.get('tmdb_type') != source.get('tmdb_type'):
                return False
            if self.mode == 'titles' and target.get('info') == 'discover' and any(
                    target.get(k) != source.get(k) for k in ('with_watch_providers', 'watch_region')):
                return False
        return True

    def get(self, path):
        with self.lock:
            row = self.rows.get(path)
            if row and self.clock() - row['time'] >= self.max_age:
                self.rows.pop(path)
            files = super().get(path)
            return files if files and self._matches(path, files) else None

    def put(self, path, files, revision=None):
        return bool(files and self._matches(path, files) and super().put(path, files, revision=revision))

    def discard(self, path):
        with self.lock:
            self.revision += 1
            if self.rows.pop(path, None) is not None:
                try:
                    self._write(self._encode(self.rows))
                except OSError:
                    self.clear()
