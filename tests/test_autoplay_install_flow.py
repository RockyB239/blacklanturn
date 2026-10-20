"""New autoplay policy: actual Standard preservation and old-installer refusal."""
import types
from pathlib import Path
from unittest.mock import patch
import test_network_install_flow as network

ROOT=Path(__file__).resolve().parents[1]
POLICY=dict(network.POLICY,preferences_policy='playback-trakt-youtube-umbrella-network-autoplay-1',
            installer_min_version='1.0.20',autoplay_patch='same-show-source-1')

class AutoplayInstallFlow(network.NetworkInstallFlow):
    def packaged(self,corrupt=False,policy=None):
        return super().packaged(corrupt=corrupt,policy=POLICY if policy is None else policy)

    def test_installer19_rejects_before_device_setup_or_cleanup(self):
        k,cfg,mods=self.f.environment();archive=self.packaged()
        module=types.ModuleType('installer19_preflight')
        module.__file__=str(network.umbrella_fixture.LIB/'platform_compatibility.py')
        source=(ROOT/'tests/fixtures/platform_compatibility_1_0_19.py').read_text()
        exec(compile(source,module.__file__,'exec'),module.__dict__)
        with patch.dict('sys.modules',mods),self.assertRaises(module.CompatibilityError):module.prepare(archive,k,home=cfg.HOME)
        self.assertEqual(k.requests,[]);self.assertEqual(k.commands,[])
        self.assertTrue((Path(cfg.HOME)/'userdata/keep-before-preflight.txt').exists())

    def test_missing_autoplay_policy_fails_before_cleanup(self):
        k,cfg,mods=self.f.environment();policy=dict(POLICY);del policy['autoplay_patch']
        self.packaged(policy=policy);self.f.install(cfg,mods)
        self.assertTrue((Path(cfg.HOME)/'userdata/keep-before-preflight.txt').exists())
        self.assertEqual(k.requests,[]);self.assertEqual(k.commands,[])

    def test_account_only_retains_selected_accounts_and_uses_build_defaults(self):
        k,cfg,mods=self.f.environment(auth_only=True);self.packaged();self.f.install(cfg,mods)
        home=Path(cfg.HOME)
        self.assertFalse((home/'userdata/keep-before-preflight.txt').exists())
        values=self.f.values(home/'userdata/addon_data/plugin.video.umbrella/settings.xml')
        for key,value in self.f.credentials.items():self.assertEqual(values[key],value)
        self.assertEqual(self.f.values(home/'userdata/guisettings.xml')['locale.audiolanguage'],'default')
        self.assertEqual((home/'userdata/addon_data/plugin.video.youtube/access_manager.json').read_bytes(),b'{"fixture":{"refresh_token":"private-refresh"}}')
        self.assertFalse((home/'userdata/favourites.xml').exists())
