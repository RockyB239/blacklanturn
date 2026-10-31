"""Import the real controller closure in a fresh interpreter, without Kodi data.

AST-extracted controller tests cannot detect transitive import startup cost.
Only the Kodi boundary is stubbed here; all controller modules are real imports.
"""
import subprocess
import sys
import unittest
from pathlib import Path


ADDON = Path(__file__).resolve().parents[1] / 'addon'
PROBE = r'''
import importlib, json, sys, tempfile, threading, types
from pathlib import Path
sys.path.insert(0, sys.argv[1])
module_name = sys.argv[2]
forbidden = ('urllib.request', 'ssl', 'http.client')
assert not any(name in sys.modules for name in forbidden), 'Probe preloaded networking'
class NoNetworkImports:
    def find_spec(self, fullname, path=None, target=None):
        if fullname in forbidden:
            raise AssertionError('Startup imported network transport: ' + fullname)
sys.meta_path.insert(0, NoNetworkImports())
def unexpected(*args, **kwargs):
    raise AssertionError('Import invoked a Kodi operation')
with tempfile.TemporaryDirectory() as folder:
    class Player:
        pass
    class WindowXML:
        pass
    class WindowXMLDialog:
        pass
    sys.modules['xbmc'] = types.SimpleNamespace(Player=Player, executeJSONRPC=unexpected)
    sys.modules['xbmcgui'] = types.SimpleNamespace(WindowXML=WindowXML, WindowXMLDialog=WindowXMLDialog)
    sys.modules['xbmcvfs'] = types.SimpleNamespace(translatePath=lambda _: folder)
    sys.modules['xbmcaddon'] = types.SimpleNamespace(Addon=lambda _: types.SimpleNamespace(getAddonInfo=lambda _: folder))
    before_threads = set(threading.enumerate())
    module = importlib.import_module(module_name)
    assert set(threading.enumerate()) == before_threads, 'Import started background work'
    assert not any(name in sys.modules for name in forbidden)
    if module_name == 'live_review':
        assert module.LiveReview.__module__ == 'live_review'
        for dependency in ('preview_identity', 'release_updates'):
            assert dependency in sys.modules, 'Dependency closure was not exercised: ' + dependency
    elif module_name == 'preview_identity':
        assert module.fetch_public_title('invalid-id') == ''
    elif module_name == 'series_metadata':
        assert module.load_show_package('invalid-id') == {}
    elif module_name == 'release_updates':
        path = Path(folder) / 'catalog.json'
        path.write_text(json.dumps({'schema': 1, 'releases': []}))
        assert module.fetch_catalog(path.as_uri()) == {'schema': 1, 'releases': []}
    assert not any(name in sys.modules for name in forbidden)
'''


class StartupNetworkImports(unittest.TestCase):
    def probe(self, module):
        result = subprocess.run([sys.executable, '-I', '-c', PROBE, str(ADDON), module],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_real_controller_dependency_closure_avoids_network_transport_at_import(self):
        self.probe('live_review')

    def test_release_import_and_local_catalog_do_not_load_network_transport(self):
        self.probe('release_updates')

    def test_series_import_and_invalid_identity_do_not_load_network_transport(self):
        self.probe('series_metadata')

    def test_preview_import_and_invalid_identity_do_not_load_network_transport(self):
        self.probe('preview_identity')


if __name__ == '__main__':
    unittest.main()
