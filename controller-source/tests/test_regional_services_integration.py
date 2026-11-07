"""Regression coverage for the country picker and service shelf wiring."""
from pathlib import Path
import sys
from urllib.parse import urlencode
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'addon'))
from streaming_cache import streaming_page_target, streaming_route
from browse_controls import page_cards
from live_core import PageHistory
from streaming_shelves import service_shelves

BASE = ('plugin://plugin.video.themoviedb.helper/?info=discover&tmdb_type=movie'
        '&with_watch_providers=11&watch_region=GB&with_id=true&nextpage=true&widget=false')


def title(ident):
    return {'file': 'plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=movie&tmdb_id=' + str(ident),
            'filetype': 'file', 'type': 'movie'}


class RegionalServicesIntegration(unittest.TestCase):
    def test_specialty_paging_requires_the_same_country_and_filters(self):
        path = BASE + '&' + urlencode({'with_origin_country': 'FR|IT|JP|KR|DE|ES|IN|BR|MX|SE|HK|DK|IR|TW'})
        self.assertEqual(streaming_route(path), 'titles')
        following = path.replace('&widget=false', '') + '&page=2'
        self.assertEqual(streaming_page_target(path, following), following + '&widget=false')
        wrong = following.replace('watch_region=GB', 'watch_region=US')
        self.assertEqual(streaming_page_target(path, wrong), wrong)
        self.assertIsNone(streaming_route(path + '&with_keywords=42'))
        result, _ = page_cards([title(4), {'file': wrong, 'filetype': 'directory'},
                                {'file': following, 'filetype': 'directory'}], PageHistory(), path)
        self.assertEqual([item['file'] for item in result], [title(4)['file'], following + '&widget=false'])

    def test_regional_layout_uses_browse_all_and_rejects_duplicate_shelves(self):
        discovery = service_shelves('MUBI · GB', BASE, adaptive=True, region_name='United Kingdom')
        rows = discovery['rows']
        self.assertEqual(rows[0]['label'], 'Browse All Movies')
        self.assertIn('United Kingdom', discovery['heading'])
        layout = rows[0]['_streaming_layout']
        popular = [title(n) for n in range(1, 13)]
        self.assertFalse(layout.available(rows[1]['path']))
        self.assertEqual(layout.filter(BASE, popular), popular)
        first, second, third = [row['path'] for row in rows[1:4]]
        self.assertTrue(layout.available(first))
        self.assertEqual(layout.filter(first, popular), [])
        self.assertFalse(layout.available(first))
        other = [title(n) for n in range(21, 30)]
        self.assertEqual(layout.filter(second, other), other)
        self.assertEqual(layout.filter(third, other), [])
        self.assertEqual(layout.filter(second + '&page=2', popular), popular)

    def test_small_complete_catalog_stays_compact(self):
        rows = service_shelves('MUBI', BASE, adaptive=True)['rows']
        layout = rows[0]['_streaming_layout']
        layout.filter(BASE, [title(n) for n in range(1, 8)])
        self.assertFalse(layout.available(rows[1]['path']))

    def test_title_drill_down_keeps_its_season_cards_inside_a_service(self):
        rows = service_shelves('MUBI', BASE.replace('tmdb_type=movie', 'tmdb_type=tv'), adaptive=True)['rows']
        layout = rows[0]['_streaming_layout']
        layout.filter(rows[0]['path'], [title(n) for n in range(1, 12)])
        seasons = [{'file': 'plugin://plugin.video.themoviedb.helper/?info=episodes&tmdb_type=tv&tmdb_id=99&season=1',
                    'filetype': 'directory', 'type': 'season'}]
        show = 'plugin://plugin.video.themoviedb.helper/?info=seasons&tmdb_type=tv&tmdb_id=99'
        self.assertIs(layout.filter(show, seasons), seasons)
        self.assertNotIn(show, layout.rejected)

    def test_large_provider_can_publish_every_distinct_populated_shelf(self):
        path = BASE.replace('with_watch_providers=11', 'with_watch_providers=8')
        rows = service_shelves('Netflix', path, adaptive=True)['rows']
        layout = rows[0]['_streaming_layout']
        layout.filter(path, [title(n) for n in range(1, 21)])
        self.assertGreaterEqual(len(rows), 15)
        for number, row in enumerate(rows[1:8], 1):
            files = [title(number * 100 + n) for n in range(1, 9)]
            self.assertEqual(layout.filter(row['path'], files), files)
        self.assertEqual(len(layout.accepted), 7)

    def test_overlapping_genres_can_each_add_a_different_view_of_the_catalog(self):
        path = BASE.replace('with_watch_providers=11', 'with_watch_providers=8')
        rows = service_shelves('Netflix', path, adaptive=True)['rows']
        layout = rows[0]['_streaming_layout']
        layout.filter(path, [title(n) for n in range(1, 21)])
        first = [title(n) for n in (5, 6, 7, 8, 21, 22, 23, 24)]
        next_ = [title(n) for n in (1, 2, 3, 4, 21, 22, 23, 24)]
        self.assertEqual(layout.filter(rows[1]['path'], first), first)
        self.assertEqual(layout.filter(rows[2]['path'], next_), next_)
        self.assertEqual(layout.filter(rows[3]['path'], next_), [])

    def test_specialty_services_can_follow_specialties_with_available_genres(self):
        rows = service_shelves('MUBI', BASE, adaptive=True)['rows']
        self.assertEqual([row['label'] for row in rows[1:4]],
                         ['World Cinema', 'Classics Before 1990', 'Film Noir'])
        self.assertTrue({'Drama', 'Documentary', 'Recent Releases'} <= {row['label'] for row in rows})
        self.assertEqual(len(rows), len({row['path'] for row in rows}))

    def test_unverified_row_names_never_flash_or_steal_focus_during_rapid_down(self):
        from tempfile import TemporaryDirectory
        from test_snapshot_controller import SnapshotController

        path = BASE.replace('with_watch_providers=11', 'with_watch_providers=8')
        rows = service_shelves('Netflix', path, adaptive=True)['rows']
        baseline = [title(n) for n in range(1, 21)]
        filled = [title(n) for n in range(101, 109)]
        lookups = {path: baseline, rows[1]['path']: [], rows[2]['path']: filled}
        with TemporaryDirectory() as folder:
            state, calls, controls, queue = SnapshotController().state(folder, lambda source: lookups.get(source, []))
            controls[611] = type(controls[101])()
            state.actions_open = False
            state.streaming_layout = lambda: state.page_definitions[0].get('_streaming_layout')
            mutations = []
            set_property = state.setProperty
            state.setProperty = lambda key, value: (mutations.append((key, value)), set_property(key, value))
            state.set_rows(rows)
            queue.pop(0)()
            self.assertTrue(state.shift_rows(1, 0))
            self.assertTrue(state.shift_rows(1, 0))
            self.assertEqual((state.row_offset, state.focus, state.getProperty('row1')), (0, 900, ''))
            self.assertEqual(len(queue), 1)
            queue.pop(0)()
            state.settle_streaming_shelf()
            self.assertEqual(state.row_offset, 0)
            queue.pop(0)()
            state.settle_streaming_shelf()
            self.assertEqual(state.getProperty('row0'), rows[2]['label'])
            self.assertTrue(state.shift_rows(-1, 0))
            self.assertEqual((state.row_offset, state.focus), (0, 900))
            self.assertEqual(calls, [path, rows[1]['path'], rows[2]['path']])
            self.assertFalse(any(key in ('row0', 'row1') and 'Recent Releases' in value
                                 for key, value in mutations))

    def test_movies_shortcut_uses_same_hero_button_textures_and_focus_style(self):
        from xml.etree import ElementTree as ET
        skin = ET.parse(Path(__file__).resolve().parents[1] / 'addon/resources/skins/Default/1080i/LiveReview.xml')
        control = skin.find(".//control[@id='612']")
        play = skin.find(".//control[@id='101']")
        for field in ('font', 'textoffsetx', 'focusedcolor', 'texturefocus', 'texturenofocus'):
            self.assertEqual(control.findtext(field), play.findtext(field))
        for state in ('Rest', 'Focus'):
            images = [image for image in skin.findall('.//control[@type="image"]')
                      if f'Control.IsVisible(612)' in (image.findtext('visible') or '')
                      and f'BlackLanturn.Navigation.{state}' in (image.findtext('texture') or '')]
            self.assertEqual(len(images), 1)
            for size in ('left', 'top', 'width', 'height'):
                self.assertEqual(images[0].findtext(size), control.findtext(size))

    def test_confirmed_next_row_paints_from_session_cache_before_visiting_it(self):
        from tempfile import TemporaryDirectory
        from test_snapshot_controller import SnapshotController

        path = BASE.replace('with_watch_providers=11', 'with_watch_providers=8')
        rows = service_shelves('Netflix', path, adaptive=True)['rows'][:4]
        available = [title(n) for n in range(101, 109)]
        with TemporaryDirectory() as folder:
            state, calls, controls, queue = SnapshotController().state(folder, lambda source: [title(n) for n in range(1, 21)])
            controls[611] = type(controls[101])()
            state.actions_open = False
            state.streaming_layout = lambda: state.page_definitions[0]['_streaming_layout']
            state.set_rows(rows)
            queue.pop(0)()
            next_row = state.page_definitions[1]
            state.streaming_layout().filter(next_row['path'], available)
            state.result_cache.put(next_row['path'], available)

            state.show_row_window(0, 0)
            self.assertEqual(state.getProperty('row1'), next_row['label'])
            self.assertEqual(state.rows[1], available)
            self.assertEqual((state.row_offset, state.focus, calls), (0, 900, [path]))
            self.assertEqual(queue, [])

    def test_shelf_index_qualifies_rows_without_visiting_them_and_skips_empty(self):
        from streaming_shelves import warm_shelves

        path = BASE.replace('with_watch_providers=11', 'with_watch_providers=8')
        rows = service_shelves('Netflix', path, adaptive=True)['rows'][:5]
        layout = rows[0]['_streaming_layout']
        layout.filter(path, [title(n) for n in range(1, 21)])
        first, second, third, fourth = [row['path'] for row in rows[1:]]
        filled = [title(n) for n in range(101, 109)]
        calls = []
        results = {first: [], second: filled, third: filled, fourth: [title(n) for n in range(201, 209)]}
        warm_shelves(rows, layout, lambda p: calls.append(p) or results[p], lambda: True)
        self.assertEqual(calls, [first, second, third, fourth])
        self.assertEqual(list(layout.accepted), [second, fourth])
        self.assertEqual(layout.rejected, {first, third})

    def test_retired_shelf_scan_does_not_qualify_or_fetch_any_more_rows(self):
        from streaming_shelves import warm_shelves

        path = BASE.replace('with_watch_providers=11', 'with_watch_providers=8')
        rows = service_shelves('Netflix', path, adaptive=True)['rows'][:5]
        layout = rows[0]['_streaming_layout']
        layout.filter(path, [title(n) for n in range(1, 21)])
        calls = []

        def load(path):
            calls.append(path)
            return [title(n) for n in range(101, 109)]

        self.assertFalse(warm_shelves(rows, layout, load, lambda: not calls))
        self.assertEqual(calls, [rows[1]['path']])
        self.assertEqual(layout.accepted, {})
        self.assertEqual(layout.rejected, set())

    def test_failed_background_check_remains_retryable(self):
        from streaming_shelves import warm_shelves

        path = BASE.replace('with_watch_providers=11', 'with_watch_providers=8')
        rows = service_shelves('Netflix', path, adaptive=True)['rows'][:3]
        layout = rows[0]['_streaming_layout']
        layout.filter(path, [title(n) for n in range(1, 21)])
        available = [title(n) for n in range(101, 109)]

        def load(path):
            if path == rows[1]['path']:
                raise OSError('provider not available')
            return available

        self.assertTrue(warm_shelves(rows, layout, load, lambda: True))
        self.assertTrue(layout.available(rows[1]['path']))
        self.assertNotIn(rows[1]['path'], layout.accepted)
        self.assertIn(rows[2]['path'], layout.accepted)

    def test_jump_can_open_a_verified_shelf_that_was_never_scrolled_into(self):
        from tempfile import TemporaryDirectory
        from types import MethodType, SimpleNamespace
        from unittest.mock import patch
        from test_snapshot_controller import SnapshotController
        from test_streaming_foreground import live_method
        import provider_work

        path = BASE.replace('with_watch_providers=11', 'with_watch_providers=8')
        rows = service_shelves('Netflix', path, adaptive=True)['rows'][:4]
        data = {row['path']: [title(i * 100 + n) for n in range(1, 13)]
                for i, row in enumerate(rows)}
        data[rows[1]['path']] = []
        with TemporaryDirectory() as folder:
            state, calls, controls, queue = SnapshotController().state(folder, data.__getitem__)
            controls[611] = type(controls[101])()
            state.owned_preview = state.actions_open = False
            state.retained_streaming_items = lambda _, **kwargs: (None, False)
            state.streaming_snapshot = lambda _: None
            state.streaming_layout = lambda: state.page_definitions[0]['_streaming_layout']
            state.warm_streaming_shelves = MethodType(
                live_method('warm_streaming_shelves', get_list=lambda p: calls.append(p) or data[p]), state)
            selected = []
            def dialog(heading, labels, *, preselect):
                self.assertEqual((heading, preselect), ('Jump to row', 0))
                selected.extend(labels)
                return labels.index(rows[3]['label'])
            state.jump_to_streaming_shelf = MethodType(live_method('jump_to_streaming_shelf'), state)
            jump = live_method('jump_streaming_shelf',
                               xbmcgui=SimpleNamespace(Dialog=lambda: SimpleNamespace(select=dialog)))
            state.set_rows(rows)
            queue.pop(0)()
            with patch.object(provider_work, 'submit_streaming_warmup', queue.append):
                state.warm_streaming_shelves()
                self.assertEqual(calls, [path])
                queue.pop(0)()
                self.assertEqual(state.row_offset, 0)
                jump(state)
            self.assertEqual(selected, [rows[0]['label'], rows[2]['label'], rows[3]['label']])
            self.assertEqual(state.getProperty('row0'), rows[3]['label'])
            self.assertEqual(calls, [row['path'] for row in rows])
            self.assertEqual(queue, [])

    def test_down_reuses_in_flight_background_request_for_the_same_row(self):
        from tempfile import TemporaryDirectory
        from threading import Event, Thread
        from types import MethodType
        from unittest.mock import patch
        from test_snapshot_controller import SnapshotController
        from test_streaming_foreground import live_method
        import provider_work

        path = BASE.replace('with_watch_providers=11', 'with_watch_providers=8')
        rows = service_shelves('Netflix', path, adaptive=True)['rows'][:2]
        baseline = [title(n) for n in range(1, 21)]
        candidate = [title(n) for n in range(101, 109)]
        background_started = Event()
        finish_background = Event()
        with TemporaryDirectory() as folder:
            state, calls, controls, queue = SnapshotController().state(folder, lambda p: baseline if p == path else candidate)
            controls[611] = type(controls[101])()
            state.owned_preview = state.actions_open = False
            state.retained_streaming_items = lambda _, **kwargs: (None, False)
            state.streaming_snapshot = lambda _: None
            state.streaming_layout = lambda: state.page_definitions[0]['_streaming_layout']

            def background_fetch(path):
                calls.append(path)
                background_started.set()
                if not finish_background.wait(4):
                    raise RuntimeError('Timed out waiting for the fixture')
                return candidate

            state.warm_streaming_shelves = MethodType(
                live_method('warm_streaming_shelves', get_list=background_fetch), state)
            state.set_rows(rows)
            queue.pop(0)()
            with patch.object(provider_work, 'submit_streaming_warmup', queue.append):
                state.warm_streaming_shelves()
            warm = Thread(target=queue.pop(0), daemon=True)
            warm.start()
            try:
                self.assertTrue(background_started.wait(2))
                self.assertTrue(state.shift_rows(1, 0))
                visible = Thread(target=queue.pop(0), daemon=True)
                visible.start()
                self.assertEqual(calls, [path, rows[1]['path']])
            finally:
                finish_background.set()
                warm.join(3)
            visible.join(3)
            self.assertFalse(warm.is_alive() or visible.is_alive())
            state.settle_streaming_shelf()
            self.assertEqual(state.getProperty('row0'), rows[1]['label'])
            self.assertEqual(calls, [path, rows[1]['path']])

    def test_background_shelves_survive_a_new_window_without_refetch_until_expiry(self):
        from tempfile import TemporaryDirectory
        from types import MethodType
        from unittest.mock import patch
        from streaming_cache import StreamingRows
        from test_snapshot_controller import SnapshotController
        from test_streaming_foreground import live_method
        import provider_work

        path = BASE.replace('with_watch_providers=11', 'with_watch_providers=8')
        rows = service_shelves('Netflix', path, adaptive=True)['rows'][:6]
        empty, duplicate, first, second, third = [row['path'] for row in rows[1:]]
        baseline = [title(n) for n in range(1, 21)]
        fresh = {
            empty: [], duplicate: baseline,
            first: [dict(title(n), title=f'Title {n}', playcount=2) for n in range(100, 108)],
            second: [dict(title(n), title=f'Title {n}') for n in range(200, 208)],
            third: [dict(title(n), title=f'Title {n}') for n in range(300, 308)],
        }
        now = [1000]
        with TemporaryDirectory() as folder:
            state, calls, controls, queue = SnapshotController().state(folder, lambda _: baseline)
            controls[611] = type(controls[101])()
            state.owned_preview = False
            state.streaming_layout = lambda: state.page_definitions[0]['_streaming_layout']
            store = StreamingRows(Path(folder), 'scope', 'titles', clock=lambda: now[0])
            state.streaming_snapshot = lambda _: store
            state.retained_streaming_items = store.display
            state.warm_streaming_shelves = MethodType(
                live_method('warm_streaming_shelves', get_list=lambda p: calls.append(p) or fresh[p]), state)
            state.set_rows(rows)
            queue.pop(0)()
            with patch.object(provider_work, 'submit_streaming_warmup', queue.append):
                state.warm_streaming_shelves()
                queue.pop(0)()

            self.assertCountEqual(calls, [row['path'] for row in rows])
            reopened = StreamingRows(Path(folder), 'scope', 'titles', clock=lambda: now[0])
            state.result_cache.clear()
            state.retained_streaming_items = reopened.display
            for target in (first, second):
                files, refresh = state.retained_row_items({'path': target})
                self.assertEqual([item['file'] for item in files or []], [item['file'] for item in fresh[target]])
                self.assertTrue(all('playcount' not in item for item in files))
                self.assertFalse(refresh)
            for target in (empty, duplicate, third):
                self.assertIsNone(reopened.get(target))
            self.assertIsNone(StreamingRows(Path(folder), 'different-scope', 'titles', clock=lambda: now[0]).get(first))
            now[0] += 900
            stale, refresh = state.retained_row_items({'path': first})
            self.assertTrue(refresh)
            self.assertEqual([item['file'] for item in stale], [item['file'] for item in fresh[first]])
            self.assertCountEqual(calls, [row['path'] for row in rows])

    def test_jump_lists_cold_shelves_and_opens_only_the_selected_one(self):
        from tempfile import TemporaryDirectory
        from types import MethodType, SimpleNamespace
        from unittest.mock import patch
        from test_snapshot_controller import SnapshotController
        from test_streaming_foreground import live_method
        import provider_work

        path = BASE.replace('with_watch_providers=11', 'with_watch_providers=8')
        for candidate in ([title(301)], [], OSError('offline'), None):
            with self.subTest(candidate=candidate), TemporaryDirectory() as folder:
                rows = service_shelves('Netflix', path, adaptive=True)['rows'][:5]
                selected = rows[-1]

                def provider(requested):
                    if requested == path:
                        return [title(n) for n in range(1, 21)]
                    self.assertEqual(requested, selected['path'])
                    if isinstance(candidate, Exception):
                        raise candidate
                    return candidate

                state, calls, controls, queue = SnapshotController().state(folder, provider)
                controls[611] = type(controls[101])()
                state.owned_preview = state.actions_open = False
                state.warm_streaming_shelves = lambda: None
                state.streaming_layout = lambda: state.page_definitions[0]['_streaming_layout']
                state.jump_to_streaming_shelf = MethodType(
                    live_method('jump_to_streaming_shelf'), state)

                def select(heading, labels, *, preselect):
                    self.assertEqual((heading, preselect), ('Jump to row', 0))
                    self.assertEqual(labels, [row['label'] for row in rows])
                    self.assertEqual(calls, [path])
                    if candidate:
                        # The baseline can reorder genre rows while the native dialog is open.
                        state.page_definitions[1:] = reversed(state.page_definitions[1:])
                    return labels.index(selected['label'])

                jump = live_method('jump_streaming_shelf', xbmcgui=SimpleNamespace(
                    Dialog=lambda: SimpleNamespace(select=select)))
                state.set_rows(rows)
                queue.pop(0)()
                with patch.object(provider_work, 'submit_streaming_jump', queue.append, create=True):
                    jump(state)
                    self.assertEqual(state.getProperty('row0'), 'Browse All Movies')
                    self.assertEqual(calls, [path])
                    if candidate is None:
                        state.input_generation = 1
                    queue.pop(0)()
                if candidate is None:
                    self.assertEqual(calls, [path])
                    self.assertEqual(state.getProperty('row0'), 'Browse All Movies')
                    self.assertNotIn('Opening', state.getProperty('notice'))
                    continue
                self.assertEqual(calls, [path, selected['path']])
                self.assertEqual(state.focus, 900)
                if isinstance(candidate, Exception):
                    self.assertEqual(state.getProperty('row0'), 'Browse All Movies')
                    self.assertNotIn(selected['path'], state.streaming_layout().empty_shelves)
                    self.assertIn('could not load', state.getProperty('notice'))
                elif candidate:
                    self.assertEqual(state.getProperty('row0'), selected['label'])
                    self.assertEqual(state.rows[0], candidate)
                else:
                    self.assertEqual(state.getProperty('row0'), 'Browse All Movies')
                    self.assertIn(selected['path'], state.streaming_layout().empty_shelves)
                    self.assertIn('No titles', state.getProperty('notice'))
                self.assertEqual(queue, [])
