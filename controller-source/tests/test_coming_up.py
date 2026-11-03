from datetime import date, timedelta
from urllib.parse import parse_qs, urlsplit
import unittest

import coming_up
from test_watch_tonight import EPISODE, HELPER

TODAY = date(2026, 11, 3)


class ComingUp(unittest.TestCase):
    def test_groups_seven_inclusive_local_days_and_preserves_unknown(self):
        items = [dict(EPISODE, file=EPISODE['file'].replace('episode=2', f'episode={n}'),
                      premiered=(TODAY+timedelta(days=offset)).isoformat())
                 for n, offset in enumerate((6, -1, 7, 0), 1)]
        unknown = dict(EPISODE, premiered='', file=EPISODE['file'].replace('episode=2', 'episode=9'))
        dated = coming_up.group_airings(items+[unknown], TODAY)
        self.assertEqual(list(dated), [TODAY, TODAY+timedelta(days=6), None])
        self.assertEqual([row[0]['episode'] for row in dated.values()], [4, 1, 9])

    def test_stack_expands_exact_episodes_with_unknown_dates(self):
        stack = {'file': HELPER+'info=specified_episodes&tmdb_type=tv&tmdb_id=25&episodes=1x02%2F2x03',
                 'filetype': 'directory', 'title': 'Show', 'premiered': TODAY.isoformat()}
        groups = coming_up.group_airings([stack], TODAY)
        self.assertEqual(list(groups), [None])
        self.assertEqual([(item['season'], item['episode']) for item in groups[None]], [(1, 2), (2, 3)])
        self.assertTrue(all(item['showtitle']=='Show' for item in groups[None]))

    def test_provider_follows_only_the_same_personal_calendar_and_honors_cancellation(self):
        path = coming_up.calendar_path()
        query = parse_qs(urlsplit(path).query)
        self.assertEqual({key: query[key][0] for key in ('info', 'user', 'days', 'widget')},
                         {'info': 'trakt_calendar', 'user': 'true', 'days': '7', 'widget': 'false'})
        next_page = {'file': path+'&page=2', 'filetype': 'directory'}
        calls = []
        def provider(url):
            calls.append(url)
            return [next_page] if url==path else [EPISODE]
        self.assertEqual(coming_up.load_airings(path, provider, lambda: True), [EPISODE])
        self.assertEqual(calls, [path, next_page['file']])
        calls.clear()
        self.assertEqual(coming_up.load_airings(path, provider, lambda: not calls), [])
        self.assertEqual(calls, [path])
