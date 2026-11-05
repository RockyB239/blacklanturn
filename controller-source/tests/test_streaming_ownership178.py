"""Streaming freshness, speculative work ownership, and native dialog input."""
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / 'addon'))
import provider_work
import test_snapshot_controller as snapshots
import test_streaming_services_grid as grids
from row_feedback import RowResultCache
from streaming_shelves import service_shelves
from test_streaming_cache import ROW, MOVIE
from test_streaming_foreground import live_method


class StreamingOwnership178(unittest.TestCase):
    def test_expired_row_revisit_revalidates_without_replacing_visible_cards(self):
        now = [1000.]
        def provider(path):
            title = 'Old title' if now[0] < 1120 else 'Fresh title'
            return [{'file': MOVIE, 'title': title, 'filetype': 'file'}]
        with tempfile.TemporaryDirectory() as folder:
            state, calls, controls, queue = snapshots.SnapshotController().state(folder, provider)
            controls[611] = type(controls[101])()
            state.result_cache = RowResultCache(clock=lambda: now[0])
            definitions = service_shelves('Service', ROW)['rows']
            state.set_rows(definitions)
            queue.pop(0)()
            state.show_row_window(2, 0)
            queue.pop(0)()
            now[0] += 121
            self.assertIsNone(state.result_cache.get(ROW))
            state.show_row_window(0, 0)
            current_cards = controls[900].items
            self.assertEqual(state.rows[0][0]['title'], 'Old title')
            self.assertEqual(len(queue), 1, 'Expired provider row needs owned revalidation')
            queue.pop(0)()
            self.assertIs(controls[900].items, current_cards, 'Background refresh must keep native cards stable')
            self.assertEqual(state.rows[0][0]['title'], 'Old title')
            self.assertEqual(state.result_cache.get(ROW)[0]['title'], 'Fresh title')
            state.show_row_window(2, 0)
            state.show_row_window(0, 0)
            self.assertEqual(state.rows[0][0]['title'], 'Fresh title')
            self.assertEqual(calls.count(ROW), 2)

    def test_fresh_row_revisit_does_not_start_duplicate_provider_work(self):
        now = [1000.]
        with tempfile.TemporaryDirectory() as folder:
            state, calls, controls, queue = snapshots.SnapshotController().state(
                folder, lambda path: [{'file': MOVIE, 'title': 'Title', 'filetype': 'file'}])
            controls[611] = type(controls[101])()
            state.result_cache = RowResultCache(clock=lambda: now[0])
            state.set_rows(service_shelves('Service', ROW)['rows'])
            queue.pop(0)()
            state.show_row_window(2, 0)
            queue.pop(0)()
            now[0] += 119
            state.show_row_window(0, 0)
            self.assertEqual(queue, [])
            self.assertEqual(calls.count(ROW), 1)

    def owner(self, paths, fetch, applied):
        def apply(slot, files, *args, **kwargs):
            applied.append(files[0]['file'])
        return SimpleNamespace(
            alive=True, generation=1, result_cache=SimpleNamespace(revision=0), paths=paths,
            path_tokens={}, preview_dispatch_lock=threading.RLock(), list_lock=threading.Lock(),
            startup_idle=True, rows=[[], []], cached_row_items=fetch, apply_row=apply)

    def join_workers(self, workers):
        for lane in workers:
            thread = lane.thread
            if thread is not None:
                thread.join(2)
                self.assertFalse(thread.is_alive())

    def test_selected_row_passes_running_speculation_and_late_result_cannot_paint(self):
        started, release, selected = threading.Event(), threading.Event(), threading.Event()
        background = provider_work.LatestWorker(paused=lambda: False)
        foreground = provider_work.LatestWorker(paused=lambda: False)
        old, new = ROW + '&with_genres=35', ROW + '&with_genres=18'
        applied = []
        def fetch(definition, **kwargs):
            if definition['path'] == old:
                started.set()
                release.wait(3)
            else:
                selected.set()
            return [{'file': definition['path']}]
        owner = self.owner(['', old], fetch, applied)
        load = live_method('request_row_loads')
        with patch.object(provider_work, '_rows', background), patch.object(provider_work, '_streaming_rows', foreground):
            load(owner, [(1, {'path': old, 'label': 'Speculative', '_explicit_streaming': True})], prefetch=True)
            self.assertTrue(started.wait(1))
            try:
                owner.generation += 1
                owner.paths = [new, '']
                load(owner, [(0, {'path': new, 'label': 'Selected', '_explicit_streaming': True})], 0)
                self.assertTrue(selected.wait(1), 'User selection waited behind obsolete lookahead')
                self.assertFalse(release.is_set())
            finally:
                release.set()
                self.join_workers((background, foreground))
        self.assertEqual(applied, [new], 'Late old generation must never paint or restore its focus')

    def test_queued_speculation_is_retired_without_fetching_after_selection(self):
        blocker_started, release, selected = threading.Event(), threading.Event(), threading.Event()
        background = provider_work.LatestWorker(paused=lambda: False)
        foreground = provider_work.LatestWorker(paused=lambda: False)
        old, new = ROW + '&with_genres=35', ROW + '&with_genres=18'
        fetched, applied = [], []
        def blocker():
            blocker_started.set()
            release.wait(3)
        def fetch(definition, **kwargs):
            fetched.append(definition['path'])
            selected.set()
            return [{'file': definition['path']}]
        owner = self.owner(['', old], fetch, applied)
        load = live_method('request_row_loads')
        background.submit('blocker', blocker)
        self.assertTrue(blocker_started.wait(1))
        try:
            with patch.object(provider_work, '_rows', background), patch.object(provider_work, '_streaming_rows', foreground):
                load(owner, [(1, {'path': old, 'label': 'Speculative', '_explicit_streaming': True})], prefetch=True)
                self.assertEqual(background.pending_count(), 1)
                owner.generation += 1
                owner.paths = [new, '']
                load(owner, [(0, {'path': new, 'label': 'Selected', '_explicit_streaming': True})], 0)
                self.assertTrue(selected.wait(1))
        finally:
            release.set()
            self.join_workers((background, foreground))
        self.assertEqual(fetched, [new])
        self.assertEqual(applied, [new])

    def grid(self):
        fixture = grids.GridTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.dialog.catalog = grids.ServiceCatalog([])
        fixture.dialog.onInit()
        return fixture.dialog, fixture.ui

    def test_catalog_completion_preserves_close_focus_after_user_navigation(self):
        grid, ui = self.grid()
        grid.onAction(SimpleNamespace(getId=lambda: 2))
        grid.setFocusId(ui.CANCEL)
        grid.catalog_loaded([grids.card(8, 'Netflix')])
        self.assertEqual(grid.getFocusId(), ui.CANCEL)
        grid.onClick(ui.CANCEL)
        self.assertTrue(grid.closed)
        self.assertIsNone(grid.result)

    def test_catalog_completion_preserves_user_tab_over_old_initial_selection(self):
        for tab_name in ('ALL', 'PINNED'):
            with self.subTest(tab=tab_name):
                grid, ui = self.grid()
                grid.initial_card = grids.card(4000, 'Old service')
                tab = getattr(ui, tab_name)
                grid.onClick(tab)
                grid.catalog_loaded([grids.card(4000 - n, f'Service {n:03}') for n in range(30)])
                self.assertEqual(grid.tab, tab)
                self.assertEqual(grid.getFocusId(), tab)

    def test_idle_catalog_completion_still_focuses_first_available_service(self):
        grid, ui = self.grid()
        grid.catalog_loaded([grids.card(8, 'Netflix')])
        self.assertEqual(grid.getFocusId(), ui.GRID)
        self.assertEqual(grid.panel.items[0].label, 'Netflix')


if __name__ == '__main__':
    unittest.main(verbosity=2)
