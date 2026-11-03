"""An ordered, profile-local list of exact movies and individual episodes."""
from copy import deepcopy
import json
import re
from urllib.parse import parse_qs, urlencode, urlsplit

HELPER = 'plugin://plugin.video.themoviedb.helper/'
FIELD = 'WatchTonight'
MAX_ITEMS = 200
SNAPSHOT_FIELDS = (
    'label', 'title', 'showtitle', 'tvshowtitle', 'year', 'premiered', 'plot',
    'art', 'thumbnail', 'uniqueid', 'runtime', 'mpaa', 'genre',
)


def helper_query(item):
    if not isinstance(item, dict) or item.get('_page_control'):
        return {}
    path = item.get('file')
    if not isinstance(path, str):
        return {}
    try:
        source = urlsplit(path)
    except ValueError:
        return {}
    if (source.scheme, source.netloc, source.path) != ('plugin', 'plugin.video.themoviedb.helper', '/'):
        return {}
    return parse_qs(source.query, keep_blank_values=True)


def number(value):
    text = str(value)
    if re.fullmatch(r'[0-9]{1,12}', text):
        return int(text)
    return None


def item_key(item):
    query = helper_query(item)
    route = query.get('info')
    if route not in (['play'], ['details']):
        return None
    ids = query.get('tmdb_id', [])
    ident = number(ids[0]) if len(ids) == 1 else None
    if not ident:
        return None
    kind = query.get('tmdb_type')
    if kind == ['movie'] and not {'season', 'episode'}.intersection(query):
        if item.get('type') in (None, '', 'movie', 'unknown') and (route == ['details'] or item.get('filetype') != 'directory'):
            return ('movie', ident)
        return None
    if kind != ['tv'] or item.get('type') in ('movie', 'season', 'tvshow'):
        return None
    season = query.get('season', [item.get('season')])
    episode = query.get('episode', [item.get('episode')])
    if len(season) == len(episode) == 1 and number(season[0]) is not None and number(episode[0]):
        if item.get('filetype') != 'directory' or route == ['details'] and 'episode' in query:
            return ('episode', ident, number(season[0]), number(episode[0]))
    return None


def playable(item, key):
    kind, ident, *coordinates = key
    query = {'info': 'play', 'tmdb_type': 'tv' if coordinates else 'movie', 'tmdb_id': ident}
    result = dict(item, type=kind, filetype='file')
    if coordinates:
        season, episode = coordinates
        query.update(season=season, episode=episode)
        result.update(season=season, episode=episode)
    result['file'] = HELPER+'?'+urlencode(query)
    return result


def label(item):
    from live_core import episode_heading
    title, episode = episode_heading(item)
    if not episode:
        return title or 'Movie'
    return f'{title} · {episode}' if item.get('showtitle') or item.get('tvshowtitle') else episode


def _validated(config):
    items = config.get(FIELD, [])
    if isinstance(items, list) and len(items) <= MAX_ITEMS:
        keys = [item_key(item) for item in items]
        if all(keys) and len(set(keys)) == len(keys):
            return items
    raise ValueError('Watch Tonight could not be read. The saved queue was kept.')


def entries(config):
    return deepcopy(_validated(config))


def contains(config, key):
    return any(item_key(item) == key for item in _validated(config))


def _update(config, items):
    value = dict(config, **{FIELD: items})
    if len(items) > MAX_ITEMS or len(json.dumps(value, indent=2, allow_nan=False).encode()) > 3*1024*1024:
        raise ValueError('Watch Tonight is full. Remove an item first.')
    return value


def toggle(config, item):
    key = item_key(item)
    if key is None:
        raise ValueError('Choose a movie or an individual episode.')
    items = entries(config)
    if any(item_key(saved) == key for saved in items):
        return _update(config, [saved for saved in items if item_key(saved) != key])
    saved = playable({field: item[field] for field in SNAPSHOT_FIELDS if field in item}, key)
    if len(json.dumps(saved).encode()) > 32768:
        raise ValueError('This title contains too much saved metadata.')
    items.append(saved)
    return _update(config, items)


def edit(config, key, action):
    items = entries(config)
    index = next((n for n, item in enumerate(items) if item_key(item) == key), None)
    if index is None:
        raise ValueError('This title is no longer in Watch Tonight.')
    if action == 'remove':
        items.pop(index)
    elif action in ('up', 'down'):
        target = index + (-1 if action == 'up' else 1)
        if not 0 <= target < len(items):
            return config
        items[index], items[target] = items[target], items[index]
    else:
        raise ValueError('Unknown Watch Tonight action.')
    return _update(config, items)
