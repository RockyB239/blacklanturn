"""Exercise title availability at the Helper HTTP and Kodi dialog boundaries."""

import importlib
import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.parse import urlencode, urlsplit


CONTROLLER = Path(__file__).resolve().parents[1] / 'controller-source' / 'addon'
AVAILABLE = {
    'id': 123,
    'results': {
        'US': {
            'link': 'https://www.themoviedb.org/tv/123/watch?locale=US',
            'flatrate': [
                {'provider_id': 9, 'provider_name': 'Amazon Prime Video'},
                {'provider_id': 1968, 'provider_name': 'Crunchyroll Amazon Channel'},
            ],
            'ads': [{'provider_id': 9, 'provider_name': 'Amazon Prime Video'}],
            'rent': [
                {'provider_id': 2, 'provider_name': 'Apple TV Store'},
                {'provider_id': 14, 'provider_name': 'Apple TV Store'},
            ],
            'buy': [{'provider_id': 2, 'provider_name': 'Apple TV Store'}],
        },
        'JP': {
            'link': 'https://www.themoviedb.org/tv/123/watch?locale=JP',
            'free': [{'provider_id': 198, 'provider_name': 'テレビ配信'}],
        },
        'GB': {'link': 'https://www.themoviedb.org/tv/123/watch?locale=GB'},
    },
}
REGIONS = {'JP': 'Japan', 'US': 'United States', 'GB': 'United Kingdom'}


class NativeDialog:
    def __init__(self, *choices):
        self.choices = iter(choices)
        self.menus = []
        self.details = []
        self.messages = []

    def select(self, heading, rows, **kwargs):
        self.menus.append((heading, list(rows), kwargs.get('preselect')))
        return next(self.choices)

    def textviewer(self, heading, text):
        self.details.append((heading, text))

    def ok(self, heading, text):
        self.messages.append((heading, text))


class TitleAvailability(unittest.TestCase):
    def setUp(self):
        self.requests = []
        self.payload = AVAILABLE

        class HelperAPI:
            req_api_url = 'https://api.themoviedb.org/3'
            req_language = 'en-US'

            def get_request_url(self, *parts, **params):
                query = urlencode(dict(params, api_key='fixture'))
                return self.req_api_url + '/' + '/'.join(parts) + '?' + query

        class Response(io.BytesIO):
            status = 200

        def open_request(request, *, timeout):
            url = urlsplit(request.full_url)
            self.requests.append((url.path, url.query, timeout))
            if isinstance(self.payload, Exception):
                raise self.payload
            return Response(json.dumps(self.payload).encode())

        helper = SimpleNamespace(getAddonInfo=lambda field: '/installed/helper')
        modules = patch.dict(sys.modules, {
            'xbmcaddon': SimpleNamespace(Addon=lambda ident: helper),
            'tmdbhelper.lib.api.tmdb.api': SimpleNamespace(TMDbAPI=HelperAPI),
            'tmdbhelper.lib.addon.consts': SimpleNamespace(DISCOVER_REGIONS=(
                {'id': 'US', 'name': 'United States of America (US)'},
                {'id': 'JP', 'name': 'Japan (JP)'},
            )),
        })
        modules.start()
        self.addCleanup(modules.stop)
        paths = patch.object(sys, 'path', [str(CONTROLLER), *sys.path])
        paths.start()
        self.addCleanup(paths.stop)
        transport = patch('urllib.request.build_opener',
                          return_value=SimpleNamespace(open=open_request))
        transport.start()
        self.addCleanup(transport.stop)
        self.availability = importlib.import_module('streaming_availability')

    def test_merges_all_offer_types_by_id_within_each_country(self):
        results = self.availability.load_title_availability('tv', '123')

        providers = results['US'].providers
        self.assertEqual([(item.provider_id, item.name, item.offers) for item in providers], [
            (9, 'Amazon Prime Video', ('Subscription', 'With ads')),
            (1968, 'Crunchyroll Amazon Channel', ('Subscription',)),
            (2, 'Apple TV Store', ('Rent', 'Buy')),
            (14, 'Apple TV Store', ('Rent',)),
        ])
        self.assertEqual(results['JP'].providers[0].name, 'テレビ配信')
        self.assertEqual(results['US'].link, AVAILABLE['results']['US']['link'])
        self.assertEqual(self.requests, [('/3/tv/123/watch/providers', 'language=en-US&api_key=fixture', 4)])

    def test_movie_uses_one_exact_movie_endpoint(self):
        self.payload = {'id': 321, 'results': {}}
        self.assertEqual(self.availability.load_title_availability('movie', 321), {})
        self.assertEqual(self.requests, [('/3/movie/321/watch/providers', 'language=en-US&api_key=fixture', 4)])

    def test_invalid_title_identity_is_rejected_before_network(self):
        for kind, identity in [('episode', 123), ('movie', True), ('tv', '0'), ('tv', '123/episodes')]:
            with self.subTest(kind=kind, identity=identity), self.assertRaises(ValueError):
                self.availability.load_title_availability(kind, identity)
        self.assertEqual(self.requests, [])

    def test_browses_current_and_worldwide_regions_from_one_title_request(self):
        dialog = NativeDialog(0, 1, 0, -1, -1)
        self.availability.show_where_to_watch(dialog, 'tv', '123', 'The Series', 'US', REGIONS)

        self.assertEqual(dialog.menus[0][1], ['United States', 'All Regions'])
        self.assertEqual(dialog.menus[2][1], ['Japan · 1 provider', 'United States · 4 providers'])
        self.assertEqual(dialog.menus[3][2], 0)
        self.assertIn('United States', dialog.details[0][0])
        self.assertIn('Amazon Prime Video · Subscription, With ads', dialog.details[0][1])
        self.assertIn('Series-level availability', dialog.details[0][1])
        self.assertIn('JustWatch', dialog.details[0][1])
        self.assertIn(AVAILABLE['results']['US']['link'], dialog.details[0][1])
        self.assertIn('Japan', dialog.details[1][0])
        self.assertIn('テレビ配信', dialog.details[1][1])
        self.assertIn(AVAILABLE['results']['JP']['link'], dialog.details[1][1])
        self.assertEqual(self.requests, [('/3/tv/123/watch/providers', 'language=en-US&api_key=fixture', 4)])

    def test_selecting_unlisted_country_offers_worldwide_as_back_path(self):
        dialog = NativeDialog(0, -1)
        self.availability.show_where_to_watch(dialog, 'tv', 123, 'The Series', 'GB', REGIONS)

        heading, text = dialog.details[0]
        self.assertIn('United Kingdom', heading)
        self.assertIn('No providers listed', text)
        self.assertIn(AVAILABLE['results']['GB']['link'], text)
        self.assertEqual(len(dialog.menus), 2)

    def test_distinguishes_empty_worldwide_data_from_unavailable_or_malformed_response(self):
        for payload, empty in [
            ({'id': 123, 'results': {}}, True),
            ({'id': 123, 'results': []}, False),
            ({'id': 124, 'results': {}}, False),
            ({'id': 123, 'results': {'US': {'rent': 'invalid'}}}, False),
            (TimeoutError('must not be shown'), False),
        ]:
            with self.subTest(payload=payload):
                self.payload = payload
                dialog = NativeDialog(1, -1)
                self.availability.show_where_to_watch(dialog, 'tv', 123, 'The Series', 'US', REGIONS)
                if empty:
                    self.assertIn('No providers listed', dialog.details[0][1])
                    self.assertEqual(dialog.messages, [])
                else:
                    self.assertIn('Could not load', dialog.messages[0][1])
                    self.assertNotIn('must not be shown', dialog.messages[0][1])
                    self.assertEqual(dialog.details, [])

    def test_cold_country_names_come_from_installed_helper_without_a_second_request(self):
        dialog = NativeDialog(1, -1, -1)
        self.availability.show_where_to_watch(dialog, 'tv', 123, 'The Series', 'US')

        self.assertEqual(dialog.menus[0][1], ['United States of America', 'All Regions'])
        self.assertEqual(dialog.menus[1][1], ['Japan · 1 provider', 'United States of America · 4 providers'])
        self.assertEqual(len(self.requests), 1)

    def test_back_from_initial_region_picker_does_not_fetch_title(self):
        dialog = NativeDialog(-1)
        self.availability.show_where_to_watch(dialog, 'tv', 123, 'The Series', 'US')
        self.assertEqual(self.requests, [])
        self.assertEqual(dialog.details, [])


if __name__ == '__main__':
    unittest.main()
