"""An on-demand seven-day view of TMDb Helper's personal Trakt airings."""
from datetime import date, datetime, timedelta
from urllib.parse import urlencode

from browse_controls import is_next_page
from watch_tonight import HELPER, helper_query, item_key, number, playable

DAYS = 7


def calendar_path():
    # Widget requests can hide Helper's Next page according to a user setting.
    return HELPER+'?'+urlencode({'info': 'trakt_calendar', 'tmdb_type': 'tv', 'startdate': 0,
                                 'days': DAYS, 'user': 'true', 'nextpage': 'true', 'widget': 'false'})


def load_airings(path, provider, current):
    items = []
    for _ in range(20):
        if not current():
            return []
        page = [item for item in provider(path) if isinstance(item, dict)]
        if not current():
            return []
        next_page = next((item for item in page if is_next_page(item, path)), None)
        items.extend(item for item in page if item is not next_page)
        if next_page is None:
            return items
        path = next_page['file']
    raise ValueError('Trakt calendar pagination limit reached')


def _air_day(item):
    # Helper's Kodi JSON-RPC export normally carries an already-local date.
    for field in ('first_aired', 'firstaired', 'premiered'):
        value = item.get(field)
        if not isinstance(value, str):
            continue
        try:
            return date.fromisoformat(value)
        except ValueError:
            try:
                stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
                if stamp.tzinfo is not None:
                    return stamp.astimezone().date()
            except ValueError:
                continue
    return None


def _episodes(item):
    key = item_key(item)
    if key and key[0] == 'episode':
        yield key, _air_day(item), playable(item, key)
        return
    query = helper_query(item)
    if query.get('info') != ['specified_episodes'] or query.get('tmdb_type') != ['tv']:
        return
    # Helper can group episodes with the same date into a folder. The folder
    # exports their coordinates but does not carry the shared air date.
    ids, groups = query.get('tmdb_id', []), query.get('episodes', [])
    ident = number(ids[0]) if len(ids) == 1 else None
    if not ident or len(groups) != 1:
        return
    show = item.get('title') or item.get('label') or 'Show'
    for coordinate in groups[0].split('/'):
        season, _, episode = coordinate.partition('x')
        season, episode = number(season), number(episode)
        if season is not None and episode:
            key = ('episode', ident, season, episode)
            metadata = {'label': f'Episode {episode}', 'showtitle': show, 'art': item.get('art') or {}}
            yield key, None, playable(metadata, key)


def group_airings(items, today):
    unique = {}
    for item in items:
        for key, day, episode in _episodes(item):
            if key not in unique or day is not None and unique[key][0] is None:
                unique[key] = day, episode
    groups = {}
    end = today + timedelta(days=DAYS)
    for day, episode in unique.values():
        if day is None or today <= day < end:
            groups.setdefault(day, []).append(episode)
    ordered = {day: groups[day] for day in sorted(day for day in groups if day is not None)}
    if None in groups:
        ordered[None] = groups[None]
    return ordered
