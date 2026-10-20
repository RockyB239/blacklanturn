"""Explicit TV pack preferences; match only current, playable scrape results."""
import json
import os
import sqlite3


def scope(meta):
    if not isinstance(meta, dict) or meta.get('episode') in (None, '', 'None'):
        return None
    # TMDb distinguishes split series which can share an IMDb ID.
    for name in ('tmdb', 'imdb', 'tvdb'):
        value = meta.get(name)
        if value not in (None, '', '0', 0, 'None'):
            try:
                return '%s:%s' % (name, value), str(int(meta['season']))
            except (KeyError, TypeError, ValueError):
                return None


def eligible(item):
    return (item.get('package') in ('season', 'show') and bool(item.get('hash'))
            and item.get('url', '').startswith('magnet:')
            and bool(item.get('debrid')) and 'uncached' not in item.get('source', '').lower())


def _connection():
    from resources.lib.modules import control
    os.makedirs(control.dataPath, exist_ok=True)
    connection = sqlite3.connect(os.path.join(control.dataPath, 'source_preferences.db'), timeout=5)
    connection.execute('CREATE TABLE IF NOT EXISTS preferences (show TEXT, season TEXT, data TEXT, PRIMARY KEY(show, season))')
    return connection


def get(meta):
    key = scope(meta)
    if not key:
        return None
    connection = _connection()
    try:
        row = connection.execute('SELECT data FROM preferences WHERE show=? AND season=?', key).fetchone()
        return json.loads(row[0]) if row else None
    finally:
        connection.close()


def save(meta, item):
    key = scope(meta)
    if not key or not eligible(item):
        return False
    data = {'hash': item['hash'].lower(), 'debrid': item['debrid'], 'name': item.get('name', '')}
    connection = _connection()
    try:
        with connection:
            connection.execute('INSERT OR REPLACE INTO preferences VALUES (?, ?, ?)', key + (json.dumps(data),))
    finally:
        connection.close()
    return True


def clear(meta):
    key = scope(meta)
    if not key:
        return
    connection = _connection()
    try:
        with connection:
            connection.execute('DELETE FROM preferences WHERE show=? AND season=?', key)
    finally:
        connection.close()


def matching(items, preference):
    return [item for item in items if eligible(item)
            and item['hash'].lower() == preference['hash']
            and item['debrid'] == preference['debrid']]


# Runtime-only preferences: never write account or global quality settings.
SESSION_PROPERTY = 'BlackLanturn.SourceSession.v1'


def _positive_size(item):
    import math
    try:
        size = float(item.get('size') or 0)
        return size if math.isfinite(size) and size > 0 else None
    except (TypeError, ValueError):
        return None


def session_policy(meta, item, now):
    key = scope(meta)
    size = _positive_size(item)
    if not key or not size or not item.get('debrid') or item.get('cloud_folder') or 'uncached' in item.get('source', '').lower():
        return None
    try:
        episode = int(meta['episode'])
    except (TypeError, ValueError, KeyError):
        return None
    return {'scope': list(key), 'episode': episode, 'ceiling': size,
            'debrid': item['debrid'], 'hash': str(item.get('hash') or '').lower(),
            'created': now, 'version': 1}


def session_applies(policy, meta, now):
    try:
        return (isinstance(policy, dict) and policy.get('version') == 1 and list(scope(meta) or ()) == policy['scope']
                and int(meta['episode']) > policy['episode']
                and 0 <= now - float(policy['created']) < 21600
                and _positive_size({'size': policy['ceiling']}) is not None)
    except (KeyError, TypeError, ValueError):
        return False


def session_candidates(items, policy):
    """Rank existing results only; no resolver, provider or account requests."""
    ceiling = _positive_size({'size': policy.get('ceiling')})
    if not ceiling:
        return []
    candidates = [item for item in items
                  if item.get('debrid') == policy.get('debrid')
                  and not item.get('cloud_folder')
                  and 'uncached' not in item.get('source', '').lower()
                  and _positive_size(item) is not None
                  and _positive_size(item) <= ceiling]
    preferred_hash = policy.get('hash')
    return sorted(candidates, key=lambda item: (
        not (preferred_hash and str(item.get('hash') or '').lower() == preferred_hash),
        ceiling - _positive_size(item)))[:3]


def remember_session(meta, item, selected=None):
    from time import time
    from resources.lib.modules import control
    policy = session_policy(meta, selected or item, time())
    actual_size = _positive_size(item)
    if policy:
        if actual_size:
            policy['ceiling'] = min(policy['ceiling'], actual_size)
        if item.get('debrid') == policy['debrid']:
            policy['hash'] = str(item.get('hash') or '').lower()
    if policy:
        control.playerWindow.setProperty(SESSION_PROPERTY, json.dumps(policy))
    else:
        control.playerWindow.clearProperty(SESSION_PROPERTY)
    # Never consume a URL prepared under a superseded size/provider choice.
    control.playerWindow.clearProperty('umbrella.preResolved_nextUrl')


def get_session(meta):
    from time import time
    from resources.lib.modules import control
    try:
        policy = json.loads(control.playerWindow.getProperty(SESSION_PROPERTY) or '{}')
        return policy if session_applies(policy, meta, time()) else None
    except (ValueError, TypeError):
        return None


PREPARED_PROPERTY = 'umbrella.preResolved_sourceSession'


def session_stamp(meta):
    policy = get_session(meta)
    return json.dumps(policy, sort_keys=True, separators=(',', ':')) if policy else ''


def clear_session():
    from resources.lib.modules import control
    control.playerWindow.clearProperty(SESSION_PROPERTY)
    control.playerWindow.clearProperty(PREPARED_PROPERTY)
    control.playerWindow.clearProperty('umbrella.preResolved_nextUrl')
