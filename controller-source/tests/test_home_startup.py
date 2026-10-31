"""Exercise the production startup contract with an in-memory Kodi boundary."""
import ast
import importlib.util
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).parents[1] / 'addon'
sys.path.insert(0, str(ROOT))
HOME = 'BlackLanturn.Startup.Home'
OWNER = 'BlackLanturn.Startup.Owner'


class Properties:
    def __init__(self, **values):
        self.values = values

    def getProperty(self, key):
        return self.values.get(key, '')

    def setProperty(self, key, value):
        self.values[key] = value

    def clearProperty(self, key):
        self.values.pop(key, None)


def method(filename, name, namespace, class_name=None):
    nodes = ast.parse((ROOT / filename).read_text()).body
    if class_name:
        nodes = next(n for n in nodes if isinstance(n, ast.ClassDef) and n.name == class_name).body
    node = next(n for n in nodes if isinstance(n, ast.FunctionDef) and n.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(ROOT / filename), 'exec'), namespace)
    return namespace[name]


class EntryContractTests(unittest.TestCase):
    def run_entry(self, home, run, fail_import=False, dialog=None):
        nodes = ast.parse((ROOT / 'default.py').read_text()).body
        start = next(i for i, n in enumerate(nodes) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'home' for t in n.targets))
        namespace = dict(xbmcgui=SimpleNamespace(Window=lambda _: home, Dialog=lambda: SimpleNamespace(ok=dialog or (lambda *a: None))),
                         xbmc=SimpleNamespace(getSkinDir=lambda: 'skin.blacklanturn.preview', Monitor=lambda: SimpleNamespace(abortRequested=lambda: False), getCondVisibility=lambda _: False),
                         xbmcaddon=SimpleNamespace(Addon=lambda *a: None), xbmcvfs=SimpleNamespace(translatePath=lambda _: '/profile'),
                         SkinStartupGate=lambda _: SimpleNamespace(tick=lambda *a: 'ready'), time=__import__('time'),
                         sys=SimpleNamespace(argv=[], exc_info=sys.exc_info), PROFILE='/profile', ROOT=ROOT, STORE=Path('/profile'),
                         record=lambda *a, **k: None, run_live_review=run)
        recovery = SimpleNamespace(recover_installer=lambda *a: False, RecoveryError=RuntimeError)
        live = None if fail_import else SimpleNamespace(LiveReview=object)
        with patch.dict(sys.modules, installer_recovery=recovery, live_review=live):
            exec(compile(ast.Module(body=nodes[start:], type_ignores=[]), str(ROOT / 'default.py'), 'exec'), namespace)

    def test_entry_publishes_pending_before_window_and_releases_on_error(self):
        home = Properties()
        seen = []
        def run(startup=None):
            seen.append((home.getProperty(HOME), home.getProperty(OWNER), startup))
            raise RuntimeError('window creation failed')
        self.run_entry(home, run)
        self.assertEqual(seen[0][0], 'pending')
        self.assertTrue(seen[0][1])
        self.assertIsNotNone(seen[0][2])
        self.assertEqual(home.getProperty(HOME), 'released')

    def test_preload_failure_releases_owned_contract(self):
        home = Properties()
        self.run_entry(home, lambda *a: self.fail('window must not open'), fail_import=True)
        self.assertEqual(home.getProperty(HOME), 'released')

    def test_failure_releases_before_blocking_error_dialog(self):
        home = Properties()
        seen = []
        self.run_entry(home, lambda *a: None, fail_import=True,
                       dialog=lambda *a: seen.append(home.getProperty(HOME)))
        self.assertEqual(seen, ['released'])

    def test_duplicate_invocation_does_not_release_existing_owner(self):
        home = Properties(**{'BlackLanturn.Preview.Running': '1', HOME: 'pending', OWNER: 'existing'})
        self.run_entry(home, lambda *a: self.fail('duplicate window'))
        self.assertEqual(home.getProperty(HOME), 'pending')
        self.assertEqual(home.getProperty(OWNER), 'existing')

    def test_old_entry_finally_cannot_release_replacement_owner(self):
        home = Properties()
        def run(startup=None):
            home.setProperty(OWNER, 'replacement')
            home.setProperty(HOME, 'pending')
        self.run_entry(home, run)
        self.assertEqual(home.getProperty(HOME), 'pending')
        self.assertEqual(home.getProperty(OWNER), 'replacement')

    def test_window_recreation_preserves_same_session_contract(self):
        opened = []
        class Window:
            def __init__(self, *args):
                opened.append(self)
                self.core_settings_request = {'target': 'settings', 'category': 0, 'row': 0} if len(opened) == 1 else None
            def doModal(self):
                pass
        namespace = dict(ROOT=ROOT, record=lambda *a, **k: None, time=__import__('time'),
                         xbmc=SimpleNamespace(Monitor=lambda: SimpleNamespace(abortRequested=lambda: False),
                                              getSkinDir=lambda: 'skin.blacklanturn.preview', executebuiltin=lambda *a: None),
                         xbmcgui=SimpleNamespace(getCurrentWindowId=lambda: 10000))
        run = method('default.py', 'run_live_review', namespace)
        startup = object()
        with patch.dict(sys.modules, live_review=SimpleNamespace(LiveReview=Window),
                        backend_core=SimpleNamespace(CoreSettingsReturn=lambda _: SimpleNamespace(tick=lambda *a: 'returned'))):
            run(startup)
        self.assertEqual(len(opened), 2)
        self.assertTrue(all(w.startup_home is startup for w in opened))


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'home_startup.py').exists(), 'Home readiness contract has not been implemented')
        spec = importlib.util.spec_from_file_location('home_startup_under_test', ROOT / 'home_startup.py')
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.now = 0.0
        self.home = Properties()
        self.startup = self.module.HomeStartup(self.home, clock=lambda: self.now)
        self.window = Properties(loading='false', hero='hero.jpg', startupOwner=self.startup.owner)
        self.window.alive = True
        self.window.window_lifetime = object()
        self.lifetime = self.window.window_lifetime
        self.window.generation = 1
        self.window.mode = 'home'
        self.window.section = 'Home'
        self.window.window_ready = [True, True]
        self.window.rows = [[{'label': 'One', 'art': {'landscape': 'one.jpg'}}], [{'label': 'Two', 'art': {'landscape': 'two.jpg'}}]]
        self.window.loading_paths = {'refresh': True}
        self.window.row_window_busy = True
        self.window.snapshot_rows = [True, True]
        self.labels = {'Window.Property(startupOwner)': self.startup.owner, 'Window.Property(loading)': 'false',
                       'Window.Property(hero)': 'hero.jpg', 'Container(900).NumItems': '1', 'Container(901).NumItems': '1',
                       'Container(900).ListItemAbsolute(0).Art(landscape)': 'one.jpg',
                       'Container(901).ListItemAbsolute(0).Art(landscape)': 'two.jpg'}
        self.booleans = {'Control.IsVisible(900)': True, 'Control.IsVisible(901)': True, 'Window.IsVisible(yesnodialog)': False}
        self.calls = []

    def rpc(self, name, params):
        self.calls.append((name, params))
        if name == 'XBMC.GetInfoLabels':
            return {'result': {key: self.labels.get(key, '') for key in params['labels']}}
        if name == 'XBMC.GetInfoBooleans':
            return {'result': {key: self.booleans.get(key, False) for key in params['booleans']}}
        self.fail('Readiness must not perform other I/O: ' + name)

    def observe(self):
        self.startup.observe(self.window, self.lifetime, self.rpc,
                             lambda item: {'image': item.get('art', {}).get('landscape', ''), 'kind': 'landscape'})

    def advance(self, when):
        self.now = when
        self.observe()

    def test_snapshot_rows_release_despite_pending_refresh_only_after_stable_native_binding(self):
        self.labels['Container(901).NumItems'] = '0'
        self.observe()
        self.advance(.4)
        self.assertEqual(self.home.getProperty(HOME), 'pending')
        self.labels['Container(901).NumItems'] = '1'
        self.advance(.8)
        self.assertEqual(self.home.getProperty(HOME), 'pending')
        self.advance(1.2)
        self.assertEqual(self.home.getProperty(HOME), 'ready')
        before = len(self.calls)
        self.advance(2)
        self.assertEqual(len(self.calls), before, 'No readiness work after publication')

    def test_loading_clear_before_second_row_binding_performs_no_native_reads(self):
        self.window.window_ready[1] = False
        self.observe()
        self.advance(1)
        self.assertEqual(self.home.getProperty(HOME), 'pending')
        self.assertEqual(self.calls, [])

    def test_artwork_and_visibility_must_be_bound_before_readiness(self):
        self.labels['Container(900).ListItemAbsolute(0).Art(landscape)'] = ''
        self.observe()
        self.advance(.4)
        self.assertEqual(self.home.getProperty(HOME), 'pending')
        self.labels['Container(900).ListItemAbsolute(0).Art(landscape)'] = 'one.jpg'
        self.booleans['Control.IsVisible(900)'] = False
        self.advance(.8)
        self.advance(1.2)
        self.assertEqual(self.home.getProperty(HOME), 'pending')
        self.booleans['Control.IsVisible(900)'] = True
        self.advance(1.6)
        self.advance(2)
        self.assertEqual(self.home.getProperty(HOME), 'ready')

    def test_text_fallback_and_single_populated_row_are_usable(self):
        self.window.rows = [[{'label': 'No artwork'}], []]
        self.labels['Container(901).NumItems'] = '0'
        self.booleans['Control.IsVisible(901)'] = False
        self.observe()
        self.advance(.4)
        self.assertEqual(self.home.getProperty(HOME), 'ready')

    def test_empty_rows_release_without_claiming_ready(self):
        self.window.rows = [[], []]
        self.observe()
        self.assertEqual(self.home.getProperty(HOME), 'released')

    def test_stale_lifetime_cannot_publish(self):
        self.observe()
        self.window.window_lifetime = object()
        self.advance(.4)
        self.assertEqual(self.home.getProperty(HOME), 'pending')

    def test_generation_change_during_native_read_cannot_publish(self):
        self.observe()
        original = self.rpc
        def mutate(name, params):
            value = original(name, params)
            self.window.generation += 1
            return value
        self.rpc = mutate
        self.advance(.4)
        self.assertEqual(self.home.getProperty(HOME), 'pending')

    def test_row_replacement_during_native_read_cannot_publish_old_binding(self):
        self.observe()
        original = self.rpc
        def mutate(name, params):
            value = original(name, params)
            self.window.rows[0] = [{'label': 'Replacement', 'art': {'landscape': 'new.jpg'}}]
            return value
        self.rpc = mutate
        self.advance(.4)
        self.assertEqual(self.home.getProperty(HOME), 'pending')

    def test_setup_failure_releases_but_stale_setup_failure_does_not(self):
        self.window.startup_home = self.startup
        self.window.finish_loading = lambda reason: self.window.setProperty('loading', 'false')
        def fail():
            raise RuntimeError('dependency failed')
        start = method('live_review.py', 'start', {'initialize_addons': fail, 'event': lambda *a, **k: None}, 'LiveReview')
        self.window.window_lifetime = object()
        start(self.window, self.lifetime)
        self.assertEqual(self.home.getProperty(HOME), 'pending')
        start(self.window, self.window.window_lifetime)
        self.assertEqual(self.home.getProperty(HOME), 'released')

    def test_monitor_observes_before_loading_paths_skip(self):
        self.window.startup_home = self.startup
        self.window.owner_skin = 'skin.blacklanturn.preview'
        self.window.update_work_paused = lambda: False
        self.window.settings_open = self.window.actions_open = False
        self.window.refresh_youtube_connection = lambda: None
        self.window.apply_nav_width = lambda: None
        clock = SimpleNamespace(monotonic=lambda: self.now, sleep=lambda _: setattr(self.window, 'alive', False))
        monitor = method('live_review.py', 'monitor',
                         {'time': clock, 'xbmc': SimpleNamespace(getSkinDir=lambda: 'skin.blacklanturn.preview',
                          Monitor=lambda: SimpleNamespace(abortRequested=lambda: False)), 'rpc': self.rpc,
                          'card_artwork': lambda item: {'image': item.get('art', {}).get('landscape', ''), 'kind': 'landscape'}}, 'LiveReview')
        monitor(self.window, self.lifetime)
        self.now = .4
        self.window.alive = True
        monitor(self.window, self.lifetime)
        self.assertEqual(self.home.getProperty(HOME), 'ready')

    def test_replacement_owner_survives_old_release_and_observation(self):
        self.observe()
        self.home.setProperty(OWNER, 'replacement')
        self.advance(.4)
        self.startup.release()
        self.assertEqual(self.home.getProperty(HOME), 'pending')
        self.assertEqual(self.home.getProperty(OWNER), 'replacement')

    def test_polling_is_throttled_and_has_hard_failure_deadline(self):
        self.labels['Container(900).NumItems'] = '0'
        self.observe()
        count = len(self.calls)
        self.advance(.01)
        self.assertEqual(len(self.calls), count)
        self.advance(16)
        self.assertEqual(self.home.getProperty(HOME), 'released')
        self.assertEqual(len(self.calls), count)

    def test_gui_failure_is_bounded_and_does_not_escape_into_controller(self):
        self.rpc = lambda *a: (_ for _ in ()).throw(RuntimeError('GUI unavailable'))
        self.observe()
        self.assertEqual(self.home.getProperty(HOME), 'pending')
        self.advance(16)
        self.assertEqual(self.home.getProperty(HOME), 'released')


if __name__ == '__main__':
    unittest.main()
