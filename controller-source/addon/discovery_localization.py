"""Offline presentation names for built-in shelves and discovery pages."""
from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path


@lru_cache(maxsize=1)
def _localization_index():
    path = Path(__file__).with_name('resources') / 'discovery-localization.json'
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {'pages': {}, 'rows': {}, 'streaming': {}}


def _localized(string_id, label):
    if not string_id:
        return label
    # Kodi loads the active interface catalog and falls back to en_GB.
    try:
        if string_id < 32000:
            import xbmc
            return xbmc.getLocalizedString(string_id) or label
        import xbmcaddon
        return xbmcaddon.Addon('script.blacklanturn.preview').getLocalizedString(string_id) or label
    except ImportError:
        return label


def localized_page_label(page_id, label):
    source, string_id = _localization_index()['pages'].get(page_id, (None, None))
    return _localized(string_id, label) if label == source else label


def localized_shelf_label(scope, row):
    label = row.get('label', 'Row')
    path = row.get('path')
    if not scope or not isinstance(label, str) or not isinstance(path, str):
        return label
    if scope == 'My Stuff' and row.get('id'):
        return label
    defaults = _localization_index()['rows'].get(scope)
    if not defaults:
        return label
    identity = sha256((label + '\0' + path).encode('utf-8')).hexdigest()
    return _localized(defaults.get(identity), label)


def display_page_rows(scope, rows):
    if not scope or scope not in _localization_index()['rows']:
        return list(rows)
    display_rows = []
    for row in rows:
        label = localized_shelf_label(scope, row)
        if label != row['label']:
            row = dict(row, label=label, _canonical_label=row['label'])
        display_rows.append(row)
    return display_rows


def display_streaming_rows(rows):
    strings = _localization_index()['streaming']
    for row in rows:
        canonical = row['label']
        label = _localized(strings.get(canonical), canonical)
        if label != canonical:
            row.update(label=label, _canonical_label=canonical)
