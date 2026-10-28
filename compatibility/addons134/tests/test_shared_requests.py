"""Exercise real RequestAPI branches with synthetic responses, never account APIs."""
import importlib.util
from pathlib import Path
import sys
import time
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'patched/script.module.jurialmunkey/resources/modules/jurialmunkey/reqapi.py'


class SharedRequestTests(unittest.TestCase):
    def setUp(self):
        self.properties = {}
        def prop(key, value=None, **kwargs):
            if value is not None:
                self.properties[key] = value
            return self.properties.get(key)
        def timestamp(value):
            return bool(value and value > time.time())
        modules = {
            'xbmc': types.SimpleNamespace(getCondVisibility=lambda _: True, Monitor=lambda: None),
            'xbmcgui': types.SimpleNamespace(Dialog=lambda: None),
            'jurialmunkey.parser': types.SimpleNamespace(try_int=lambda n: int(n)),
            'jurialmunkey.window': types.SimpleNamespace(get_property=prop),
            'jurialmunkey.tmdate': types.SimpleNamespace(get_timestamp=timestamp, set_timestamp=lambda n: time.time()+n),
            'jurialmunkey.plugin': types.SimpleNamespace(KodiPlugin=lambda _: types.SimpleNamespace(get_localized=lambda _: '{}')),
            'jurialmunkey.bcache': types.SimpleNamespace(BasicCache=type('Cache', (), {'__init__': lambda *args, **kwargs: None})),
        }
        self.context = patch.dict(sys.modules, modules)
        self.context.start(); self.addCleanup(self.context.stop)
        spec = importlib.util.spec_from_file_location('shared_requests_under_test', SOURCE)
        self.module = importlib.util.module_from_spec(spec); spec.loader.exec_module(self.module)
        self.api = self.module.RequestAPI(req_api_name='synthetic-test')
        self.logs = []; self.calls = []
        self.api.kodi_log = lambda message, level=0: self.logs.append(str(message))

    def respond(self, code, headers=None):
        response = types.SimpleNamespace(status_code=code, headers=headers or {})
        def transport(*args):
            self.calls.append(args)
            return response
        self.api.get_simple_api_request = transport
        return response

    def test_retry_after_is_honored_and_next_request_is_suppressed_without_sleep(self):
        self.respond(429, {'Retry-After': '120'})
        start = time.time()
        self.assertIsNone(self.api.get_api_request('https://example.invalid/path'))
        self.assertGreaterEqual(self.api.req_connect_err, start + 120)
        self.assertIsNone(self.api.get_api_request('https://example.invalid/path'))
        self.assertEqual(len(self.calls), 1)
        self.assertLess(time.time()-start, 1)

    def test_missing_invalid_negative_and_short_cooldowns_use_one_minute_floor(self):
        for value in (None, '', 'invalid', '-1', '0', '15'):
            with self.subTest(value=value):
                self.api.req_connect_err = 0
                self.respond(429, {} if value is None else {'Retry-After': value})
                start = time.time(); self.api.get_api_request('https://example.invalid/path')
                self.assertGreaterEqual(self.api.req_connect_err, start + 60)
                self.assertLess(self.api.req_connect_err, start + 62)

    def test_error_logs_keep_status_and_host_without_request_or_response_secrets(self):
        for code in (401, 403, 404, 422):
            with self.subTest(code=code):
                self.logs.clear(); self.respond(code)
                self.api.get_api_request('https://user_secret:password_secret@example.invalid/private_secret?token=query_secret',
                                         {'password': 'body_secret'}, {'Authorization': 'Bearer header_secret'})
                logged = '\n'.join(self.logs)
                self.assertIn(str(code), logged); self.assertIn('example.invalid', logged)
                for secret in ('user_secret', 'password_secret', 'private_secret', 'query_secret', 'body_secret', 'header_secret', 'namespace('):
                    self.assertNotIn(secret, logged)

    def test_success_returns_original_response_without_extra_work(self):
        response = self.respond(200)
        self.assertIs(self.api.get_api_request('https://example.invalid/path'), response)
        self.assertEqual(len(self.calls), 1); self.assertEqual(self.logs, [])
        self.assertEqual(self.api.req_connect_err, 0)

    def test_service_unavailable_keeps_existing_five_minute_cooldown(self):
        self.respond(503)
        start = time.time(); self.api.get_api_request('https://example.invalid/path')
        self.assertGreaterEqual(self.api.req_connect_err, start + 300)


if __name__ == '__main__': unittest.main()
