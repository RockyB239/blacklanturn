"""Synthetic gate inputs only; these fixtures are never native acceptance receipts."""
import copy
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch
import zipfile

from tools import verify_release
from test_compatibility import Kodi


DEVICE_CHECKS = (
    'source_exact', 'ordinary_restart', 'authorization_grants_preserved',
    'settings_preserved', 'youtube_history_preserved', 'youtube_details_supported_content',
    'youtube_details_movie_sections_hidden', 'youtube_details_back_retains_captions',
    'independent_preview_focus_verified', 'preview_policy_unchanged', 'help_current')


class Release112Acceptance(unittest.TestCase):
    def setUp(self):
        self.manifest = {'controller': '0.1.83', 'files': {'live_review.py': 'new-ui', 'HELP.txt': 'new-help'}}
        device = dict.fromkeys(DEVICE_CHECKS, True)
        self.receipt = {'controller': '0.1.83', 'files': copy.deepcopy(self.manifest['files']),
                        'passed': True, 'devices': {name: copy.deepcopy(device) for name in ('mac', 'fire', 'apple_tv')}}
        self.receipt['devices']['fire'].update(
            browsing_speed={'protocol': 'cached-native-first-usable-row-v1',
                            'before_controller': '0.1.82', 'after_controller': '0.1.83',
                            'sections': {name: {'before_seconds': [1.4, 1.5, 1.6],
                                                'after_seconds': [1.6, 1.7, 1.8]}
                                         for name in ('Home', 'Shows', 'Movies', 'YouTube', 'My Stuff')}},
            paused_stop={'actual_outgoing_writer_verified': True, 'helper_source_exact': True,
                         'stopped_while_paused': True, 'pause_seconds': 10,
                         'kodi_position_seconds': 720, 'duration_seconds': 6000,
                         'helper_stop_progress': 12, 'settled_trakt_progress': 12})

    def check(self, receipt=None, manifest=None):
        gate = getattr(verify_release, 'verify_release112_acceptance', None)
        self.assertTrue(callable(gate), 'Missing fresh release 1.1.12 native gate')
        gate(self.receipt if receipt is None else receipt, self.manifest if manifest is None else manifest)

    def test_complete_synthetic_receipt_passes(self):
        self.check()

    def test_entrypoint_rejects_missing_current_ui_receipt_before_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(verify_release, 'ROOT', Path(tmp)):
            with self.assertRaises(FileNotFoundError) as caught:
                verify_release.verify(Path(tmp)/'artifacts')
            self.assertEqual(Path(caught.exception.filename), Path(tmp)/'controller-source/usability-release112-verification.json')

    def test_entrypoint_does_not_reuse_historical_helper_receipt_for_current_source(self):
        real_root = verify_release.ROOT
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for relative in (
                'controller-source/manifest75.json', 'controller-source/manifest76.json',
                'controller-source/manifest81.json', 'controller-source/manifest82.json',
                'controller-source/youtube-native-verification.json',
                'controller-source/youtube-stall-mac-verification.json',
                'controller-source/youtube-stall-native-verification.json',
                'controller-source/youtube-release110-verification.json',
                'controller-source/youtube-release111-verification.json',
                'compatibility/helper-empty-cache/native-verification.json'):
                target = root/relative; target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((real_root/relative).read_bytes())
            (root/'controller-source/manifest83.json').write_text(json.dumps(self.manifest))
            (root/'controller-source/usability-release112-verification.json').write_text(json.dumps(self.receipt))
            # Isolate the Helper lookup from the separately tested native v2 gate.
            candidate = copy.deepcopy(self.receipt)
            candidate['devices']['fire']['browsing_speed']['protocol'] = 'cached-native-first-usable-row-v2'
            (root/'controller-source/usability-release112-verification.json').write_text(json.dumps(candidate))
            with patch.object(verify_release, 'ROOT', root), patch.object(verify_release, 'verify_fire_browsing_v2'), self.assertRaises(FileNotFoundError) as caught:
                verify_release.verify(root/'artifacts')
            self.assertEqual(Path(caught.exception.filename), root/'compatibility/helper-progress/native-verification.json')

    def test_old_or_changed_source_and_incomplete_device_coverage_fail_closed(self):
        for change in ('version', 'manifest', 'files', 'passed', 'missing_device', 'extra_device'):
            with self.subTest(change=change):
                r = copy.deepcopy(self.receipt); m = copy.deepcopy(self.manifest)
                if change == 'version': r['controller'] = '0.1.82'
                elif change == 'manifest': m['controller'] = '0.1.82'
                elif change == 'files': r['files']['live_review.py'] = 'stale'
                elif change == 'passed': r['passed'] = False
                elif change == 'missing_device': del r['devices']['apple_tv']
                else: r['devices']['other'] = {}
                with self.assertRaises(AssertionError): self.check(r, m)

    def test_each_device_needs_fresh_ui_restart_and_preservation_evidence(self):
        for name in ('mac', 'fire', 'apple_tv'):
            for key in DEVICE_CHECKS:
                with self.subTest(device=name, key=key):
                    r = copy.deepcopy(self.receipt); r['devices'][name][key] = False
                    with self.assertRaises(AssertionError): self.check(r)

    def test_speed_uses_medians_and_larger_of_twenty_percent_or_point35_seconds(self):
        r = copy.deepcopy(self.receipt)
        for d in r['devices']['fire']['browsing_speed']['sections'].values():
            d.update(before_seconds=[1, 1, 100], after_seconds=[1.35, 1.35, 1000])
        self.check(r)
        for d in r['devices']['fire']['browsing_speed']['sections'].values():
            d.update(before_seconds=[3, 3, 3], after_seconds=[3.6, 3.6, 3.6])
        self.check(r)
        r['devices']['fire']['browsing_speed']['sections']['Home']['after_seconds'] = [3.601] * 3
        with self.assertRaises(AssertionError): self.check(r)

    def test_speed_rejects_missing_sections_short_invalid_or_unidentified_samples(self):
        for change in ('missing_section', 'short', 'nan', 'infinite', 'boolean', 'zero', 'old_controller', 'protocol'):
            with self.subTest(change=change):
                r = copy.deepcopy(self.receipt); speed = r['devices']['fire']['browsing_speed']
                if change == 'missing_section': del speed['sections']['YouTube']
                elif change == 'old_controller': speed['after_controller'] = '0.1.82'
                elif change == 'protocol': speed['protocol'] = ''
                else:
                    speed['sections']['Home']['before_seconds'] = {
                        'short': [1, 1], 'nan': [1, float('nan'), 1],
                        'infinite': [1, float('inf'), 1], 'boolean': [1, True, 1], 'zero': [1, 0, 1]}[change]
                with self.assertRaises(AssertionError): self.check(r)

    def test_paused_stop_requires_actual_writer_and_numeric_cloud_agreement(self):
        changes = {'actual_outgoing_writer_verified': False, 'helper_source_exact': False,
                   'stopped_while_paused': False, 'pause_seconds': 0,
                   'kodi_position_seconds': 0, 'duration_seconds': 0,
                   'helper_stop_progress': 2.5, 'settled_trakt_progress': 2.5}
        for key, value in changes.items():
            with self.subTest(key=key):
                r = copy.deepcopy(self.receipt); r['devices']['fire']['paused_stop'][key] = value
                with self.assertRaises(AssertionError): self.check(r)
        for invalid in (True, '12', float('nan'), float('inf')):
            r = copy.deepcopy(self.receipt); r['devices']['fire']['paused_stop']['settled_trakt_progress'] = invalid
            with self.assertRaises(AssertionError): self.check(r)


class HelperProgressAcceptance(unittest.TestCase):
    def setUp(self):
        self.manifest = {'upstream_version': '6.17.9', 'playback_patch': 'sampled-progress-1',
                         'files': {'file%d' % n: '%064x' % n for n in range(471)}}
        self.receipt = {'source_version': '6.17.9', 'playback_patch': 'sampled-progress-1',
                        'source_files': copy.deepcopy(self.manifest['files']), 'source_origin_verified': True,
                        'device': 'Fire Stick Kodi21.3', 'mode': 'packaged', 'tests': 12,
                        'failures': 0, 'errors': 0, 'passed': True}

    def check(self, receipt=None, manifest=None):
        gate = getattr(verify_release, 'verify_helper_progress_acceptance', None)
        self.assertTrue(callable(gate), 'Missing exact current Helper native gate')
        gate(self.receipt if receipt is None else receipt, self.manifest if manifest is None else manifest)

    def test_exact_current_full_source_native_cache_proof_passes(self): self.check()

    def test_historical_partial_failed_or_nonnative_proof_is_rejected(self):
        for change in ('patch', 'source', 'partial', 'version', 'failed', 'failures', 'errors', 'tests', 'origin', 'mode', 'device'):
            with self.subTest(change=change):
                r = copy.deepcopy(self.receipt); m = copy.deepcopy(self.manifest)
                if change == 'patch': del r['playback_patch']
                elif change == 'source': r['source_files']['file0'] = 'historical'
                elif change == 'partial':
                    del m['files']['file0']; del r['source_files']['file0']
                elif change == 'version': r['source_version'] = '6.17.8'
                elif change == 'failed': r['passed'] = False
                elif change in ('failures', 'errors'): r[change] = 1
                elif change == 'tests': r['tests'] = 11
                elif change == 'origin': r['source_origin_verified'] = False
                elif change == 'mode': r['mode'] = 'synthetic'
                else: r['device'] = 'Mac'
                with self.assertRaises(AssertionError): self.check(r, m)


class FrozenInstallerBoundary(unittest.TestCase):
    def test_installer16_rejects_minimum17_before_native_setup(self):
        root = Path(__file__).resolve().parents[1]
        with zipfile.ZipFile(root/'plugin.program.blacklanturninstaller/plugin.program.blacklanturninstaller-1.0.16.zip') as z:
            source = z.read('plugin.program.blacklanturninstaller/resources/libs/platform_compatibility.py')
        old = types.ModuleType('frozen_installer16_compatibility')
        exec(compile(source, 'frozen-installer16/platform_compatibility.py', 'exec'), old.__dict__)
        managed = types.SimpleNamespace(verify_archive=lambda z: None, ProtectionError=RuntimeError)
        prefs = types.SimpleNamespace(verify_archive=lambda *a, **k: self.fail('Old installer reached preferences'), PreferenceError=RuntimeError)
        package = types.ModuleType('resources.libs'); package.managed_addons = managed; package.build_preferences = prefs
        with tempfile.TemporaryDirectory() as tmp, patch.dict('sys.modules', {'resources.libs': package}):
            path = Path(tmp)/'new-build.zip'
            with zipfile.ZipFile(path, 'w') as z:
                z.writestr('addons/skin.test/addon.xml', '<addon id="skin.test" version="1.0"/>')
                z.writestr('userdata/blacklanturn-build.json', json.dumps({
                    'schema': 3, 'edition': 'apple', 'kodi_major': 21, 'helper_patch': 'empty-cache-1',
                    'preferences_policy': 'playback-trakt-youtube-1', 'installer_min_version': '1.0.17'}))
            kodi = Kodi()
            with self.assertRaisesRegex(old.CompatibilityError, 'Update BlackLanturn Installer'):
                old.prepare(path, kodi)
            self.assertEqual(kodi.requests, [])
            self.assertEqual(kodi.commands, [])


if __name__ == '__main__': unittest.main()
