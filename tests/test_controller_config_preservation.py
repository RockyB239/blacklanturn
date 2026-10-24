"""Keep the exact controller config through Standard cleanup and pending retries."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import zipfile

import test_build_preferences as fixtures
import test_preferences_install_flow as install_flow

CONTROLLER = 'script.blacklanturn.preview'
ROWS = 'addon_data/script.blacklanturn.preview/rows.json'
ORIGINAL = b'{\n  "RatingSources": ["imdb", "popcorn"], "PreviewMode": "manual",\n  "Saved": [{"title": "Custom", "id": 42}], "custom": {"visible": true, "scale": 0.75}, "name": "caf\xc3\xa9"\n}\n'
DEFAULT = b'{"RatingSources":["rottentomatoes","metacritic","imdb","popcorn"],"PreviewMode":"auto"}'


class ControllerConfigPreservation(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.BuildPreferences()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.home = self.fixture.home
        self.module = self.fixture.m
        self.ids = fixtures.IDS + [CONTROLLER]
        self.path = self.home / 'userdata' / ROWS

    def write(self, raw):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_bytes(raw)

    def accounts(self):
        result = self.fixture.accounts()
        result['addon_ids'] = self.ids
        return result

    def snapshot(self, clean=False):
        return self.module.prepare(self.home, self.accounts(), self.ids, auth_only=clean)

    def test_standard_restores_exact_bytes_including_unknown_saved_rows_and_formatting(self):
        self.write(ORIGINAL)
        accounts = self.snapshot()
        self.write(DEFAULT)
        self.module.restore(self.home, accounts, self.ids)
        self.assertEqual(self.path.read_bytes(), ORIGINAL)

    def test_account_only_clean_does_not_restore_controller_preferences(self):
        self.write(ORIGINAL)
        accounts = self.snapshot(clean=True)
        self.write(DEFAULT)
        self.module.restore(self.home, accounts, self.ids)
        self.assertEqual(self.path.read_bytes(), DEFAULT)
        self.assertIsNone(accounts['build_preferences'].get('controller'))

    def test_missing_original_keeps_new_build_default(self):
        accounts = self.snapshot()
        self.write(DEFAULT)
        self.module.restore(self.home, accounts, self.ids)
        self.assertEqual(self.path.read_bytes(), DEFAULT)

    def test_snapshot_survives_pending_json_roundtrip_and_retry_without_resnapshot(self):
        self.write(ORIGINAL)
        first = self.snapshot()
        pending = json.loads(json.dumps(first))
        self.write(b'{broken partial extraction')
        again = self.module.prepare(self.home, pending, self.ids, auth_only=False)
        self.module.restore(self.home, again, self.ids)
        self.assertEqual(self.path.read_bytes(), ORIGINAL)
        self.assertEqual(first, again)

    def test_controller_not_in_payload_is_neither_captured_nor_restored(self):
        self.write(ORIGINAL)
        accounts = self.module.prepare(self.home, self.accounts(), fixtures.IDS, auth_only=False)
        self.assertNotIn('Custom', json.dumps(accounts))
        self.write(DEFAULT)
        self.module.restore(self.home, accounts, fixtures.IDS)
        self.assertEqual(self.path.read_bytes(), DEFAULT)

    def test_bad_original_json_stops_capture_before_cleanup(self):
        for raw in (b'[]', b'null', b'{broken', b'{"value":NaN}', b'{"value":Infinity}',
                    b'{"value":1e999}', b'{"nested":{"x":1,"x":2}}', b'\xff'):
            with self.subTest(raw=raw):
                self.write(raw)
                with self.assertRaises(self.module.PreferenceError): self.snapshot()
                self.assertEqual(self.path.read_bytes(), raw)

    def test_oversized_original_stops_before_cleanup(self):
        self.write(b'{"value":"' + b'x' * (4 * 1024 * 1024) + b'"}')
        with self.assertRaises(self.module.PreferenceError): self.snapshot()

    def test_symlink_file_or_parent_is_rejected_at_capture(self):
        victim = self.home / 'victim.json'
        victim.write_bytes(ORIGINAL)
        self.path.parent.mkdir(parents=True)
        self.path.symlink_to(victim)
        with self.assertRaises(self.module.PreferenceError): self.snapshot()
        self.path.unlink(); self.path.parent.rmdir()
        self.path.parent.symlink_to(self.home, target_is_directory=True)
        with self.assertRaises(self.module.PreferenceError): self.snapshot()
        self.assertEqual(victim.read_bytes(), ORIGINAL)

    def test_malformed_pending_controller_is_rejected_before_any_restore_write(self):
        self.write(ORIGINAL)
        original = self.snapshot()
        for raw in ('[]', '{"value":NaN}', '{"value":1e999}', {'../escape': '{}'}, 7, 'x' * (4 * 1024 * 1024 + 1)):
            with self.subTest(raw_type=type(raw).__name__):
                broken = copy.deepcopy(original)
                broken['build_preferences']['controller'] = raw
                with self.assertRaises(self.module.PreferenceError):
                    self.module.prepare(self.home, broken, self.ids, auth_only=False)
                with self.assertRaises(self.module.PreferenceError):
                    self.module.restore(self.home, broken, self.ids)
                self.assertFalse((self.home / 'userdata/guisettings.xml').exists())
                self.assertEqual(self.path.read_bytes(), ORIGINAL)

    def test_pending_controller_cannot_bypass_clean_or_packaged_addon_guards(self):
        self.write(ORIGINAL)
        original = self.snapshot()
        clean = copy.deepcopy(original)
        clean['build_preferences']['auth_only'] = True
        with self.assertRaises(self.module.PreferenceError):
            self.module.prepare(self.home, clean, self.ids, auth_only=True)
        with self.assertRaises(self.module.PreferenceError):
            self.module.restore(self.home, original, fixtures.IDS)

    def test_new_pending_missing_controller_field_is_not_mistaken_for_originally_absent(self):
        snapshot = self.snapshot()
        snapshot['build_preferences']['schema'] = 2
        snapshot['build_preferences'].pop('controller', None)
        with self.assertRaises(self.module.PreferenceError):
            self.module.prepare(self.home, snapshot, self.ids, auth_only=False)

    def test_old_standard_pending_with_controller_fails_closed_instead_of_recapturing(self):
        self.write(DEFAULT)
        accounts = self.accounts()
        accounts['build_preferences'] = {'schema': 1, 'auth_only': False, 'values': {}}
        with self.assertRaisesRegex(self.module.PreferenceError, 'older|recovery'):
            self.module.prepare(self.home, accounts, self.ids, auth_only=False)
        self.assertEqual(self.path.read_bytes(), DEFAULT)

    def test_old_clean_pending_and_old_noncontroller_build_keep_previous_safe_semantics(self):
        for clean, ids in ((True, self.ids), (False, fixtures.IDS)):
            with self.subTest(clean=clean):
                accounts = self.accounts()
                accounts['build_preferences'] = {'schema': 1, 'auth_only': clean, 'values': {}}
                again = self.module.prepare(self.home, accounts, ids, auth_only=clean)
                self.assertEqual(again, accounts)
                self.module.restore(self.home, again, ids)

    def test_restore_rejects_controller_symlink_before_writing_other_preferences(self):
        self.write(ORIGINAL)
        accounts = self.snapshot()
        self.path.unlink()
        victim = self.home / 'victim.json'; victim.write_bytes(DEFAULT)
        self.path.symlink_to(victim)
        with self.assertRaises(self.module.PreferenceError): self.module.restore(self.home, accounts, self.ids)
        self.assertEqual(victim.read_bytes(), DEFAULT)
        self.assertFalse((self.home / 'userdata/guisettings.xml').exists())

    def test_controller_restore_uses_atomic_replacement_and_keeps_pending_after_failure(self):
        self.write(ORIGINAL)
        accounts = self.snapshot()
        self.write(DEFAULT)
        replace = Path.replace
        def fail_controller_replace(source, target):
            if Path(target) == self.path: raise OSError('Simulated interruption before atomic rename')
            return replace(source, target)
        with patch.object(Path, 'replace', fail_controller_replace), self.assertRaises(self.module.PreferenceError):
            self.module.restore(self.home, accounts, self.ids)
        self.assertEqual(self.path.read_bytes(), DEFAULT)
        self.assertEqual(list(self.path.parent.glob('*.pending')), [])
        self.module.restore(self.home, accounts, self.ids)
        self.assertEqual(self.path.read_bytes(), ORIGINAL)


class ControllerConfigInstallFlow(unittest.TestCase):
    def run_install(self, clean=False, keep_gui=False, invalid_pending=False):
        fixture = install_flow.PreferenceInstallFlow()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        packaged = fixture.packaged
        def package_with_controller(change=None):
            def add_controller(data):
                data['addons/' + CONTROLLER + '/addon.xml'] = b'<addon id="script.blacklanturn.preview" version="0.1.83"/>'
                data['userdata/' + ROWS] = DEFAULT
                if change: change(data)
            archive = packaged(add_controller)
            home = fixture.root / 'profile'
            rows = home / 'userdata' / ROWS
            rows.parent.mkdir(parents=True, exist_ok=True)
            rows.write_bytes(ORIGINAL)
            if invalid_pending:
                with zipfile.ZipFile(archive) as bundle:
                    ids = sorted({name.split('/')[1] for name in bundle.namelist()
                                  if name.startswith('addons/') and name.endswith('/addon.xml') and len(name.split('/')) == 3})
                pending = home / 'userdata/addon_data/plugin.program.blacklanturninstaller/authorizations.pending.json'
                pending.parent.mkdir(parents=True, exist_ok=True)
                pending.write_text(json.dumps({'schema': 1, 'addon_ids': ids, 'categories': ['login', 'trakt'],
                    'settings': {}, 'files': {}, 'build_preferences': {'schema': 2, 'auth_only': False,
                    'values': {}, 'controller': '{"invalid": NaN}'}}))
                (home / 'userdata/pre-wipe-marker.txt').write_text('preserve')
            return archive
        fixture.packaged = package_with_controller
        return fixture.run_install(auth_only=clean, gui_keep=keep_gui)

    def test_real_wizard_standard_and_keep_gui_retain_exact_controller_and_account(self):
        for keep_gui in (False, True):
            with self.subTest(keep_gui=keep_gui):
                home = self.run_install(keep_gui=keep_gui)
                self.assertEqual((home / 'userdata' / ROWS).read_bytes(), ORIGINAL)
                backup = home / 'userdata/addon_data/plugin.program.blacklanturninstaller/authorizations.json'
                snapshot = json.loads(backup.read_text())['build_preferences']
                self.assertEqual(snapshot['controller'].encode('utf-8'), ORIGINAL)
                self.assertEqual(snapshot['schema'], 3)
                self.assertIn('update_notes', snapshot)
                self.assertFalse(backup.with_name('authorizations.pending.json').exists())
                helper = home / 'userdata/addon_data/plugin.video.themoviedb.helper/settings.xml'
                self.assertEqual({node.get('id'): node.text for node in fixtures.E.parse(helper).getroot()}['trakt_token'], 'private-token')

    def test_real_wizard_account_only_clean_uses_new_controller_default(self):
        home = self.run_install(clean=True)
        self.assertEqual((home / 'userdata' / ROWS).read_bytes(), DEFAULT)
        backup = home / 'userdata/addon_data/plugin.program.blacklanturninstaller/authorizations.json'
        self.assertIsNone(json.loads(backup.read_text())['build_preferences']['controller'])

    def test_real_wizard_bad_pending_controller_stops_before_cleanup(self):
        home = self.run_install(invalid_pending=True)
        self.assertEqual((home / 'userdata/pre-wipe-marker.txt').read_text(), 'preserve')
        self.assertEqual((home / 'userdata' / ROWS).read_bytes(), ORIGINAL)
        self.assertTrue((home / 'userdata/addon_data/plugin.program.blacklanturninstaller/authorizations.pending.json').exists())


if __name__ == '__main__': unittest.main()
