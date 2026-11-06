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
