"""Build the controller's default discovery identities from the installer catalog."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'installer-source/plugin.program.blacklanturninstaller/resources/discovery-lineup.json'
RESOURCES = ROOT / 'controller-source/addon/resources'
ENGLISH = RESOURCES / 'language/resource.language.en_gb/strings.po'
INDEX = RESOURCES / 'discovery-localization.json'

# Kodi 21.3 genre/program categories with the same meaning as these shelves.
KODI_IDS = {
    'Video add-ons': 1037, 'Program add-ons': 1043,
    'Comedy': 19504, 'Romance': 19506, 'Documentary': 19519,
    'Drama': 19676, 'Talk': 29939, 'News': 29941, 'Travel': 29962,
}

# Exact Home and Add-ons defaults shared by the two clean build editions.
HOME_ROWS = (
    ('Recommended shows', 'trakt_recommendations', 'tv'),
    ('Recommended movies', 'trakt_recommendations', 'movie'),
    ('Trending shows', 'trakt_trending', 'tv'),
    ('Trending movies', 'trakt_trending', 'movie'),
    ('Continue watching · episodes', 'trakt_ondeck', 'tv'),
    ('Continue watching · movies', 'trakt_inprogress', 'movie'),
    ('Next episodes', 'trakt_nextepisodes', 'tv'),
    ('Shows this week', 'trending_week', 'tv'),
    ('Movies this week', 'trending_week', 'movie'),
)
ADDON_ROWS = (('Video add-ons', 'video'), ('Program add-ons', 'program'))


def helper_path(info, kind):
    return 'plugin://plugin.video.themoviedb.helper/?' + urlencode({
        'info': info, 'tmdb_type': kind, 'nextpage': 'true', 'widget': 'true',
    })


def runtime_defaults():
    sys.path.insert(0, str(RESOURCES.parent))
    from adaptive_services import _PROFILES
    from live_core import my_stuff_rows
    from streaming_shelves import GENRES, MOVIE_GENRES, SHOW_GENRES, BASE_LABELS

    rows = {
        'Home': [{'label': label, 'path': helper_path(info, kind)} for label, info, kind in HOME_ROWS],
        'Add-ons': [{'label': label, 'path': 'plugin://script.blacklanturn.preview/?info=installed_addons&category=' + kind}
                    for label, kind in ADDON_ROWS],
        'My Stuff': my_stuff_rows([], helper_path),
    }
    streaming = set(BASE_LABELS)
    streaming.update(label for label, *_ in GENRES + MOVIE_GENRES + SHOW_GENRES)
    streaming.update(label for profile in _PROFILES.values() for rows in profile.values() for label, _ in rows)
    return rows, streaming


def index_contents():
    phrases = {json.loads(text): int(number) for number, text in re.findall(
        r'^msgctxt "#(\d+)"\nmsgid (".*")$', ENGLISH.read_text(encoding='utf-8'), re.M)}
    for prefix in ('Classic', 'Modern', '2020s'):
        phrases[prefix + ' favourites'] = phrases.pop(prefix + ' Favourites')
    phrases.update(KODI_IDS)
    defaults = json.loads(CATALOG.read_text(encoding='utf-8'))['defaults']
    pages = {page['id']: page for group in ('Genres', 'Categories') for page in defaults[group]}
    shelf_groups = {group: defaults[group] for group in ('Movies', 'Shows')}
    shelf_groups.update({key: page['rows'] for key, page in pages.items()})
    extra_rows, streaming = runtime_defaults()
    shelf_groups.update(extra_rows)

    def identity(row):
        return hashlib.sha256((row['label'] + '\0' + row['path']).encode('utf-8')).hexdigest()

    rows = {key: {identity(row): phrases[row['label']] for row in entries}
            for key, entries in shelf_groups.items()}
    names = {key: [page['label'], phrases[page['label']]] for key, page in pages.items()}
    streaming_ids = {label: phrases[label] for label in streaming}
    return json.dumps({'pages': names, 'rows': rows, 'streaming': streaming_ids}, indent=2, sort_keys=True) + '\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Check the generated file without editing it')
    if parser.parse_args().check:
        if INDEX.read_text(encoding='utf-8') != index_contents():
            raise SystemExit('Discovery localization index is out of date')
    else:
        INDEX.write_text(index_contents(), encoding='utf-8')
