import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location('row_ready', Path(__file__).parents[1] / 'tools/device_validation/row_readiness.py')
ready = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ready)


class RowReadiness(unittest.TestCase):
    def sample(self):
        return dict(eyebrow='YOUTUBE / HOME', states=['ready', 'ready'], counts=[20, 20], labels=['Recommended for you', 'Subscriptions'], routes=[{'provider':'plugin.video.youtube','kind':''}] * 2)

    def test_previous_home_cards_under_new_youtube_heading_are_rejected(self):
        value = self.sample()
        value['labels'] = ['Recommended shows', 'Recommended movies']
        self.assertFalse(ready.settled(value, 'YOUTUBE / HOME', ['Recommended for you', 'Subscriptions'], [{'provider':'plugin.video.youtube'}] * 2))

    def test_partial_row_replacement_is_rejected_even_if_headings_match(self):
        value = self.sample()
        value['routes'][1] = {'provider':'plugin.video.themoviedb.helper','kind':'movie'}
        self.assertFalse(ready.settled(value, 'YOUTUBE / HOME', value['labels'], [{'provider':'plugin.video.youtube'}] * 2))

    def test_fresh_both_rows_are_ready(self):
        value = self.sample()
        self.assertTrue(ready.settled(value, 'YOUTUBE / HOME', value['labels'], [{'provider':'plugin.video.youtube'}] * 2))

    def test_error_is_not_fast_success(self):
        value = self.sample()
        value['states'][1] = 'error'
        self.assertFalse(ready.settled(value, 'YOUTUBE / HOME', value['labels'], [None, None]))

    def test_empty_result_needs_its_own_heading(self):
        value = self.sample()
        value['states'][1] = 'empty'
        value['counts'][1] = 0
        value['labels'][1] = 'Subscriptions  ·  No titles'
        self.assertTrue(ready.settled(value, 'YOUTUBE / HOME', ['Recommended for you', 'Subscriptions'], [None, None]))

    def test_route_discards_all_sensitive_query_fields(self):
        self.assertEqual(ready.media_route('plugin://plugin.video.themoviedb.helper/?tmdb_type=tv&token=secret&tmdb_id=123'), {'provider':'plugin.video.themoviedb.helper','kind':'tv'})

    def test_empty_state_cannot_keep_previous_native_cards(self):
        value = self.sample()
        value['states'][1] = 'empty'
        value['labels'][1] += '  ·  No titles'
        self.assertFalse(ready.settled(value, 'YOUTUBE / HOME', ['Recommended for you', 'Subscriptions'], [None, None]))

    def test_ready_state_cannot_use_empty_row_heading(self):
        value = self.sample()
        value['labels'][1] += '  ·  No titles'
        self.assertFalse(ready.settled(value, 'YOUTUBE / HOME', ['Recommended for you', 'Subscriptions'], [None, None]))

    def test_route_never_exports_url_userinfo(self):
        self.assertEqual(ready.media_route('https://user:password@example.com/video?token=secret'), {'provider':'example.com','kind':''})
