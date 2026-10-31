"""Keep explicit settings/playback helpers outside the initial Home closure."""
import subprocess
import sys
import unittest
from test_startup_network_imports import ADDON, PROBE


class StartupActionImports(unittest.TestCase):
    def probe(self, extra):
        result = subprocess.run(
            [sys.executable, '-I', '-B', '-c', PROBE + extra, str(ADDON), 'live_review'],
            capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_initial_window_does_not_import_eight_action_only_modules(self):
        self.probe(r'''
import ast
optional = {'backend_core', 'backend_ui', 'playback_info', 'playback_runtime',
            'icon_picker', 'genre_picker', 'related_titles', 'preview_language'}
assert not optional & sys.modules.keys(), sorted(optional & sys.modules.keys())
# Exercise the real launcher function, including its pre-modal imports.
def initialize(self, *args, **kwargs):
    self.core_settings_request = None
sys.modules['xbmcgui'].WindowXML.__init__ = initialize
sys.modules['xbmcgui'].WindowXML.doModal = lambda self: None
sys.modules['xbmc'].getSkinDir = lambda: 'skin.blacklanturn.preview'
sys.modules['xbmc'].Monitor = lambda: types.SimpleNamespace(abortRequested=lambda: False)
tree = ast.parse((Path(sys.argv[1]) / 'default.py').read_text())
launch = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'run_live_review')
namespace = {'ROOT': module.ROOT, 'xbmc': sys.modules['xbmc']}
exec(compile(ast.Module(body=[launch], type_ignores=[]), 'default.py', 'exec'), namespace)
namespace['run_live_review']()
assert not optional & sys.modules.keys(), sorted(optional & sys.modules.keys())
''')

    def test_first_actions_preserve_forwarding_signatures_and_native_dialog_types(self):
        self.probe(r'''
import inspect
calls = []
def initialize_dialog(self, *args, **kwargs):
    self.constructor = (args, kwargs)
sys.modules['xbmcgui'].WindowXMLDialog.__init__ = initialize_dialog
for name in ('BackendSettings', 'LoadingPreview'):
    instance = getattr(module, name)('Example.xml', '/addon', 'Default', '1080i', marker=True)
    original = getattr(sys.modules['backend_ui'], name)
    assert type(instance) is original, 'Dialog factory replaced the native subclass'
    assert instance.constructor == (('Example.xml', '/addon', 'Default', '1080i'), {'marker': True})

specs = [
    ('wait_for_helper', 'playback_runtime', ('owner',), {}),
    ('choose_icon', 'icon_picker', ('home',), {'pack': 'silver'}),
    ('choose_genre', 'genre_picker', ('Movies', ['page'], 'action'), {}),
    ('load_related', 'related_titles', ('path', 'provider', 'movie', '123'), {'valid': 'guard'}),
    ('cached_video_metadata', 'preview_language', ('profile', ('movie', '123')), {}),
    ('cached_title_aliases', 'preview_language', ('profile', ('tv', '123')), {}),
]
for name, owner_name, args, kwargs in specs:
    owner = importlib.import_module(owner_name)
    original = getattr(owner, name)
    wrapper = getattr(module, name)
    expected_parameters = inspect.signature(original).parameters
    actual_parameters = inspect.signature(wrapper).parameters
    assert list(actual_parameters) == list(expected_parameters), name
    for key, expected in expected_parameters.items():
        actual = actual_parameters[key]
        assert actual.kind == expected.kind, (name, key)
        if key == 'valid':
            assert actual.default() is True and expected.default() is True
        else:
            assert actual.default == expected.default, (name, key)
    expected_bound = inspect.signature(original).bind(*args, **kwargs)
    expected_bound.apply_defaults()
    marker = object()
    def capture(*received, **options):
        actual = inspect.signature(original).bind(*received, **options)
        actual.apply_defaults()
        assert actual.arguments == expected_bound.arguments, name
        calls.append(name)
        return marker
    setattr(owner, name, capture)
    try:
        assert wrapper(*args, **kwargs) is marker, name
    finally:
        setattr(owner, name, original)
assert calls == [spec[0] for spec in specs]
# Call actual safe, empty-result paths after first-use import.
assert module.load_related(lambda *a: 'unused', lambda *a: [], 'unsupported', '123') == ('', [])
assert module.cached_video_metadata('/missing', None) == {}
assert module.cached_title_aliases('/missing', None) == []
''')


if __name__ == '__main__':
    unittest.main()
