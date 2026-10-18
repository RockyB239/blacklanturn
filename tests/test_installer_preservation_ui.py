"""Exercise real installer routes/dialogs without a Kodi profile or network."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

import test_compatibility as compatibility

LIB = compatibility.ROOT


class Control:
    def __init__(self, label=''):
        self.label = label
        self.selected = False
        self.items = []
        self.position = 0
    def setSelected(self, value): self.selected = value
    def isSelected(self): return self.selected
    def setLabel(self, value): self.label = value
    def setText(self, value): self.label = value
    def setProperty(self, *args): pass
    def setArt(self, *args): pass
    def reset(self): self.items = []
    def addItem(self, item): self.items.append(item)
    def selectItem(self, index): self.position = index
    def getSelectedPosition(self): return self.position


class FakeWindow:
    callback = None
    last = None
    def __new__(cls, *args, **kwargs):
        obj = super().__new__(cls)
        obj.controls = {}
        obj.properties = {}
        obj.closed = False
        FakeWindow.last = obj
        return obj
    def __init__(self, *args, **kwargs): pass
    def getControl(self, number): return self.controls.setdefault(number, Control())
    def setFocus(self, control): pass
    def setFocusId(self, number): pass
    def setProperty(self, key, value): self.properties[key] = value
    def close(self): self.closed = True
    def doModal(self):
        self.onInit()
        if FakeWindow.callback: FakeWindow.callback(self)


class InstallerPreservationUI(unittest.TestCase):
    def setUp(self):
        self.fixture = compatibility.CompatibilityTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.kodi = compatibility.Kodi()
        self.kodi.LOGDEBUG = 0
        self.config, self.modules = self.fixture.install_environment(self.kodi)
        self.values = {}
        self.writes = []
        self.config.get_setting = lambda key: self.values.get(key, 'false')
        def write(key, value):
            self.writes.append((key, value)); self.values[key] = value
        self.config.set_setting = write
        self.config.clear_setting = lambda key: self.writes.append(('clear', key))
        for key in ('ICONSAVE', 'ICONTRAKT', 'ICONDEBRID', 'ICONLOGIN', 'THEME1',
                    'THEME2', 'THEME3', 'THEME4', 'ICONBUILDS', 'ADDON_ICON',
                    'ADDON_FANART', 'ADDON_VERSION', 'BUILDFILE', 'BUILDNAME', 'BUILDVERSION'):
            setattr(self.config, key, '')
        self.config.ADDONFILE = 'http://'
        self.rows = []
        def add(label, params=None, **kw):
            self.rows.append(dict(label=label, params=params or {}, description=kw.get('description', '')))
        self.directory = types.SimpleNamespace(add_file=add, add_dir=add, add_separator=lambda *a, **kw: None)
        self.modules['resources.libs.common.directory'] = self.directory
        self.modules['xbmcgui'].WindowXMLDialog = FakeWindow
        self.modules['xbmcgui'].ListItem = Control
        self.modules['xbmcaddon'] = types.ModuleType('xbmcaddon')
        self.modules['xbmcvfs'] = types.ModuleType('xbmcvfs')
        self.modules['xbmcplugin'] = types.ModuleType('xbmcplugin')
        self.modules['resources.libs.common.tools'].ensure_folders = lambda path=None: Path(path).mkdir(parents=True, exist_ok=True) if path else None
        # Actual packages keep relative sibling imports available to the real modules.
        self.modules['resources.libs.gui'].__path__ = [str(LIB / 'gui')]
        self.modules['resources.libs.common'].__path__ = [str(LIB / 'common')]
        self.addCleanup(setattr, FakeWindow, 'callback', None)

    def load(self, relative):
        name = 'resources.libs.' + relative.replace('/', '.').removesuffix('.py')
        spec = importlib.util.spec_from_file_location(name, LIB / relative)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_gui_keep_toggle_targets_setting_consumed_by_install(self):
        with patch.dict(sys.modules, self.modules):
            self.load('gui/menu.py').save_menu()
        row = next(r for r in self.rows if 'guisettings.xml' in r['label'])
        self.assertEqual(row['params'], {'mode': 'togglesetting', 'name': 'keepguisettings'})
        with patch.dict(sys.modules, self.modules):
            from urllib.parse import urlencode
            self.load('common/router.py').Router().dispatch(1, urlencode(row['params']))
        self.assertEqual(self.values['keepguisettings'], 'true')

    def test_first_run_super_favourites_does_not_toggle_repositories(self):
        def click(window):
            window.getControl(308).setSelected(True)
            window.getControl(309).setSelected(False)
            window.onClick(201)
        FakeWindow.callback = click
        with patch.dict(sys.modules, self.modules):
            self.load('gui/window.py').show_save_data_settings()
        self.assertEqual(self.values['keepsuper'], 'true')
        self.assertEqual(self.values['keeprepos'], 'false')

    def test_first_run_displays_existing_repository_choice_in_correct_control(self):
        self.values['keeprepos'] = 'true'
        with patch.dict(sys.modules, self.modules):
            self.load('gui/window.py').show_save_data_settings()
        self.assertTrue(FakeWindow.last.getControl(309).isSelected())
        self.assertFalse(FakeWindow.last.getControl(308).isSelected())

    def test_first_run_shows_saved_reset_consequences(self):
        self.values['authonlyclean'] = 'true'
        with patch.dict(sys.modules, self.modules):
            self.load('gui/window.py').show_save_data_settings()
        text = FakeWindow.last.getControl(102).label
        self.assertIn('Account-only reset', text)
        self.assertIn('Save Data', text)

    def test_back_from_first_run_does_not_change_settings_or_mark_it_complete(self):
        FakeWindow.callback = lambda window: window.onAction(types.SimpleNamespace(getId=lambda: 92))
        with patch.dict(sys.modules, self.modules):
            self.load('gui/window.py').show_save_data_settings()
        self.assertEqual(self.writes, [])

    def test_save_data_exposes_persisted_account_only_mode_without_changing_it(self):
        self.values['authonlyclean'] = 'true'
        with patch.dict(sys.modules, self.modules):
            self.load('gui/menu.py').save_menu()
        row = next((r for r in self.rows if r['params'].get('name') == 'authonlyclean'), None)
        self.assertIsNotNone(row, 'Saved account-only reset cannot be changed from Save Data')
        self.assertIn('Account-only reset', row['label'])
        self.assertIn('reset', row['description'].lower())
        self.assertTrue(any('standard' in r['label'].lower() and not r['params'] for r in self.rows))
        self.assertEqual(self.writes, [])
        self.assertEqual(self.values['authonlyclean'], 'true')

    def test_build_action_discloses_saved_account_only_mode(self):
        self.values['authonlyclean'] = 'true'
        self.config.KODIV = 21.3
        catalog = ('name="Fixture" version="1.0" url="https://example.invalid/build.zip" '
                   'gui="http://" kodi="21.3" theme="http://" icon="icon" fanart="fanart" '
                   'preview="http://" adult="no" info="http://" description="Fixture build"')
        self.modules['resources.libs.common.tools'].open_url = lambda url, **kw: types.SimpleNamespace(text=catalog) if url == self.config.BUILDFILE else False
        self.modules['resources.libs.common.tools'].clean_text = lambda text: text
        with patch.dict(sys.modules, self.modules):
            self.load('gui/build_menu.py').BuildMenu().view_build('Fixture')
        row = next(r for r in self.rows if r['params'].get('action') == 'build')
        self.assertIn('Account-only reset', row['label'])
        self.assertIn('reset', row['description'].lower())

    def confirm_cancel(self, auth_only, over=False, kodi='21.3'):
        self.values['authonlyclean'] = 'true' if auth_only else 'false'
        self.config.KEEPTRAKT = 'true'
        self.config.KEEPGUISETTINGS = 'true'
        self.config.KEEPSOURCES = 'false'
        messages = []
        self.confirmation_bodies = []
        self.confirmation_titles = []
        def decline(*args, **kwargs):
            self.confirmation_titles.append(args[0])
            self.confirmation_bodies.append(args[1])
            messages.append(' '.join(str(arg) for arg in args)); return False
        self.modules['xbmcgui'].Dialog = lambda: types.SimpleNamespace(yesno=decline)
        self.modules['resources.libs.check'].check_build = lambda name, key: {'kodi': kodi, 'version': '1.0', 'url': 'unused'}[key]
        self.downloads = []
        def stop_download(*args):
            self.downloads.append(args)
            return False
        self.modules['resources.libs.downloader'].Downloader = lambda: types.SimpleNamespace(download=stop_download)
        with patch.dict(sys.modules, self.modules):
            self.load('wizard.py').Wizard().build('Fixture', over=over)
        return messages

    def test_final_confirmation_reviews_standard_choices_before_any_mutation(self):
        messages = self.confirm_cancel(False)
        self.assertIn('Standard', messages[0])
        self.assertIn('Trakt', messages[0])
        self.assertIn('guisettings.xml', messages[0])
        self.assertIn('Sources: OFF', messages[0])
        self.assertEqual(self.writes, [])
        self.assertEqual(list(Path(self.config.MYBUILDS).iterdir()), [])
        self.assertEqual(self.kodi.commands, [])

    def test_account_only_confirmation_warns_of_reset_and_ignored_keep_choices(self):
        messages = self.confirm_cancel(True)
        self.assertIn('Account-only reset', messages[0])
        self.assertIn('reset', messages[0].lower())
        self.assertIn('Trakt: ON', messages[0])
        self.assertIn('ignored', messages[0].lower())
        self.assertEqual(self.writes, [])
        self.assertEqual(self.values['authonlyclean'], 'true')
        self.assertEqual(self.config.KEEPGUISETTINGS, 'true')

    def test_reset_consequence_and_accounts_fit_first_three_visible_confirmation_lines(self):
        self.confirm_cancel(True)
        lines = self.confirmation_bodies[0].splitlines()
        self.assertTrue(lines[0].startswith('Mode: Account-only reset'))
        visible = ' '.join(lines[:3]).lower()
        for required in ('reset settings', 'playback', 'ignored', 'trakt: on', 'debrid: off', 'login: off'):
            self.assertIn(required, visible)
        self.assertTrue(all(len(line) <= 60 for line in lines[:3]))
        self.assertIn('Fixture v1.0', self.confirmation_titles[0])

    def test_standard_mode_and_accounts_fit_first_three_visible_confirmation_lines(self):
        self.confirm_cancel(False)
        lines = self.confirmation_bodies[0].splitlines()
        self.assertTrue(lines[0].startswith('Mode: Standard'))
        visible = ' '.join(lines[:3]).lower()
        for required in ('preserve', 'preferences', 'trakt: on', 'debrid: off', 'login: off'):
            self.assertIn(required, visible)
        self.assertTrue(all(len(line) <= 60 for line in lines[:3]))

    def test_version_warning_does_not_push_reset_consequence_below_visible_lines(self):
        self.confirm_cancel(True, kodi='22')
        lines = self.confirmation_bodies[0].splitlines()
        self.assertTrue(lines[0].startswith('Mode: Account-only reset'))
        self.assertIn('reset settings', ' '.join(lines[:3]).lower())
        self.assertIn('WARNING', self.confirmation_titles[0])

    def test_over_update_still_requires_review_before_download(self):
        messages = self.confirm_cancel(True, over=True)
        self.assertTrue(messages, 'Update bypassed the preservation review')
        self.assertIn('Account-only reset', messages[0])
        self.assertEqual(self.writes, [])
        self.assertEqual(self.downloads, [])

    def test_version_warning_still_discloses_the_reset_mode(self):
        messages = self.confirm_cancel(True, kodi='22')
        self.assertIn('Account-only reset', messages[0])
        self.assertEqual(self.writes, [])

    def test_account_only_legacy_payload_stops_instead_of_silently_using_standard(self):
        self.values['authonlyclean'] = 'true'
        cleanup = []
        errors = []
        self.modules['resources.libs.install'].wipe = lambda **kw: cleanup.append(kw) or False
        self.modules['xbmcgui'].Dialog = lambda: types.SimpleNamespace(yesno=lambda *a, **kw: True, ok=lambda *args: errors.append(args))
        old = Path(self.config.HOME) / 'userdata' / 'existing-settings.txt'
        old.parent.mkdir(parents=True)
        old.write_text('preserve')
        with patch.dict(sys.modules, self.modules):
            self.load('wizard.py').Wizard().build('Fixture')
        self.assertEqual(cleanup, [], 'Reviewed reset mode silently fell back to Standard cleanup')
        self.assertTrue(errors)
        self.assertIn('Account-only reset', errors[0][1])
        self.assertEqual(old.read_text(), 'preserve')
        self.assertEqual(self.values['authonlyclean'], 'true')

    def test_unconfigured_addon_sidebar_is_absent_and_tools_route_remains_correct(self):
        with patch.dict(sys.modules, self.modules):
            nav = self.load('gui/navigation.py')
            model = self.load('gui/navigation_model.py')
            screen = nav.InstallerNavigation('unused', navigation=model.Navigation(), rows=[])
            screen.onInit()
            labels = [item.label for item in screen.getControl(100).items]
            self.assertNotIn('Addon Installer', labels)
            screen.getControl(100).position = labels.index('More tools')
            screen.onClick(100)
            self.assertEqual(screen.pending, ('switch', {'mode': 'tools'}, 'More tools'))

    def test_configured_addon_sidebar_keeps_existing_infrastructure(self):
        self.config.ADDONFILE = 'https://example.invalid/addons.json'
        with patch.dict(sys.modules, self.modules):
            nav = self.load('gui/navigation.py')
            model = self.load('gui/navigation_model.py')
            screen = nav.InstallerNavigation('unused', navigation=model.Navigation(), rows=[])
            screen.onInit()
        self.assertIn('Addon Installer', [item.label for item in screen.getControl(100).items])


if __name__ == '__main__': unittest.main()
