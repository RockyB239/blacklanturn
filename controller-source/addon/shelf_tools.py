"""Explicit browse actions over loaded shelves and TMDb Helper's regional catalog."""
import random
import re
import time
from urllib.parse import parse_qs, urlencode, urlsplit

from shelf_visits import title_key

SERVICE_ROUTE = 'blacklanturn_streaming_services'
HELPER = 'plugin://plugin.video.themoviedb.helper/'
RUNTIME_LIMITS = (90, 120)


def shelf_titles(files):
    titles = {}
    for item in files:
        if item.get('type') in ('season', 'episode', 'person', 'addon'):
            continue
        key = title_key(item)
        if key:
            titles.setdefault(key, item)
    return list(titles.values())


def under_runtime(files, minutes):
    def matches(item):
        seconds = item.get('runtime')
        return title_key(item).startswith('movie:') and type(seconds) in (int, float) and 0 < seconds < minutes * 60
    return [item for item in shelf_titles(files) if matches(item)]


def visit_key(window, slot):
    return window.section, getattr(window, 'active_page', None) or '', window.paths[slot]


def new_shelf_titles(window, slot, files):
    marked = getattr(window, 'shelf_visit_badges', {}).get(visit_key(window, slot), set())
    return [item for item in shelf_titles(files) if title_key(item) in marked]


def pick_three(files, sample=random.sample):
    titles = shelf_titles(files)
    return sample(titles, min(3, len(titles)))


def streaming_folders(files, kind):
    cards = {}
    for item in files:
        if item.get('filetype') != 'directory':
            continue
        route = urlsplit(item.get('file', ''))
        if (route.scheme, route.netloc, route.path) != ('plugin', 'plugin.video.themoviedb.helper', '/'):
            continue
        query = parse_qs(route.query)
        provider = query.get('with_watch_providers', [''])[0]
        region = query.get('watch_region', [''])[0]
        name = item.get('title') or item.get('label')
        if (query.get('info') != ['discover'] or query.get('tmdb_type') != [kind]
                or not re.fullmatch(r'[1-9][0-9]{0,8}', provider)
                or not re.fullmatch(r'[A-Z]{2}', region)
                or len(query.get('with_watch_providers', [])) != 1
                or len(query.get('watch_region', [])) != 1 or not name):
            continue
        params = dict(info='discover', tmdb_type=kind, with_watch_providers=provider,
                      watch_region=region, with_id='true', nextpage='true', widget='false')
        label = f'{name} · {region}'
        cards.setdefault((provider, region), dict(item, label=label, title=label,
                         plot='Regional availability from TMDb and JustWatch.',
                         file=HELPER + '?' + urlencode(params), _streaming_provider=True))
    return list(cards.values())


class ShelfTools:
    def shelf_actions(self, focus, genre_available):
        actions = []
        if self.shelf_choices(focus):
            actions.append(('shelf_tools', 'Shelf tools…'))
        if genre_available:
            actions.append(('streaming_services', 'Browse by streaming service…'))
        return actions

    def shelf_choices(self, focus):
        if (focus not in (900, 901) or self.mode != 'home'
                or self.section not in ('Movies', 'Shows', 'My Stuff')
                or any(getattr(self, name, None) for name in
                       ('nav', 'search_state', 'episode_browser_context', 'person_context'))):
            return []
        slot = focus - 900
        index = self.row_offset + slot
        if index >= len(self.page_definitions) or self.page_definitions[index].get('_current_shelf_view'):
            return []
        titles = shelf_titles(self.rows[slot])
        if not titles:
            return []
        choices = []
        if any(title_key(item).startswith('movie:') for item in titles):
            choices.extend((limit, f'Under {limit} minutes') for limit in RUNTIME_LIMITS)
        if visit_key(self, slot) in getattr(self, 'shelf_visit_badges', {}):
            choices.append(('new', 'Show new titles'))
        choices.append(('pick', 'Pick Three'))
        return choices

    def show_shelf_tools(self, focus):
        import xbmcgui

        choices = self.shelf_choices(focus)
        if not choices:
            return
        slot = focus - 900
        generation = self.generation
        shelf = self.rows[slot]
        label = self.row_labels.get(slot, 'Current shelf')
        self.actions_open = True
        try:
            dialog = xbmcgui.Dialog()
            selected = dialog.select(label, [name for _, name in choices])
            if selected < 0 or not self.alive or generation != self.generation or self.rows[slot] is not shelf:
                return
            action, heading = choices[selected]
            if action == 'pick':
                picks = pick_three(shelf)
                labels = [f'{item.get("title") or item.get("label", "Title")}'
                          + (f' · {item["year"]}' if item.get('year') else '') for item in picks]
                selected = dialog.select('Pick Three', labels)
                if selected >= 0 and self.alive and generation == self.generation and self.rows[slot] is shelf:
                    self.getControl(focus).selectItem(shelf.index(picks[selected]))
                    self.details(picks[selected])
                return
            if action == 'new':
                files = new_shelf_titles(self, slot, shelf)
                empty = 'No titles are marked new on this shelf.'
            else:
                files = under_runtime(shelf, action)
                empty = 'No movies on this shelf have a known runtime under %d minutes.' % action
            if not files:
                dialog.ok(heading, empty)
                return
            self.open_discovery({'heading': label.upper() + ' / ' + heading.upper(), 'hide_captions': True,
                                 'rows': [{'label': heading + ' · Back to clear', 'path': '',
                                           'local_items': files, '_current_shelf_view': True}]})
            self.last_row = 0
        finally:
            self.dwell = time.monotonic()
            self.actions_open = False

    def browse_streaming_services(self, make_path):
        kind = {'Movies': 'movie', 'Shows': 'tv'}.get(self.section)
        if kind is None:
            return
        self.open_discovery({'heading': self.section.upper() + ' / STREAMING SERVICES',
                             'rows': [{'label': 'Streaming services · TMDb / JustWatch',
                                       'path': make_path(SERVICE_ROUTE, kind)}]})
        self.last_row = 0
