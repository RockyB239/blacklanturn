"""Real wizard verifies common code before cleanup and preserves user choices."""
import json
import types
from unittest.mock import patch
from pathlib import Path
import sqlite3
import unittest
import zipfile
import test_umbrella_install_flow as umbrella_fixture

ROOT = Path(__file__).resolve().parents[1]
ADDON = 'script.module.jurialmunkey'
POLICY = dict(umbrella_fixture.POLICY,
              preferences_policy='playback-trakt-youtube-umbrella-network-1',
              installer_min_version='1.0.19', network_patch='request-reliability-privacy-1')


class NetworkInstallFlow(unittest.TestCase):
    def setUp(self):
        self.f = umbrella_fixture.UmbrellaInstallFlow(); self.f.setUp()
        self.addCleanup(self.f.doCleanups)

    def packaged(self, corrupt=False, policy=None):
        with zipfile.ZipFile(ROOT/'compatibility/shared-requests/upstream-general-0.2.35.zip') as z:
            files = {'addons/'+n:z.read(n) for n in z.namelist()}
        files['addons/'+ADDON+'/resources/modules/jurialmunkey/reqapi.py'] = (
            ROOT/'compatibility/shared-requests'/('general-before.py' if corrupt else 'reqapi.py')).read_bytes()
        return self.f.packaged(change=lambda data:data.update(files), policy=POLICY if policy is None else policy)

    def test_standard_install_preserves_accounts_playback_and_existing_rules(self):
        k,cfg,mods = self.f.environment(); self.packaged()
        h = Path(cfg.HOME); self.f.install(cfg,mods)
        self.assertFalse((h/'userdata/keep-before-preflight.txt').exists(), 'New policy never reached the real install flow')
        self.assertEqual((h/'addons'/ADDON/'resources/modules/jurialmunkey/reqapi.py').read_bytes(),
                         (ROOT/'compatibility/shared-requests/reqapi.py').read_bytes())
        vals = self.f.values(h/'userdata/addon_data/plugin.video.umbrella/settings.xml')
        for key,value in self.f.credentials.items(): self.assertEqual(vals[key], value)
        self.assertEqual(vals['remove.hdr'], 'true'); self.assertEqual(vals['scrobble'], 'Local')
        self.assertEqual(self.f.values(h/'userdata/guisettings.xml')['locale.audiolanguage'], 'English')
        self.assertEqual(self.f.values(h/'userdata/addon_data/plugin.video.youtube/settings.xml')['kodion.mpd.quality.selection'], '3')
        self.assertEqual((h/'userdata/addon_data/plugin.video.youtube/access_manager.json').read_bytes(), b'{"fixture":{"refresh_token":"private-refresh"}}')
        with sqlite3.connect(h/'userdata/Database/Addons33.db') as c:
            rules = c.execute('SELECT addonID,updateRule FROM update_rules ORDER BY id').fetchall()
        self.assertIn(('repository.keep',2), rules); self.assertIn((ADDON,1), rules)
        self.assertEqual(k.commands.count('UpdateLocalAddons'), 2)

    def test_unpatched_shared_code_fails_before_cleanup_and_native_setup(self):
        k,cfg,mods = self.f.environment(); self.packaged(corrupt=True)
        h=Path(cfg.HOME); self.f.install(cfg,mods)
        self.assertEqual((h/'userdata/keep-before-preflight.txt').read_bytes(), b'keep until verified')
        self.assertEqual(k.requests, []); self.assertNotIn('UpdateLocalAddons', k.commands)

    def test_installer18_rejects_new_payload_before_device_setup(self):
        k,cfg,mods=self.f.environment();archive=self.packaged()
        module=types.ModuleType('installer18_preflight')
        module.__file__=str(umbrella_fixture.LIB/'platform_compatibility.py')
        source=(ROOT/'tests/fixtures/platform_compatibility_1_0_18.py').read_text()
        exec(compile(source,module.__file__,'exec'),module.__dict__)
        with patch.dict('sys.modules',mods),self.assertRaises(module.CompatibilityError):module.prepare(archive,k,home=cfg.HOME)
        self.assertEqual(k.requests,[])

    def test_missing_patch_policy_fails_before_cleanup(self):
        k,cfg,mods=self.f.environment();policy=dict(POLICY);del policy['network_patch']
        self.packaged(policy=policy);self.f.install(cfg,mods)
        self.assertTrue((Path(cfg.HOME)/'userdata/keep-before-preflight.txt').exists())
        self.assertEqual(k.requests,[])


if __name__ == '__main__': unittest.main()
