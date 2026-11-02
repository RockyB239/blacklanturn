"""A newer reviewed service patch must have a distinct installer requirement."""
import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / 'installer-source/plugin.program.blacklanturninstaller'
sys.path.insert(0, str(INSTALLER))

def load():
    path = INSTALLER / 'resources/libs/managed_versions.py'
    spec = importlib.util.spec_from_file_location('shutdown156_versions', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class ShutdownReleasePolicy(unittest.TestCase):
    def marker(self):
        return dict(managed_update_policy='kodi-version-epoch-1',
                    inplace_update_policy='bundled-code-1', bundle_registration_policy='new-bundles-1',
                    youtube_refresh_patch='youtube-freshness-2', helper_sync_policy='providers-1',
                    cocoscrapers_policy='parallel-airdate-1', installer_min_version='1.0.48')

    def test_new_service_patch_requires51_and_legacy_release_keeps48(self):
        module = load()
        with patch.object(module, 'verify_archive_metadata'):
            self.assertEqual(module.prepare_policy(self.marker(), None), '1.0.48')
            current = dict(self.marker(), shutdown_patch='retained-monitor-1', installer_min_version='1.0.51')
            self.assertEqual(module.prepare_policy(current, None), '1.0.51')
            with self.assertRaises(ValueError):
                module.prepare_policy(dict(current, installer_min_version='1.0.48'), None)

    def test_unknown_shutdown_revision_is_rejected(self):
        module = load()
        with patch.object(module, 'verify_archive_metadata'), self.assertRaises(ValueError):
            module.prepare_policy(dict(self.marker(), shutdown_patch='unknown'), None)

if __name__ == '__main__':
    unittest.main()
