"""Regression tests for the regional directory's public data boundary."""
import json
from pathlib import Path
import ssl
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import regional_catalog
from streaming_services import ServiceCatalog


def provider(ident=8, name='Netflix', priority=1, **changes):
    return dict(
        {'provider_id': ident, 'provider_name': name, 'display_priority': priority,
         'logo_path': '/logo.png', 'display_priorities': {'GB': 0, 'US': 999}},
        **changes
    )


class CatalogTests(unittest.TestCase):
    def setUp(self):
        folder = TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.profile = Path(folder.name)
        self.now = 1000
        self.allowlist = ''
        self.responses = {}
        self.calls = []
        self.helper = SimpleNamespace(
            getAddonInfo=lambda name: '/installed/helper',
            getSettingString=lambda name: self.allowlist,
        )
        kodi = patch.dict(sys.modules, {'xbmcaddon': SimpleNamespace(Addon=lambda ident: self.helper)})
        kodi.start()
        self.addCleanup(kodi.stop)
        self.catalog = self.new_catalog()

    def new_catalog(self):
        return regional_catalog.RegionalCatalog(self.profile, fetch=self.fetch, clock=lambda: self.now)

    def fetch(self, *parts, **params):
        self.calls.append((parts, params))
        value = self.responses.get((parts[-1], params.get('watch_region')))
        if isinstance(value, Exception):
            raise value
        return value

    def test_preference_persists_and_invalid_input_cannot_replace_it(self):
        self.assertEqual(self.catalog.selected('GB'), 'GB')
        self.assertTrue(self.catalog.select('CA'))
        self.assertFalse(self.catalog.select('../US'))
        self.assertEqual(self.new_catalog().selected('US'), 'CA')
        self.assertEqual(self.calls, [])
        pins = self.profile / 'addon_data/script.blacklanturn.preview/streaming-service-pins.json'
        self.assertFalse(pins.exists())

    def test_atomic_preference_failure_retains_previous_choice(self):
        self.assertTrue(self.catalog.select('CA'))
        with patch('regional_catalog.os.replace', side_effect=OSError('profile is read-only')):
            self.assertFalse(self.catalog.select('GB'))
        self.assertEqual(self.new_catalog().selected('US'), 'CA')
        self.assertFalse(list(self.profile.rglob('*.tmp')))

    def test_current_helper_country_is_independent_of_preference(self):
        helper_module = SimpleNamespace(get_language=lambda: 'fr-CA')
        with patch.dict(sys.modules, {'tmdbhelper.lib.addon.plugin': helper_module}):
            self.assertTrue(self.catalog.select('GB'))
            self.assertEqual(self.catalog.default_region(), 'CA')
            self.assertEqual(self.catalog.selected(self.catalog.default_region()), 'GB')
        self.assertEqual(self.calls, [])

    def test_helper_country_names_are_local_and_do_not_imply_supported_membership(self):
        constants = SimpleNamespace(DISCOVER_REGIONS=(
            {'id': 'US', 'name': 'United States of America (US)'},
            {'id': 'AF', 'name': 'Afghanistan (AF)'},
        ))
        with patch.dict(sys.modules, {'tmdbhelper.lib.addon.consts': constants}):
            self.assertEqual(regional_catalog.helper_region_names(),
                             {'US': 'United States of America', 'AF': 'Afghanistan'})
        self.assertEqual(self.catalog.cached_regions(), ({}, False))
        self.assertEqual(self.calls, [])

    def test_picker_uses_full_country_names_and_retains_last_good_after_error(self):
        self.responses['regions', None] = {'results': [
            {'iso_3166_1': 'GB', 'english_name': 'United Kingdom', 'native_name': 'UK'},
            {'iso_3166_1': 'GP', 'english_name': 'Guadeloupe', 'native_name': 'Guadeloupe'},
        ]}
        countries = {'GB': 'United Kingdom', 'GP': 'Guadeloupe'}
        self.assertEqual(self.catalog.cached_regions(), ({}, False))
        self.assertEqual(self.catalog.regions(), (countries, 'fresh'))
        self.assertEqual(self.new_catalog().cached_regions(), (countries, True))
        self.assertEqual(self.new_catalog().regions(), (countries, 'fresh'))
        self.assertEqual(self.calls, [(('watch', 'providers', 'regions'), {})])
        self.now += 365 * 24 * 3600
        self.responses['regions', None] = {'results': [{'iso_3166_1': '../US'}]}
        self.assertEqual(self.catalog.regions(), (countries, 'stale'))

    def test_cold_lookup_failure_and_verified_empty_are_distinct(self):
        self.responses['movie', 'GP'] = {'results': []}
        self.responses['tv', 'GP'] = TimeoutError()
        self.assertEqual(self.catalog.cached('movie', 'GP'), (None, False))
        self.assertEqual(self.calls, [])
        self.assertEqual(self.catalog.load('movie', 'GP'), ([], 'fresh'))
        self.assertEqual(self.catalog.load('tv', 'GP'), (None, 'error'))
        self.assertEqual(self.new_catalog().cached('movie', 'GP'), ([], True))
        self.assertEqual(self.new_catalog().cached('tv', 'GP'), (None, False))
        self.assertEqual(self.catalog.regions(), ({}, 'error'))

    def test_region_and_media_membership_are_separate_and_routes_are_native(self):
        self.responses['movie', 'GB'] = {'results': [
            provider(8, 'Netflix', 5, display_priorities={'GB': 0}),
            provider(9, 'Amazon Prime Video', 1, display_priorities={'GB': 99}),
        ]}
        self.responses['movie', 'US'] = {'results': [provider(8)]}
        self.responses['tv', 'GB'] = {'results': [provider(15, 'Hulu')]}
        for kind, country, keys in (
            ('movie', 'GB', ['GB:9', 'GB:8']),
            ('movie', 'US', ['US:8']),
            ('tv', 'GB', ['GB:15']),
        ):
            with self.subTest(kind=kind, country=country):
                cards, state = self.catalog.load(kind, country)
                self.assertEqual(state, 'fresh')
                self.assertEqual(list(ServiceCatalog(cards).services), keys)
                self.assertEqual(self.new_catalog().cached(kind, country), (cards, True))
        cards, _ = self.catalog.cached('movie', 'GB')
        self.assertEqual(cards[0]['title'], 'Amazon Prime Video · GB')
        self.assertEqual(cards[0]['art']['icon'], 'https://image.tmdb.org/t/p/w185/logo.png')
        self.assertEqual(cards[0]['file'], 'plugin://plugin.video.themoviedb.helper/?info=discover'
                         '&tmdb_type=movie&with_watch_providers=9&watch_region=GB&with_id=true'
                         '&nextpage=true&widget=false')
        self.assertEqual(self.calls, [
            (('watch', 'providers', 'movie'), {'watch_region': 'GB'}),
            (('watch', 'providers', 'movie'), {'watch_region': 'US'}),
            (('watch', 'providers', 'tv'), {'watch_region': 'GB'}),
        ])

    def test_allowlist_changes_also_filter_fresh_cached_membership(self):
        self.responses['movie', 'CA'] = {'results': [provider(8), provider(9, "CBC's Gem")]}
        self.allowlist = "CBC's Gem | Hulu"
        cards, state = self.catalog.load('movie', 'CA')
        self.assertEqual((list(ServiceCatalog(cards).services), state), (['CA:9'], 'fresh'))
        self.allowlist = 'Netflix'
        cards, fresh = self.catalog.cached('movie', 'CA')
        self.assertEqual((list(ServiceCatalog(cards).services), fresh), (['CA:8'], True))
        self.allowlist = 'Hulu'
        self.assertEqual(self.catalog.load('movie', 'CA'), ([], 'fresh'))
        self.assertEqual(len(self.calls), 1)

    def test_malformed_refresh_retains_last_good_and_success_replaces_it(self):
        self.responses['movie', 'CA'] = {'results': [provider(8), provider(9, 'Prime Video')]}
        first, _ = self.catalog.load('movie', 'CA')
        self.now += 365 * 24 * 3600
        self.responses['movie', 'CA'] = {'results': [provider(8), provider(9, 'Prime Video',
                                             logo_path='https://example.com/logo.png')]}
        self.assertEqual(self.catalog.load('movie', 'CA'), (first, 'stale'))
        self.assertEqual(self.new_catalog().cached('movie', 'CA'), (first, False))
        self.responses['movie', 'CA'] = {'results': []}
        self.assertEqual(self.catalog.load('movie', 'CA'), ([], 'fresh'))
        self.assertEqual(self.new_catalog().cached('movie', 'CA'), ([], True))

    def test_verified_empty_is_scoped_and_expires_without_losing_membership(self):
        self.responses['movie', 'CA'] = {'results': [provider(8), provider(9, 'Prime Video')]}
        self.responses['tv', 'CA'] = {'results': [provider(8)]}
        self.responses['movie', 'GB'] = {'results': [provider(8)]}
        ca_movies, _ = self.catalog.load('movie', 'CA')
        ca_shows, _ = self.catalog.load('tv', 'CA')
        gb_movies, _ = self.catalog.load('movie', 'GB')
        self.assertTrue(self.catalog.mark_empty('movie', 'CA', '8'))
        reopened = self.new_catalog()
        visible = reopened.visible(ca_movies, 'movie', 'CA')
        self.assertEqual(list(ServiceCatalog(visible).services), ['CA:9'])
        self.assertEqual(reopened.visible(ca_shows, 'tv', 'CA'), ca_shows)
        self.assertEqual(reopened.visible(gb_movies, 'movie', 'GB'), gb_movies)
        self.assertEqual(reopened.cached('movie', 'CA'), (ca_movies, True))
        self.now += 601
        self.assertEqual(reopened.visible(ca_movies, 'movie', 'CA'), ca_movies)
        self.assertEqual(len(self.calls), 3)

    def test_verified_empty_merge_preserves_each_provider(self):
        self.responses['movie', 'CA'] = {'results': [provider(8), provider(9, 'Prime Video')]}
        cards, _ = self.catalog.load('movie', 'CA')
        second = self.new_catalog()
        self.assertTrue(self.catalog.mark_empty('movie', 'CA', 8))
        self.assertTrue(second.mark_empty('movie', 'CA', 9))
        self.assertFalse(second.mark_empty('movie', 'CA', '8|9'))
        self.assertEqual(self.catalog.visible(cards, 'movie', 'CA'), [])

    def test_verified_positive_clears_only_the_exact_empty_provider(self):
        self.responses['movie', 'CA'] = {'results': [provider(8), provider(9, 'Prime Video')]}
        cards, _ = self.catalog.load('movie', 'CA')
        self.assertTrue(self.catalog.mark_empty('movie', 'CA', 8))
        self.assertTrue(self.catalog.mark_empty('movie', 'CA', 9))
        self.assertTrue(self.catalog.mark_available('movie', 'CA', 8))
        reopened = self.new_catalog()
        self.assertEqual(list(ServiceCatalog(reopened.visible(cards, 'movie', 'CA')).services),
                         ['CA:8'])

    def test_corrupt_verified_empty_stamp_cannot_hide_a_provider_or_break_grid(self):
        self.now = 1000.0
        self.responses['movie', 'CA'] = {'results': [provider(8)]}
        cards, _ = self.catalog.load('movie', 'CA')
        self.assertTrue(self.catalog.mark_empty('movie', 'CA', 8))
        marks = next(self.profile.rglob('empty-movie-CA.json'))
        document = json.loads(marks.read_text())
        document['providers']['8'] = 10 ** 400
        marks.write_text(json.dumps(document))
        self.assertEqual(self.catalog.visible(cards, 'movie', 'CA'), cards)

    def test_invalid_scope_is_rejected_before_fetch(self):
        for kind, region in (('person', 'US'), ('movie', '../US'), ('tv', 'us')):
            self.assertEqual(self.catalog.load(kind, region), (None, 'error'))
        self.assertEqual(self.calls, [])


class PublicTransportTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.value = b'{"results":[]}'
        self.generated_region = 'CA'
        transport = self

        class HelperApi:
            req_api_url = 'https://api.themoviedb.org/3'
            req_language = 'en-US'

            def get_request_url(self, *parts, **params):
                transport.calls.append((parts, params))
                route = '/'.join(parts)
                region = f'&watch_region={transport.generated_region}' if 'watch_region' in params else ''
                return f'{self.req_api_url}/{route}?api_key=fake&language=en-US{region}'

        self.certifi_addon = None
        helper = SimpleNamespace(getAddonInfo=lambda name: '/installed/helper')

        def installed_addon(ident):
            if ident == 'script.module.certifi':
                if self.certifi_addon is None:
                    raise RuntimeError('not installed')
                return SimpleNamespace(getAddonInfo=lambda name: 'special://home/addons/script.module.certifi')
            return helper

        kodi = patch.dict(sys.modules, {
            'xbmcaddon': SimpleNamespace(Addon=installed_addon),
            'xbmcvfs': SimpleNamespace(translatePath=lambda path: str(self.certifi_addon)),
            'tmdbhelper.lib.api.tmdb.api': SimpleNamespace(TMDbAPI=HelperApi),
        })
        kodi.start()
        self.addCleanup(kodi.stop)

        class Response:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def read(self, limit):
                transport.calls.append(('read', limit))
                return transport.value

        def open_request(request, *, timeout):
            self.calls.append(('open', request.get_method(), timeout))
            return Response()

        opener = patch('urllib.request.build_opener', return_value=SimpleNamespace(open=open_request))
        self.opener = opener.start()
        self.addCleanup(opener.stop)

    def installed_certificate_bundle(self):
        folder = TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.certifi_addon = Path(folder.name)
        bundle = self.certifi_addon / 'lib/certifi/cacert.pem'
        bundle.parent.mkdir(parents=True)
        bundle.write_text('test bundle')
        return bundle

    def test_verified_https_uses_kodi_certifi_and_does_not_follow_redirects(self):
        bundle = self.installed_certificate_bundle()
        verified_context = ssl.create_default_context()
        with patch('ssl.create_default_context', return_value=verified_context) as context:
            self.assertEqual(regional_catalog.fetch_public_tmdb('watch', 'providers', 'regions'),
                             {'results': []})
        context.assert_called_once_with(cafile=str(bundle))
        redirect, https = self.opener.call_args.args
        self.assertIsNone(redirect.redirect_request(None, None, 302, '', {}, 'https://example.com/'))
        self.assertIs(https._context, verified_context)
        self.assertTrue(https._context.check_hostname)
        self.assertEqual(https._context.verify_mode, ssl.CERT_REQUIRED)

    def test_absent_bundle_keeps_platform_default_https(self):
        bundle = self.installed_certificate_bundle()
        bundle.unlink()
        with patch('ssl.create_default_context') as context:
            self.assertEqual(regional_catalog.fetch_public_tmdb('watch', 'providers', 'regions'),
                             {'results': []})
        context.assert_not_called()
        redirect, https = self.opener.call_args.args
        self.assertIsNone(https._context)
        self.assertIsNone(redirect.redirect_request(None, None, 302, '', {}, 'https://example.com/'))

    def test_invalid_installed_bundle_fails_before_request(self):
        self.installed_certificate_bundle()
        with self.assertRaisesRegex(ValueError, '^Public provider request failed$'):
            regional_catalog.fetch_public_tmdb('watch', 'providers', 'regions')
        self.opener.assert_not_called()

    def test_explicit_regional_request_has_a_time_and_body_limit(self):
        self.assertEqual(regional_catalog.fetch_public_tmdb('watch', 'providers', 'movie', watch_region='CA'),
                         {'results': []})
        self.assertEqual(self.calls, [
            (('watch', 'providers', 'movie'), {'language': 'en-US', 'watch_region': 'CA'}),
            ('open', 'GET', 4), ('read', 1024 * 1024 + 1),
        ])
        self.value = b' ' * (1024 * 1024 + 1)
        with self.assertRaises(ValueError):
            regional_catalog.fetch_public_tmdb('watch', 'providers', 'movie', watch_region='CA')

    def test_mismatched_generated_region_is_rejected_before_open(self):
        self.generated_region = 'GB'
        with self.assertRaises(ValueError):
            regional_catalog.fetch_public_tmdb('watch', 'providers', 'movie', watch_region='CA')
        self.assertEqual(self.calls, [
            (('watch', 'providers', 'movie'), {'language': 'en-US', 'watch_region': 'CA'}),
        ])

    def test_title_endpoint_admits_int32_ids_and_excludes_regional_filters(self):
        self.assertEqual(regional_catalog.fetch_public_tmdb('tv', '2147483647', 'watch', 'providers'),
                         {'results': []})
        with self.assertRaises(ValueError):
            regional_catalog.fetch_public_tmdb('tv', '2147483648', 'watch', 'providers')
        self.assertEqual(self.calls, [
            (('tv', '2147483647', 'watch', 'providers'), {'language': 'en-US'}),
            ('open', 'GET', 4), ('read', 1024 * 1024 + 1),
        ])

    def test_unsupported_routes_do_not_reach_helper(self):
        with self.assertRaises(ValueError):
            regional_catalog.fetch_public_tmdb('account', '1')
        self.assertEqual(self.calls, [])


if __name__ == '__main__':
    unittest.main()
