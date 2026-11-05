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

    def test_force_reload_discard_removes_existing_snapshot(self):
        self.assertTrue(self.store().put(ROW, [{'file': MOVIE, 'label': 'Title', 'filetype': 'file'}]))
        self.store().discard(ROW)
        self.assertIsNone(self.store().get(ROW))

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
