"""On-demand TMDb/JustWatch regional catalogs and a profile-local country choice."""
from http.client import HTTPException
import json
import os
from pathlib import Path
import re
import ssl
import sys
import tempfile
from threading import Lock
import time
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib import request

from shelf_tools import HELPER, streaming_folders

_HELPER_ID = 'plugin.video.themoviedb.helper'
_API_BASES = ('https://api.themoviedb.org/3', 'https://api.tmdb.org/3')
_MEDIA = ('movie', 'tv')
_REGION = re.compile(r'[A-Z]{2}')
_ID = re.compile(r'[1-9][0-9]{0,8}')
_LOGO = re.compile(r'/[A-Za-z0-9_-]{1,128}\.(?:png|jpe?g|webp)')
_TEXT_CONTROLS = re.compile(r'[\x00-\x1f\x7f-\x9f\ud800-\udfff]')
_MAX_NETWORK_BYTES = 1024 * 1024
_MAX_SNAPSHOT_BYTES = 512 * 1024
_PROVIDER_TTL = 5 * 60
_VERIFIED_EMPTY_TTL = 10 * 60
_REGION_TTL = 7 * 24 * 60 * 60
_WRITE_LOCK = Lock()


def _region_code(value):
    return isinstance(value, str) and _REGION.fullmatch(value) is not None


def _addon(addon_id):
    import xbmcaddon

    return xbmcaddon.Addon(addon_id)


def _addon_path(addon_id):
    path = _addon(addon_id).getAddonInfo('path')
    if path.startswith('special://'):
        import xbmcvfs

        path = xbmcvfs.translatePath(path)
    root = Path(path)
    if not root.is_absolute():
        raise ValueError('Kodi addon path unavailable')
    return root


def _enable_helper_import():
    root = str(_addon_path(_HELPER_ID) / 'resources')
    if root not in sys.path:
        sys.path.insert(0, root)


def default_region():
    """Read Helper's current metadata country without making a request."""
    try:
        _enable_helper_import()
        from tmdbhelper.lib.addon.plugin import get_language

        code = get_language().rsplit('-', 1)[-1]
        if _region_code(code):
            return code
    except (AttributeError, ImportError, IndexError, OSError, RuntimeError, ValueError):
        pass
    return 'US'


def helper_region_names():
    """Read offline display names. Only the live or saved region list defines picker membership."""
    try:
        _enable_helper_import()
        from tmdbhelper.lib.addon.consts import DISCOVER_REGIONS

        return {
            entry['id']: entry['name'].removesuffix(f" ({entry['id']})")
            for entry in DISCOVER_REGIONS
            if isinstance(entry, dict) and _region_code(entry.get('id')) and _name(entry.get('name'))
        }
    except (AttributeError, ImportError, OSError, RuntimeError, TypeError, ValueError):
        return {}


class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _tls_context():
    try:
        bundle = _addon_path('script.module.certifi') / 'lib/certifi/cacert.pem'
        if not bundle.is_file():
            return None
    except (AttributeError, ImportError, OSError, RuntimeError, ValueError):
        return None
    # Use the CA bundle shipped by Kodi, including on platforms without a
    # Python trust store. A broken installed bundle fails before connecting.
    return ssl.create_default_context(cafile=str(bundle))


def _title_id(value):
    text = str(value)
    return re.fullmatch(r'[1-9][0-9]{0,9}', text) and int(text) <= 2147483647


def fetch_public_tmdb(*parts, **filters):
    """Make one bounded GET using the installed Helper's public TMDb client."""
    allowed = (
        (parts == ('watch', 'providers', 'regions') and not filters)
        or (len(parts) == 3 and parts[:2] == ('watch', 'providers') and parts[2] in _MEDIA
            and filters.keys() == {'watch_region'} and _region_code(filters['watch_region']))
        or (len(parts) == 4 and parts[0] in _MEDIA and _title_id(parts[1])
            and parts[2:] == ('watch', 'providers') and not filters)
    )
    if not allowed:
        raise ValueError('Unsupported public provider request')
    try:
        _enable_helper_import()
        from tmdbhelper.lib.api.tmdb.api import TMDbAPI

        api = TMDbAPI()
        if api.req_api_url not in _API_BASES or not re.fullmatch(r'[a-z]{2}-[A-Z]{2}', api.req_language):
            raise ValueError
        parts = tuple(map(str, parts))
        params = dict(filters, language=api.req_language)
        url = api.get_request_url(*parts, **params)
        parsed = urlsplit(url)
        query = parse_qs(parsed.query, keep_blank_values=True)
        base = f'{parsed.scheme}://{parsed.netloc}'
        if (base + '/3' != api.req_api_url or parsed.path != '/3/' + '/'.join(parts) or parsed.fragment
                or query.keys() != params.keys() | {'api_key'}
                or not query['api_key'][0] or len(query['api_key']) != 1
                or any(query[key] != [value] for key, value in params.items())):
            raise ValueError
        opener = request.build_opener(_NoRedirect(), request.HTTPSHandler(context=_tls_context()))
        with opener.open(request.Request(url, headers={'Accept': 'application/json'}), timeout=4) as response:
            if response.status != 200:
                raise ValueError
            raw = response.read(_MAX_NETWORK_BYTES + 1)
        if len(raw) > _MAX_NETWORK_BYTES:
            raise ValueError
        value = json.loads(raw)
        if not isinstance(value, dict) or value.get('success') is False:
            raise ValueError
        return value
    except (AttributeError, HTTPException, ImportError, IndexError, OSError, RecursionError, RuntimeError, TypeError, ValueError):
        # URL-bearing transport errors can include the API credential.
        raise ValueError('Public provider request failed') from None


def _name(value):
    return (isinstance(value, str) and 0 < len(value) <= 160 and bool(value.strip())
            and not _TEXT_CONTROLS.search(value))


def _regions(rows):
    if not isinstance(rows, list) or not 0 < len(rows) <= 676:
        raise ValueError
    codes = set()
    records = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError
        code = row.get('iso_3166_1')
        name = row.get('english_name') or row.get('native_name')
        if not _region_code(code) or code in codes or not _name(name):
            raise ValueError
        codes.add(code)
        records.append({'iso_3166_1': code, 'english_name': name})
    return records


def _providers(rows):
    if not isinstance(rows, list) or len(rows) > 512:
        raise ValueError
    ids = set()
    records = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError
        ident = row.get('provider_id')
        name = row.get('provider_name')
        logo = row.get('logo_path')
        priority = row.get('display_priority')
        if (type(ident) is not int or not 0 < ident <= 999999999 or ident in ids or not _name(name)
                or type(priority) is not int or not 0 <= priority <= 999999
                or (logo is not None and (not isinstance(logo, str) or not _LOGO.fullmatch(logo)))):
            raise ValueError
        ids.add(ident)
        records.append(dict(provider_id=ident, provider_name=name, logo_path=logo, display_priority=priority))
    # Each explicitly regional response supplies its own display priorities.
    return sorted(records, key=lambda row: row['display_priority'])


def _cards(rows, kind, region):
    allowed = _addon(_HELPER_ID).getSettingString('provider_allowlist')
    allowlist = set(allowed.split(' | ')) if allowed else None
    files = []
    for row in rows:
        name = row['provider_name']
        if allowlist is not None and name not in allowlist:
            continue
        logo = row['logo_path']
        art = {'icon': 'https://image.tmdb.org/t/p/w185' + logo} if logo else {}
        params = dict(info='discover', tmdb_type=kind, with_watch_providers=row['provider_id'], watch_region=region)
        files.append(dict(file=HELPER + '?' + urlencode(params), filetype='directory', label=name, art=art))
    return streaming_folders(files, kind)


def _read_json(path, limit):
    try:
        with path.open('rb') as stream:
            raw = stream.read(limit + 1)
        if len(raw) <= limit:
            document = json.loads(raw)
            if isinstance(document, dict) and type(document.get('version')) is int and document['version'] == 1:
                return document
    except (OSError, ValueError, RecursionError):
        pass
    return {}


def _write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=path.name + '.', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, separators=(',', ':'))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


class RegionalCatalog:
    default_region = staticmethod(default_region)

    def __init__(self, profile, fetch=None, clock=time.time):
        base = Path(profile) / 'addon_data/script.blacklanturn.preview'
        self.preference = base / 'streaming-service-region.json'
        self.directory = base / 'streaming-regional-catalog'
        self.fetch = fetch if fetch is not None else fetch_public_tmdb
        self.clock = clock

    def selected(self, default):
        saved = _read_json(self.preference, 1024).get('region')
        return saved if _region_code(saved) else default

    def select(self, code):
        if not _region_code(code):
            return False
        try:
            with _WRITE_LOCK:
                _write_json(self.preference, {'version': 1, 'region': code})
        except OSError:
            return False
        return True

    def _read_snapshot(self, key, validate):
        document = _read_json(self.directory / (key + '.json'), _MAX_SNAPSHOT_BYTES)
        stamp = document.get('time')
        if (document.get('scope') == key and type(stamp) in (int, float)
                and 0 <= stamp <= self.clock()):
            try:
                return validate(document.get('results')), stamp
            except ValueError:
                pass
        return None, None

    def _snapshot(self, key, validate, ttl, *parts, **filters):
        rows, stamp = self._read_snapshot(key, validate)
        if stamp is not None and self.clock() - stamp < ttl:
            return rows, 'fresh'
        started = self.clock()
        try:
            response = self.fetch(*parts, **filters)
            if (not isinstance(response, dict) or response.get('success') is False
                    or response.get('watch_region', filters.get('watch_region')) != filters.get('watch_region')):
                raise ValueError
            results = validate(response.get('results'))
        except (OSError, ValueError, RuntimeError, RecursionError):
            # Another refresh may have succeeded while this request was waiting.
            rows, stamp = self._read_snapshot(key, validate)
            if stamp is not None:
                return rows, 'fresh' if self.clock() - stamp < ttl else 'stale'
            return None, 'error'
        with _WRITE_LOCK:
            current, saved = self._read_snapshot(key, validate)
            if saved is not None and saved >= started:
                return current, 'fresh'
            try:
                _write_json(self.directory / (key + '.json'),
                            dict(version=1, scope=key, time=self.clock(), results=results))
            except OSError:
                # A profile write error does not erase a successful live response.
                pass
        return results, 'fresh'

    @staticmethod
    def _country_names(rows):
        return {row['iso_3166_1']: row['english_name'] for row in rows or ()}

    def cached_regions(self):
        rows, stamp = self._read_snapshot('regions', _regions)
        return self._country_names(rows), stamp is not None and self.clock() - stamp < _REGION_TTL

    def regions(self):
        rows, state = self._snapshot('regions', _regions, _REGION_TTL, 'watch', 'providers', 'regions')
        return self._country_names(rows), state

    def cached(self, kind, region):
        if kind not in _MEDIA or not _region_code(region):
            return None, False
        rows, stamp = self._read_snapshot(f'{kind}-{region}', _providers)
        if rows is not None:
            try:
                return _cards(rows, kind, region), self.clock() - stamp < _PROVIDER_TTL
            except (AttributeError, ImportError, OSError, RuntimeError):
                pass
        return None, False

    def load(self, kind, region):
        if kind not in _MEDIA or not _region_code(region):
            return None, 'error'
        rows, state = self._snapshot(f'{kind}-{region}', _providers, _PROVIDER_TTL,
                                     'watch', 'providers', kind, watch_region=region)
        if rows is not None:
            try:
                return _cards(rows, kind, region), state
            except (AttributeError, ImportError, OSError, RuntimeError):
                return None, 'error'
        return None, state

    def _empty_stamps(self, key):
        document = _read_json(self.directory / (key + '.json'), 32 * 1024)
        stamps = document.get('providers')
        if document.get('scope') != key or not isinstance(stamps, dict) or len(stamps) > 512:
            return {}
        now = self.clock()
        return {
            provider: stamp for provider, stamp in stamps.items()
            if _ID.fullmatch(provider) and type(stamp) in (int, float)
            and now - _VERIFIED_EMPTY_TTL < stamp <= now
        }

    def mark_empty(self, kind, region, provider_id):
        """Remember a verified successful zero from the exact unfiltered Browse All route."""
        return self._change_empty(kind, region, provider_id, empty=True)

    def mark_available(self, kind, region, provider_id):
        """Clear a previous zero when the exact Browse All route returns titles."""
        return self._change_empty(kind, region, provider_id, empty=False)

    def _change_empty(self, kind, region, provider_id, *, empty):
        provider_id = str(provider_id)
        if kind not in _MEDIA or not _region_code(region) or not _ID.fullmatch(provider_id):
            return False
        key = f'empty-{kind}-{region}'
        try:
            with _WRITE_LOCK:
                stamps = self._empty_stamps(key)
                if empty:
                    if provider_id not in stamps and len(stamps) >= 512:
                        return False
                    stamps[provider_id] = self.clock()
                elif stamps.pop(provider_id, None) is None:
                    return True
                _write_json(self.directory / (key + '.json'), dict(version=1, scope=key, providers=stamps))
        except OSError:
            return False
        return True

    def visible(self, cards, kind, region):
        """Return the display view without removing providers from regional membership."""
        if kind not in _MEDIA or not _region_code(region):
            return list(cards)
        stamps = self._empty_stamps(f'empty-{kind}-{region}')
        if not stamps:
            return list(cards)

        def verified_empty(card):
            route = urlsplit(card.get('file', ''))
            if (route.scheme, route.netloc, route.path) != ('plugin', _HELPER_ID, '/'):
                return False
            params = parse_qs(route.query)
            providers = params.get('with_watch_providers', [])
            return (params.get('tmdb_type') == [kind] and params.get('watch_region') == [region]
                    and len(providers) == 1 and providers[0] in stamps)

        return [card for card in cards if not verified_empty(card)]
