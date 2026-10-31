"""Lazy imports must retain transport authority and existing request bounds."""
import ast
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import urlencode

ADDON = Path(__file__).resolve().parents[1] / 'addon'
sys.path.insert(0, str(ADDON))
import preview_identity
import release_updates


class Response:
    def __init__(self, raw):
        self.raw = raw
        self.read_sizes = []
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def read(self, size=-1):
        self.read_sizes.append(size)
        return self.raw


class DeferredNetworkPolicies(unittest.TestCase):
    def test_default_preview_transport_retains_no_redirect_handler_and_bounds(self):
        from urllib.request import HTTPRedirectHandler
        response = Response(b'{"title":"Example Trailer"}')
        with patch('urllib.request.build_opener') as build:
            build.return_value.open.return_value = response
            self.assertEqual(preview_identity.fetch_public_title('00000000001'), 'Example Trailer')
        handler, = build.call_args.args
        self.assertIsInstance(handler, HTTPRedirectHandler)
        for code in (301, 302, 303, 307, 308):
            self.assertIsNone(handler.redirect_request(None, None, code, '', {}, 'https://other.example/'))
        request, = build.return_value.open.call_args.args
        self.assertTrue(request.full_url.startswith('https://www.youtube.com/oembed?'))
        self.assertEqual(request.get_header('Accept'), 'application/json')
        self.assertEqual(build.return_value.open.call_args.kwargs, {'timeout': 2})
        self.assertEqual(response.read_sizes, [65537])

    def test_release_transport_retains_host_check_and_two_second_socket_timeout(self):
        response = Response(b'')
        response.url = 'https://other.example/catalog.json'
        with patch('urllib.request.urlopen', return_value=response) as fetch:
            with self.assertRaisesRegex(ValueError, 'Unexpected catalog redirect'):
                release_updates.fetch_catalog()
        request, = fetch.call_args.args
        self.assertEqual(request.full_url, release_updates.FEED)
        self.assertEqual(request.get_header('User-agent'), 'BlackLanturn/1')
        self.assertEqual(fetch.call_args.kwargs, {'timeout': 2})
        self.assertEqual(response.read_sizes, [])

    def test_selected_ratings_retains_certifi_context_timeout_and_existing_worker(self):
        class ImmediateThread:
            created = []
            def __init__(self, target, name, daemon):
                self.target = target
                self.created.append((name, daemon))
            def start(self):
                self.target()
        source = ast.parse((ADDON / 'live_review.py').read_text())
        cls = next(node for node in source.body if isinstance(node, ast.ClassDef) and node.name == 'LiveReview')
        method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == 'selected_ratings')
        events = []
        namespace = {
            'PROFILE': Path('/test-profile/userdata'), 'json': json, 'urlencode': urlencode,
            'xbmcaddon': SimpleNamespace(Addon=lambda _: SimpleNamespace(getSetting=lambda _: 'test-key')),
            'threading': SimpleNamespace(Thread=ImmediateThread),
            'rating_badges': lambda item, data: [{'icon': 'imdb', 'value': '8'}],
            'event': lambda *args, **kwargs: events.append((args, kwargs)),
        }
        exec(compile(ast.Module(body=[method], type_ignores=[]), 'selected-ratings', 'exec'), namespace)
        displayed = []
        owner = SimpleNamespace(selected={'title': 'Example'}, rating_identity=lambda _: ('movie', '1'),
                                rating_busy=False, rating_cache={}, alive=True, display_ratings=displayed.append)
        context = object()
        with patch('ssl.create_default_context', return_value=context) as tls, \
                patch('urllib.request.urlopen', return_value=Response(b'{}')) as fetch:
            namespace['selected_ratings'](owner)
        tls.assert_called_once_with(cafile='/test-profile/addons/script.module.certifi/lib/certifi/cacert.pem')
        request, = fetch.call_args.args
        self.assertEqual(request.full_url, 'https://api.mdblist.com/tmdb/movie/1?apikey=test-key')
        self.assertEqual(request.get_header('User-agent'), 'Kodi/21.3 BlackLanturnReview')
        self.assertEqual(fetch.call_args.kwargs, {'timeout': 8, 'context': context})
        self.assertEqual(ImmediateThread.created, [('BlackLanturnSelectedRatings', True)])
        self.assertFalse(owner.rating_busy)
        self.assertEqual(owner.rating_cache[('movie', '1')], displayed[0])
        self.assertEqual(events[0][0], ('critic_ratings_loaded',))


if __name__ == '__main__':
    unittest.main()
