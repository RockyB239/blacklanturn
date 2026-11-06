import ast
import sys
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ADDON = Path(__file__).parents[1] / 'addon'
sys.path.insert(0, str(ADDON))

import provider_work


HELPER = 'plugin://plugin.video.themoviedb.helper/'
MOVIES = HELPER + '?info=popular&tmdb_type=movie&nextpage=true&widget=true'
CATALOG = HELPER + '?info=blacklanturn_streaming_services&tmdb_type=movie&nextpage=true&widget=true'
NETFLIX = HELPER + '?info=discover&tmdb_type=movie&with_watch_providers=8&watch_region=US&with_id=true&nextpage=true&widget=false'


def live_method(name, **overrides):
    source = ADDON / 'live_review.py'
    module = ast.parse(source.read_text())
    cls = next(node for node in module.body if isinstance(node, ast.ClassDef) and node.name == 'LiveReview')
    method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == name)
    namespace = {
        'submit_latest': provider_work.submit_latest,
        'threading': threading,
        'time': time,
        'event': lambda *args, **kwargs: None,
        **overrides,
    }
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(source), 'exec'), namespace)
    return namespace[name]


class StreamingForeground(unittest.TestCase):
    def test_cold_catalog_opens_the_picker_while_obsolete_movies_fetch_is_still_running(self):
        movies_started = threading.Event()
        release_movies = threading.Event()
        picker = []
        transitions = []
        card = {'file': NETFLIX, 'label': 'Netflix'}
        shown = threading.Event()
        finished = threading.Event()
        def open_grid(root, profile, cards, *, request_catalog, initial_card, region_store, media_kind, region, observe, read_labels):
            self.assertIsNone(cards)
            transitions.append('grid')
            shown.set()
            self.assertEqual((media_kind,region), ('movie','US'))
            request_catalog(region,lambda rows,state: (picker.extend(rows), finished.set()),lambda: True)
            self.assertTrue(finished.wait(2))
        def fetch(definition, **kwargs):
            if definition['path'] == MOVIES:
                movies_started.set()
                release_movies.wait(5)
                return []
            self.assertTrue(shown.is_set())
            self.assertEqual(definition['path'], CATALOG)
            return [card]

        owner = SimpleNamespace(
            alive=True, generation=1, result_cache=SimpleNamespace(revision=0), paths=[MOVIES, ''],
            path_tokens={}, preview_dispatch_lock=threading.RLock(), list_lock=threading.Lock(),
            startup_idle=True, rows=[[], []], cached_row_items=fetch, section='Movies', actions_open=False,
            stop_preview=lambda: None, configure_row_snapshots=lambda: False,
            retained_row_items=lambda definition: (None, False),
            regional_services=lambda:SimpleNamespace(
                default_region=lambda:'US',selected=lambda default:default,
                load=lambda kind,region:(fetch({'path':CATALOG}),'fresh')),
        )
        grid = SimpleNamespace(choose_streaming_service=open_grid)
        load = live_method('request_row_loads')
        browse = live_method('browse_streaming_services', ROOT=None, PROFILE=None, gui_labels=lambda keys:{})
        load(owner, [(0, {'path': MOVIES, 'label': 'Popular Movies'})])
        background = provider_work._rows.thread
        try:
            self.assertTrue(movies_started.wait(1))
            owner.generation += 1
            with patch.dict(sys.modules, {'streaming_services_ui': grid}):
                browse(owner, lambda route, kind: CATALOG)
            self.assertEqual(picker, [card])
            self.assertTrue(background.is_alive())
        finally:
            release_movies.set()
            background.join(2)
        self.assertEqual(transitions, ['grid'])
        self.assertFalse(owner.actions_open)

    def test_foreground_executes_only_the_latest_pending_selection(self):
        lane = provider_work.LatestWorker(paused=lambda: False)
        started = threading.Event()
        release = threading.Event()
        finished = threading.Event()
        calls = []

        def active():
            calls.append('active')
            started.set()
            release.wait(5)

        def latest():
            calls.append('latest')
            finished.set()

        with patch.object(provider_work, '_streaming_rows', lane):
            provider_work.submit_latest(None, active, foreground=True)
            worker = lane.thread
            try:
                self.assertTrue(started.wait(2))
                provider_work.submit_latest(None, lambda: calls.append('replaced'), foreground=True)
                provider_work.submit_latest(None, latest, foreground=True)
                self.assertEqual(calls, ['active'])
                self.assertEqual(lane.pending_count(), 1)
            finally:
                release.set()
                worker.join(2)
            self.assertTrue(finished.is_set())
            self.assertEqual(calls, ['active', 'latest'])

    def test_selected_streaming_row_publishes_while_obsolete_movies_fetch_is_still_running(self):
        for selected in (CATALOG, NETFLIX):
            with self.subTest(selected=selected):
                movies_started = threading.Event()
                release_movies = threading.Event()
                movies_finished = threading.Event()
                streaming_rendered = threading.Event()
                published = []

                def fetch(definition, **kwargs):
                    path = definition['path']
                    if path == MOVIES:
                        movies_started.set()
                        release_movies.wait(5)
                        movies_finished.set()
                    return [{'file': path}]

                def apply_row(slot, files, label, position, **kwargs):
                    published.append(files[0]['file'])
                    if files[0]['file'] == selected:
                        streaming_rendered.set()

                owner = SimpleNamespace(
                    alive=True, generation=1, result_cache=SimpleNamespace(revision=0), paths=[MOVIES, ''],
                    path_tokens={}, preview_dispatch_lock=threading.RLock(), list_lock=threading.Lock(),
                    startup_idle=True, rows=[[], []], cached_row_items=fetch, apply_row=apply_row,
                )
                load = live_method('request_row_loads')
                load(owner, [(0, {'path': MOVIES, 'label': 'Popular Movies'})])
                background = provider_work._rows.thread
                try:
                    self.assertTrue(movies_started.wait(2), 'Movies provider did not start')
                    owner.generation += 1
                    owner.paths[0] = selected
                    load(owner, [(0, {'path': selected, 'label': 'Streaming services', '_explicit_streaming': True})])
                    self.assertTrue(streaming_rendered.wait(1), 'The streaming selection is queued behind Movies')
                    self.assertFalse(movies_finished.is_set(), 'Movies finished before the selected row rendered')
                finally:
                    release_movies.set()
                    background.join(2)
                self.assertTrue(movies_finished.is_set())
                self.assertFalse(background.is_alive())
                self.assertEqual(published, [selected])
