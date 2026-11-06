import tempfile
import unittest
from pathlib import Path

from streaming_cache import StreamingRows

BASE = 'plugin://plugin.video.themoviedb.helper/?'
CATALOG = BASE + 'info=blacklanturn_streaming_services&tmdb_type=movie&nextpage=true&widget=true'
ROW = BASE + 'info=discover&tmdb_type=movie&with_watch_providers=350&watch_region=US&with_id=true&nextpage=true&widget=false'
NEXT = ROW.replace('&widget=false', '') + '&page=2&cacheonly=False&plugin_category=Apple+TV'
MOVIE = BASE + 'info=play&tmdb_type=movie&tmdb_id=12'


class StreamingRowsTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.now = 1_700_000_000
        self.cache_path = Path(self.directory.name)

    def store(self, path=ROW, scope='us-settings'):
        return StreamingRows.for_route(self.cache_path, scope, path, clock=lambda: self.now)

    def test_fresh_catalog_persists_all_native_cards_and_marks_them_as_folders(self):
        folders = [{'file': ROW.replace('=350', f'={i}'), 'label': f'Service {i} · US',
                    'filetype': 'directory', '_streaming_provider': True} for i in range(1, 299)]
        self.assertTrue(self.store(CATALOG).put(CATALOG, folders))
        found = self.store(CATALOG).get(CATALOG)
        self.assertEqual([i['file'] for i in found], [i['file'] for i in folders])
        self.assertTrue(all(i['_streaming_provider'] for i in found))
        self.now += 300
        self.assertIsNone(self.store(CATALOG).get(CATALOG))

    def test_exact_provider_region_and_scope_expire_without_serving_old_rows(self):
        card = {'file': MOVIE, 'label': 'Title', 'filetype': 'file', 'playcount': 1}
        next_page = {'file': NEXT, 'label': 'Next', 'filetype': 'directory'}
        self.assertTrue(self.store().put(ROW, [card, next_page]))
        fresh = self.store().get(ROW)
        self.assertNotIn('playcount', fresh[0])
        self.assertEqual(fresh[1]['file'], NEXT)
        self.assertIsNone(self.store().get(ROW.replace('US', 'GB')))
        self.assertIsNone(self.store(scope='other-settings').get(ROW))
        self.now += 120
        self.assertIsNone(self.store().get(ROW))

    def test_fail_closed_for_non_streaming_routes_and_bad_payloads(self):
        for path in (NEXT, MOVIE, ROW + '&token=secret', ROW.replace('350', '350%2C8')):
            self.assertIsNone(self.store(path))
        self.assertFalse(self.store().put(ROW, [{'file': NEXT.replace('US','GB'), 'filetype':'directory'}]))
        self.assertIsNone(self.store().get(ROW))
        self.assertFalse(self.store(CATALOG).put(CATALOG, [{'file':MOVIE,'filetype':'file'}]))

    def test_filtered_cache_and_branded_paging_preserve_genre(self):
        from browse_controls import page_cards
        from live_core import PageHistory

        comedy = ROW + '&with_genres=35'
        next_page = {'file': NEXT + '&with_genres=35', 'filetype': 'directory'}
        card = {'file': MOVIE, 'label': 'Title', 'filetype': 'file'}
        store = self.store(comedy)
        self.assertTrue(store.put(comedy, [card, next_page]))
        self.assertIsNone(store.get(ROW))
        self.assertIsNone(store.get(comedy.replace('35', '18')))
        mismatched = dict(next_page, file=NEXT + '&with_genres=18')
        self.assertFalse(store.put(comedy, [card, mismatched]))
        cards, _ = page_cards(store.get(comedy), PageHistory(), comedy)
        self.assertEqual(cards[-1]['_page_control'], 'next')
        self.assertIn('&with_genres=35&widget=false', cards[-1]['file'])

    def test_force_reload_discard_removes_existing_snapshot(self):
        self.assertTrue(self.store().put(ROW, [{'file': MOVIE, 'label': 'Title', 'filetype': 'file'}]))
        self.store().discard(ROW)
        self.assertIsNone(self.store().get(ROW))

    def test_streaming_directory_requires_an_explicit_files_array(self):
        import sys
        from types import SimpleNamespace
        from unittest.mock import patch
        from urllib.parse import parse_qs, urlsplit

        from live_core import directory_items, valid_source
        from test_window_lifecycle import ROOT, extract

        for response in ({}, {'result': {}}, {'result': {'files': None}},
                         {'error': {'code': -32602, 'message': 'Invalid params.'}},
                         {'result': {'files': []}}):
            with self.subTest(response=response):
                load = extract(ROOT/'live_review.py', 'get_list', dict(
                    valid_source=valid_source, urlsplit=urlsplit, parse_qs=parse_qs,
                    rpc=lambda *args: response, catalogue_category=lambda path: None,
                    directory_items=directory_items, PROPERTIES=[], event=lambda *a, **k: None))
                with patch.dict(sys.modules, {'update_activity': SimpleNamespace(wait_for_idle=lambda: True)}):
                    if response == {'result': {'files': []}}:
                        self.assertEqual(load(ROW), [])
                    else:
                        with self.assertRaises(ValueError):
                            load(ROW)

    def test_provider_opens_popular_then_loads_only_the_requested_row(self):
        from streaming_shelves import service_shelves
        from test_snapshot_controller import SnapshotController

        definitions = service_shelves('Service', ROW)['rows']
        with tempfile.TemporaryDirectory() as folder:
            card = {'file': MOVIE, 'title': 'Current title', 'filetype': 'file'}
            state, calls, controls, queue = SnapshotController().state(folder, lambda path: [card])
            controls[611] = type(controls[101])()

            state.set_rows(definitions)
            self.assertEqual(calls, [])
            queue.pop(0)()
            self.assertEqual(calls, [ROW])
            self.assertEqual(state.getProperty('row0'), 'Popular')
            self.assertEqual(state.rows[1], [])
            state.show_row_window(3, 0)
            queue.pop(0)()
            self.assertEqual(calls, [ROW, definitions[3]['path']])
            self.assertEqual(state.getProperty('row0'), 'Comedy')
            self.assertEqual(state.rows[1], [])

    def test_down_preserves_current_posters_until_next_shelf_is_ready(self):
        from streaming_shelves import service_shelves
        from test_snapshot_controller import SnapshotController

        definitions = service_shelves('Service', ROW)['rows']
        with tempfile.TemporaryDirectory() as folder:
            card = {'file': MOVIE, 'title': 'Current title', 'filetype': 'file'}
            state, calls, controls, queue = SnapshotController().state(folder, lambda path: [card])
            controls[611] = type(controls[101])()
            state.set_rows(definitions)
            queue.pop(0)()
            first = state.rows[0]
            self.assertEqual(calls, [ROW])
            self.assertTrue(state.shift_rows(1, 0))
            self.assertIs(state.rows[0], first)
            self.assertEqual((state.row_offset, state.focus), (0, 900))
            self.assertEqual(state.getProperty('rowState1'), 'loading')
            self.assertEqual(len(queue), 1)
            queue.pop(0)()
            self.assertEqual(calls, [ROW, definitions[1]['path']])
            self.assertIs(state.rows[0], first)
            self.assertEqual(state.getProperty('row1'), 'Recent Releases')
            state.actions_open=False
            state.settle_streaming_shelf()
            self.assertEqual((state.row_offset, state.focus), (1, 900))
            self.assertEqual(state.getProperty('row0'), 'Recent Releases')
            self.assertTrue(state.load_next_streaming_shelf(prefetch=True))
            queue.pop(0)()
            self.assertEqual(calls, [ROW, definitions[1]['path'], definitions[2]['path']])
            self.assertEqual((state.getProperty('row0'), state.getProperty('row1')), ('Recent Releases', 'Action'))
            self.assertTrue(state.shift_rows(1, 0))
            self.assertEqual((state.row_offset, state.focus), (2, 900))
            self.assertEqual(state.getProperty('row0'), 'Action')
            self.assertTrue(state.shift_rows(-1, 0))
            self.assertTrue(state.shift_rows(-1, 0))
            self.assertEqual((state.row_offset, state.focus), (0, 900))
            self.assertEqual(state.getProperty('row0'), 'Popular')

    def test_down_can_retire_an_unfinished_shelf(self):
        from streaming_shelves import service_shelves
        from test_snapshot_controller import SnapshotController

        definitions = service_shelves('Service', ROW)['rows']
        with tempfile.TemporaryDirectory() as folder:
            card = {'file': MOVIE, 'title': 'Available title', 'filetype': 'file'}
            state, calls, controls, queue = SnapshotController().state(folder, lambda path: [card])
            controls[611] = type(controls[101])()
            state.set_rows(definitions)
            self.assertTrue(state.shift_rows(1, 0))
            self.assertEqual(state.row_offset, 1)
            self.assertEqual(state.getProperty('row0'), 'Recent Releases · Loading…')
            while queue:
                queue.pop(0)()
            self.assertEqual(calls, [definitions[1]['path']])
            self.assertEqual(state.focus, 900)

    def test_down_skips_confirmed_empty_shelf_and_preserves_selected_poster_until_next_loads(self):
        from streaming_shelves import service_shelves
        from test_snapshot_controller import SnapshotController

        definitions = service_shelves('MUBI', ROW)['rows']
        card = {'file': MOVIE, 'title': 'Current title', 'filetype': 'file'}
        with tempfile.TemporaryDirectory() as folder:
            state, calls, controls, queue = SnapshotController().state(
                folder, lambda path: [] if path == definitions[1]['path'] else [card])
            controls[611] = type(controls[101])()
            state.actions_open = False
            state.set_rows(definitions)
            queue.pop(0)()
            first = controls[900].items[0]

            self.assertTrue(state.shift_rows(1, 0))
            queue.pop(0)()
            state.settle_streaming_shelf()
            self.assertIs(controls[900].items[0], first)
            self.assertEqual((state.row_offset, state.focus), (0, 900))
            self.assertNotIn('No titles', state.getProperty('row1'))
            self.assertNotIn('Unavailable', state.getProperty('row1'))
            self.assertEqual(len(queue), 1)
            queue.pop(0)()
            state.settle_streaming_shelf()

            self.assertEqual(calls, [ROW, definitions[1]['path'], definitions[2]['path']])
            self.assertEqual((state.row_offset, state.focus), (2, 900))
            self.assertEqual(state.getProperty('row0'), 'Action')
            self.assertTrue(state.shift_rows(-1, 0))
            self.assertEqual((state.row_offset, state.focus), (0, 900))
            self.assertEqual(state.getProperty('row1'), 'Action')

    def test_confirmed_empty_first_shelf_advances_to_available_shelf(self):
        from streaming_shelves import service_shelves
        from test_snapshot_controller import SnapshotController

        definitions = service_shelves('MUBI', ROW)['rows']
        card = {'file': MOVIE, 'title': 'Current title', 'filetype': 'file'}
        with tempfile.TemporaryDirectory() as folder:
            state, calls, controls, queue = SnapshotController().state(
                folder, lambda path: [] if path == ROW else [card])
            controls[611] = type(controls[101])()
            state.actions_open = False
            state.set_rows(definitions)
            queue.pop(0)()
            state.settle_streaming_shelf()
            queue.pop(0)()

            self.assertEqual(calls, [ROW, definitions[1]['path']])
            self.assertEqual((state.row_offset, state.focus), (1, 900))

    def test_failed_shelf_keeps_current_titles_and_offers_streaming_retry(self):
        from streaming_shelves import service_shelves
        from test_snapshot_controller import SnapshotController

        definitions = service_shelves('MUBI', ROW)['rows']
        card = {'file': MOVIE, 'title': 'Current title', 'filetype': 'file'}
        outage = True

        def provider(path):
            if outage and path == definitions[1]['path']:
                raise ValueError('Invalid params.')
            return [card]

        with tempfile.TemporaryDirectory() as folder:
            state, calls, controls, queue = SnapshotController().state(folder, provider)
            controls[611] = type(controls[101])()
            state.actions_open = False
            state.set_rows(definitions)
            queue.pop(0)()
            first = controls[900].items[0]
            self.assertTrue(state.shift_rows(1, 0))
            queue.pop(0)()
            state.settle_streaming_shelf()

            self.assertIs(controls[900].items[0], first)
            self.assertEqual((state.row_offset, state.focus), (0, 900))
            self.assertEqual(state.row_states[1], 'error')
            self.assertEqual(state.failed_paths[1]['path'], definitions[1]['path'])
            self.assertIn('Recent Releases', state.getProperty('rowMessage1'))
            self.assertIn('Retry unavailable shelves', state.getProperty('rowMessage1'))
            self.assertNotIn('integration', state.getProperty('rowMessage1'))
            self.assertEqual(queue, [])

            outage = False
            state.retry_lists()
            queue.pop(0)()
            self.assertEqual(state.row_states[1], 'ready')
            self.assertEqual(state.failed_paths, {})
            self.assertIs(controls[900].items[0], first)
            self.assertEqual(calls, [ROW, definitions[1]['path'], definitions[1]['path']])

    def test_fresh_streaming_row_paints_before_any_provider_worker_runs(self):
        from test_snapshot_controller import SnapshotController
        with tempfile.TemporaryDirectory() as folder:
            state, calls, controls, queue = SnapshotController().state(folder, lambda path: [])
            seen = []
            cards = [{'file': MOVIE, 'title': 'Cached title', 'filetype': 'file'}]
            state.retained_streaming_items = lambda path: seen.append(path) or cards if path == ROW else None
            state.set_rows([{'label': 'Service', 'path': ROW}])
            self.assertEqual([item['title'] for item in state.rows[0]], ['Cached title'])
            self.assertEqual(seen, [ROW])
            for worker in queue:
                worker()
            self.assertEqual(calls, [])
