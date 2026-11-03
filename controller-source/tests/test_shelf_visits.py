from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from shelf_visits import ShelfVisits, title_key

BASE = 'plugin://plugin.video.themoviedb.helper/?'

def item(identity, suffix=''):
    return {'file': BASE + 'info=play&tmdb_type=movie&tmdb_id=' + str(identity) + suffix}


class ShelfVisitTests(unittest.TestCase):
    def test_baseline_reorder_new_title_and_failed_row(self):
        with TemporaryDirectory() as folder:
            store = ShelfVisits(Path(folder)/'visits.json', submit=lambda save: save())
            self.assertEqual(store.visit('movies/action', [item(1), item(2)]), set())
            self.assertEqual(store.visit('movies/action', []), set())
            self.assertEqual(store.visit('movies/action', [item(2), item(1, '&widget=true'), item(3)]), {'movie:3'})
            reopened = ShelfVisits(store.path, submit=lambda save: save())
            self.assertEqual(reopened.visit('movies/action', [item(3), item(2)]), set())
            self.assertEqual(reopened.visit('movies/comedy', [item(4)]), set())

    def test_controls_and_episode_actions_do_not_enter_the_baseline(self):
        self.assertIsNone(title_key({'file': BASE + 'info=discover&tmdb_type=movie&page=2'}))
        self.assertIsNone(title_key({'file': BASE + 'info=play&tmdb_type=tv&tmdb_id=1&season=1&episode=2'}))
        self.assertIsNone(title_key({'file': 'plugin://other/?info=play&tmdb_type=movie&tmdb_id=1'}))

    def test_controller_keeps_badge_on_repaint_and_passes_it_only_to_native_card(self):
        import json
        from urllib.parse import parse_qs, urlsplit
        from public_rows import public_path
        from test_window_lifecycle import extract
        from test_snapshot_controller import SnapshotController
        from test_public_row_snapshots import P, ITEM

        with TemporaryDirectory() as folder:
            state, _, controls, _ = SnapshotController().state(folder, lambda _: [])
            store = ShelfVisits(Path(folder)/'visits.json', submit=lambda save: save())
            store.visit(json.dumps(('Movies', 'action', P)), [ITEM])
            annotate = extract(Path(__file__).parents[1]/'addon/live_review.py', 'annotate_shelf_cards',
                               dict(public_path=public_path, parse_qs=parse_qs, urlsplit=urlsplit, json=json), 'LiveReview')
            state.section = 'Movies'
            state.row_navigation = lambda: None
            state.active_page = 'action'
            state.shelf_visit_badges = {}
            state.shelf_visit_store = store
            state.annotate_shelf_cards = lambda n, items: annotate(state, n, items)
            state.paths[0] = P
            added = dict(ITEM, file=ITEM['file'].replace('42', '43'))
            for _ in range(2):
                state.apply_row(0, [ITEM, added], 'Public', display_position=True)
                self.assertEqual(controls[900].items[0].properties.get('newSinceVisit'), None)
                self.assertEqual(controls[900].items[1].properties.get('newSinceVisit'), 'true')
                self.assertNotIn('_new_since_visit', state.rows[0][1])
