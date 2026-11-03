import random
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit
import unittest
from unittest.mock import patch

from shelf_tools import ShelfTools, shelf_titles, under_runtime, pick_three, new_shelf_titles, streaming_folders

TMDB = 'plugin://plugin.video.themoviedb.helper/?'
PUBLIC = TMDB + 'info=popular&tmdb_type=movie'


def movie(ident, runtime=None, **fields):
    return dict(file=TMDB + f'info=play&tmdb_type=movie&tmdb_id={ident}',
                label=f'Movie {ident}', runtime=runtime, **fields)


class ShelfToolsTests(unittest.TestCase):
    def test_runtime_limits_use_kodi_seconds_and_exclude_unknowns(self):
        files = [movie(1, 5399), movie(2, 5400), movie(3, 7199), movie(4, 7200),
                 movie(5, 0), movie(6), movie(7, float('nan')), movie(8, True)]
        self.assertEqual(under_runtime(files, 90), files[:1])
        self.assertEqual(under_runtime(files, 120), files[:3])

    def test_title_pool_excludes_folders_controls_episodes_and_duplicate_ids(self):
        first = movie(1, 3600)
        show = {'file': TMDB + 'info=seasons&tmdb_type=tv&tmdb_id=1', 'filetype': 'directory'}
        duplicate = dict(first, file=first['file'] + '&widget=true')
        episode = {'file': TMDB + 'info=play&tmdb_type=tv&tmdb_id=2&season=1&episode=2'}
        invalid = {'file': TMDB + 'info=discover&tmdb_type=movie&page=2', 'filetype': 'directory'}
        self.assertEqual(shelf_titles([first, duplicate, episode, invalid, show]), [first, show])

    def test_picks_are_three_distinct_titles_from_the_supplied_shelf(self):
        files = [movie(i) for i in range(1, 7)]
        picks = pick_three(files + [files[0]], sample=random.Random(7).sample)
        self.assertEqual(len({item['file'] for item in picks}), 3)
        self.assertTrue(all(item in files for item in picks))
        self.assertCountEqual(pick_three(files[:2]), files[:2])

    def test_new_titles_use_the_exact_shelf_visit_key(self):
        files = [movie(1), movie(2), movie(3)]
        state = SimpleNamespace(section='Movies', active_page='action', paths=[PUBLIC],
                                shelf_visit_badges={('Movies', 'action', PUBLIC): {'movie:2'},
                                                    ('Movies', 'drama', PUBLIC): {'movie:1'}})
        self.assertEqual(new_shelf_titles(state, 0, files), [files[1]])
        state.active_page = 'other'
        self.assertEqual(new_shelf_titles(state, 0, files), [])

    def test_streaming_folders_keep_only_valid_provider_region_pairs(self):
        from page_ahead import eligible
        from search_ui import discovery_result

        def folder(region='GB', ident='8', kind='movie'):
            return {'filetype': 'directory', 'label': 'Service',
                    'file': TMDB + f'info=discover&tmdb_type={kind}&with_watch_providers={ident}&watch_region={region}&with_id=True'}
        cards = streaming_folders([folder(), folder(''), folder('GB', '8,9'), folder('GB', kind='tv'),
                                   dict(folder(), file=folder()['file'].replace('plugin.video.themoviedb.helper', 'plugin.video.other'))], 'movie')
        self.assertEqual(len(cards), 1)
        self.assertEqual(parse_qs(urlsplit(cards[0]['file']).query), {
            'info': ['discover'], 'tmdb_type': ['movie'], 'with_watch_providers': ['8'], 'watch_region': ['GB'],
            'with_id': ['true'], 'nextpage': ['true'], 'widget': ['false']})
        self.assertIn('GB', cards[0]['label'])
        view = discovery_result(cards[0])
        self.assertEqual(view['rows'][0]['path'], cards[0]['file'])
        self.assertFalse(eligible(cards[0]['file'] + '&page=2'))

    def test_streaming_page_continuation_keeps_the_exact_region_and_provider(self):
        from browse_controls import page_cards
        from live_core import PageHistory

        folder = {'filetype': 'directory', 'label': 'Service',
                  'file': TMDB + 'info=discover&tmdb_type=movie&with_watch_providers=8&watch_region=GB'}
        path = streaming_folders([folder], 'movie')[0]['file']
        native_next = {'filetype': 'directory', 'label': 'Next page',
                       'file': path + '&page=2&plugin_category=Service'}
        cards, position = page_cards([movie(1), native_next], PageHistory(), path)
        self.assertEqual(cards[1]['_page_control'], 'next')
        self.assertEqual(cards[1]['file'], native_next['file'])
        self.assertEqual(position, 0)

    def test_current_shelf_filter_view_paints_without_hydration_or_provider_requests(self):
        from tempfile import TemporaryDirectory
        from test_snapshot_controller import SnapshotController

        with TemporaryDirectory() as folder:
            def unexpected(*args):
                self.fail('Current-shelf views must paint only the items already in memory')

            state, calls, controls, queue = SnapshotController().state(folder, unexpected)
            state.hydrate_library_items = unexpected
            cards = [movie(1, 4600), movie(2, 7000)]
            state.set_rows([{'label': 'Under 90 minutes', 'path': '', 'local_items': under_runtime(cards, 90),
                             '_current_shelf_view': True}])
            self.assertEqual([item['label'] for item in state.rows[0]], ['Movie 1'])
            for work in queue:
                work()
            self.assertEqual(calls, [])

    def test_streaming_catalog_queries_the_existing_helper_directory_only(self):
        from live_core import directory_items, valid_source
        from test_window_lifecycle import ROOT, extract
        import sys

        paths = []
        native = {'label': 'Service', 'filetype': 'directory',
                  'file': TMDB + 'info=discover&tmdb_type=tv&with_watch_providers=8&watch_region=GB'}

        def rpc(method, params):
            self.assertEqual(method, 'Files.GetDirectory')
            paths.append(params['directory'])
            return {'result': {'files': [native]}}

        namespace = dict(valid_source=valid_source, urlsplit=urlsplit, parse_qs=parse_qs, rpc=rpc,
                         tmdb=lambda info, kind: TMDB + f'info={info}&tmdb_type={kind}',
                         catalogue_category=lambda path: None, directory_items=directory_items,
                         PROPERTIES=[], event=lambda *a, **k: None)
        load = extract(ROOT/'live_review.py', 'get_list', namespace)
        with patch.dict(sys.modules, {'update_activity': SimpleNamespace(wait_for_idle=lambda: True)}):
            cards = load(TMDB + 'info=blacklanturn_streaming_services&tmdb_type=tv')
        self.assertEqual(paths, [TMDB + 'info=watch_providers&tmdb_type=tv'])
        self.assertEqual(cards[0]['title'], 'Service · GB')

    def test_actions_are_scoped_to_the_focused_title_shelf(self):
        state = SimpleNamespace(section='Movies', mode='home', row_offset=0, page_definitions=[{}],
                                rows=[[movie(1, 4600)], []], paths=[PUBLIC, ''],
                                shelf_visit_badges={('Movies', '', PUBLIC): {'movie:1'}})
        self.assertEqual([key for key, _ in ShelfTools.shelf_choices(state, 900)], [90, 120, 'new', 'pick'])
        self.assertEqual(ShelfTools.shelf_choices(state, 901), [])
        self.assertEqual(ShelfTools.shelf_choices(state, 600), [])
        state.episode_browser_context = {'item': movie(1)}
        self.assertEqual(ShelfTools.shelf_choices(state, 900), [])


if __name__ == '__main__':
    unittest.main()
