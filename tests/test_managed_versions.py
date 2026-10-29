"""Exact metadata protection; no runtime source or preference changes."""
import copy
import importlib.util
import json
import hashlib
import tempfile
import zipfile
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / 'installer-source/plugin.program.blacklanturninstaller/resources/libs'


class ManagedVersions(unittest.TestCase):
    def setUp(self):
        path = LIB / 'managed_versions.py'
        self.assertTrue(path.is_file(), 'Managed bulk-update protection is missing')
        spec = importlib.util.spec_from_file_location('managed_versions_test', path)
        self.m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.m)
        self.policy = json.loads((LIB.parent / 'managed-versions.json').read_text())

    def data(self, apple=False):
        data = {'userdata/keep.txt': b'preserve', 'addons/unrelated/code.py': b'ordinary'}
        for key in self.policy['source_adapters']:
            data['addons/' + key] = (ROOT / 'compatibility/managed-updates/umbrella/upstream' / key.split('/', 1)[1]).read_bytes()
        for aid, variants in self.policy['addons'].items():
            variant = variants[-1] if apple and aid == 'plugin.video.youtube' else variants[0]
            name = aid + '-' + variant['upstream_version'] + '.xml'
            data['addons/' + aid + '/addon.xml'] = (ROOT / 'compatibility/managed-updates/metadata' / name).read_bytes()
        return data

    def test_both_editions_transform_only_exact_metadata_and_round_trip(self):
        for apple in (False, True):
            data = self.data(apple); before = copy.deepcopy(data)
            self.m.apply_metadata(data)
            for name, raw in data.items():
                if name.endswith('/addon.xml'):
                    aid = name.split('/')[1]
                    self.assertEqual(self.m.normalize_metadata(aid, raw), before[name])
                    self.assertTrue(self.m.upstream_version(aid, raw))
                    self.assertIn(b'1:', raw)
                else:
                    self.assertEqual(raw, before[name])

    def test_exact_metadata_transform_is_idempotent(self):
        data = self.data(); self.m.apply_metadata(data); once = dict(data)
        self.m.apply_metadata(data); self.assertEqual(data, once)

    def test_unknown_source_or_missing_addon_fails_atomically(self):
        for change in ('unknown', 'missing'):
            data = self.data(); key = 'addons/plugin.video.youtube/addon.xml'
            if change == 'unknown': data[key] = data[key].replace(b'7.4.4', b'7.5.0')
            else: del data[key]
            before = dict(data)
            with self.assertRaises(ValueError): self.m.apply_metadata(data)
            self.assertEqual(data, before)

    def test_unknown_managed_metadata_is_never_normalized(self):
        data = self.data(); self.m.apply_metadata(data)
        aid = 'plugin.video.umbrella'; key = 'addons/' + aid + '/addon.xml'
        bad = data[key].replace(b'blacklanturn.1', b'blacklanturn.2')
        self.assertEqual(self.m.normalize_metadata(aid, bad), bad)
        with self.assertRaises(ValueError): self.m.upstream_version(aid, bad)

    def test_epoch_does_not_hide_other_metadata_edits(self):
        data = self.data(); self.m.apply_metadata(data)
        aid = 'plugin.video.umbrella'; key = 'addons/' + aid + '/addon.xml'
        bad = data[key].replace(b'<addon ', b'<addon foreign="true" ', 1)
        self.assertEqual(self.m.normalize_metadata(aid, bad), bad)
        with self.assertRaises(ValueError): self.m.verify_metadata(data | {key: bad})

    def test_policy_requires_all_four_managed_addons(self):
        data = self.data(); self.m.apply_metadata(data); self.m.verify_metadata(data)
        self.assertEqual(len(self.policy['addons']), 4)
        del data['addons/script.module.jurialmunkey/addon.xml']
        with self.assertRaises(ValueError): self.m.verify_metadata(data)

    def test_unmanaged_addon_metadata_is_unchanged(self):
        raw = b'<addon id="unrelated" version="99"/>'
        self.assertEqual(self.m.normalize_metadata('unrelated', raw), raw)

    def test_old_metadata_cannot_claim_bulk_update_protection(self):
        with self.assertRaises(ValueError): self.m.verify_metadata(self.data())

    def managed(self):
        spec = importlib.util.spec_from_file_location('managed_versions_inventory', LIB / 'managed_addons.py')
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        return m

    def test_installed_inventory_normalizes_only_reviewed_metadata(self):
        data = self.data(); before = dict(data); self.m.apply_metadata(data)
        aid = 'plugin.video.umbrella'; key = 'addons/' + aid + '/addon.xml'
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / aid; p.mkdir(); (p / 'addon.xml').write_bytes(data[key])
            for adapter in self.policy['source_adapters']:
                rel = adapter.split('/',1)[1]; dest = p / rel; dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes((ROOT / 'compatibility/managed-updates/umbrella/candidate' / rel).read_bytes())
            actual = self.managed()._source_files(p, 'invalid')
            self.assertEqual(actual['addon.xml'], hashlib.sha256(before[key]).hexdigest())

    def test_metadata_overlay_keeps_exact_helper_archive_accepted(self):
        from test_managed_helper import ManagedTests
        fixture = ManagedTests(); fixture.setUp()
        self.addCleanup(fixture.tearDown)
        with zipfile.ZipFile(fixture.archive()) as z:
            data = {n:z.read(n) for n in z.namelist()}
        metadata = self.data(); self.m.apply_metadata(metadata)
        key = 'addons/plugin.video.themoviedb.helper/addon.xml'; data[key] = metadata[key]
        path = fixture.root / 'versioned-helper.zip'
        with zipfile.ZipFile(path, 'w') as z:
            for n,raw in data.items(): z.writestr(n,raw)
        with zipfile.ZipFile(path) as z:
            self.assertEqual(self.managed().verify_archive(z), 'plugin.video.themoviedb.helper')

    def test_whitelist_cannot_keep_old_unprotected_metadata(self):
        from test_managed_helper import ManagedTests
        fixture = ManagedTests(); fixture.setUp(); self.addCleanup(fixture.tearDown)
        with zipfile.ZipFile(fixture.archive()) as z: z.extractall(fixture.root)
        m = self.managed()
        with self.assertRaises(m.ProtectionError):
            m.verify_kept(fixture.root, {m.HELPER}, metadata_protected=True)

    def test_legacy_metadata_cannot_hide_a_partial_adapter_pair(self):
        for chosen in self.policy['source_adapters']:
            data = self.data()
            rel = chosen.split('/',1)[1]
            data['addons/' + chosen] = (ROOT / 'compatibility/managed-updates/umbrella/candidate' / rel).read_bytes()
            with tempfile.TemporaryDirectory() as tmp:
                home = Path(tmp); addon = home / 'addons/plugin.video.umbrella'; addon.mkdir(parents=True)
                for key, raw in data.items():
                    if key.startswith('addons/plugin.video.umbrella/'):
                        path = home / key; path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
                with self.assertRaises(ValueError): self.m.verify_installed_adapters(addon)
                checker = getattr(self.m, 'verify_adapter_sets', None)
                self.assertTrue(callable(checker), 'Archive verification needs atomic adapter sets')
                with self.assertRaises(ValueError): checker(data)

    def test_managed_metadata_without_internal_adapter_is_rejected(self):
        data = self.data(); self.m.apply_metadata(data)
        with tempfile.TemporaryDirectory() as tmp:
            addon = Path(tmp) / 'plugin.video.umbrella'; addon.mkdir()
            (addon / 'addon.xml').write_bytes(data['addons/plugin.video.umbrella/addon.xml'])
            for key in self.policy['source_adapters']:
                rel = key.split('/',1)[1]; target = addon / rel; target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data['addons/' + key])
            with self.assertRaises(ValueError): self.m.verify_installed_adapters(addon)

    def test_exact_version_adapter_required_and_normalized_without_accepting_foreign_code(self):
        data = self.data(); candidates = {}
        for key, variant in self.policy['source_adapters'].items():
            rel = key.split('/', 1)[1]
            data['addons/' + key] = (ROOT / 'compatibility/managed-updates/umbrella/upstream' / rel).read_bytes()
            candidates[key] = (ROOT / 'compatibility/managed-updates/umbrella/candidate' / rel).read_bytes()
        apply = getattr(self.m, 'apply_source_adapters', None)
        self.assertTrue(callable(apply), 'Managed versions need their reviewed internal version adapter')
        apply(data, candidates)
        for key, raw in candidates.items():
            self.assertEqual(data['addons/' + key], raw)
            aid, rel = key.split('/', 1)
            self.assertEqual(self.managed()._digest(aid, rel, raw), self.policy['source_adapters'][key]['upstream_sha256'])
            self.assertEqual(self.managed()._digest(aid, rel, raw + b'foreign'), hashlib.sha256(raw + b'foreign').hexdigest())
        before = dict(data)
        with self.assertRaises(ValueError): apply(data, dict(candidates, **{next(iter(candidates)):b'foreign'}))
        self.assertEqual(data, before)

    def test_builder_has_metadata_only_stage(self):
        spec = importlib.util.spec_from_file_location('build_managed_versions', ROOT / 'tools/build_release.py')
        b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
        stage = getattr(b, 'apply_managed_versions', None)
        self.assertTrue(callable(stage), 'Both package editions must receive bulk-update protection')
        data = self.data(); stage(data); self.m.verify_metadata(data)

    def test_new_policy_requires_current_installer_and_exact_metadata(self):
        import io
        data = self.data(); self.m.apply_metadata(data)
        self.m.apply_source_adapters(data, {key:(ROOT / 'compatibility/managed-updates/umbrella/candidate' / key.split('/',1)[1]).read_bytes() for key in self.policy['source_adapters']})
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as z:
            for n, raw in data.items(): z.writestr(n, raw)
        with zipfile.ZipFile(stream) as z:
            gate = getattr(self.m, 'prepare_policy', None)
            self.assertTrue(callable(gate), 'Protected packages need a pre-cleanup installer gate')
            good = {'managed_update_policy': 'kodi-version-epoch-1', 'installer_min_version': self.policy['installer_min_version'], 'youtube_refresh_patch': 'youtube-freshness-2'}
            self.assertEqual(gate(good, z), self.policy['installer_min_version'])
            self.assertIsNone(gate({}, z))
            for bad in (good | {'installer_min_version':'1.0.24'},good | {'installer_min_version':'1.0.25'}, good | {'managed_update_policy':'future'}, good | {'youtube_refresh_patch':'unknown'}):
                with self.assertRaises(ValueError): gate(bad, z)

    def test_exact_reviewed_upstream97_inventory_passes_but_mixed_tree_fails(self):
        # Inventory-contract test; actual installed bytes are checked separately
        # by the native Standard-update preflight.
        inventory = json.loads((ROOT / 'compatibility/managed-updates/upstream-umbrella-6.7.97.json').read_text())
        m = self.managed()
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp); addon = home / 'addons/plugin.video.umbrella'; addon.mkdir(parents=True)
            (addon / 'addon.xml').write_text('<addon id="plugin.video.umbrella" version="6.7.97"/>')
            with patch.object(m, '_source_files', return_value=inventory['files']):
                self.assertEqual(m.verify_installed(home), 'plugin.video.umbrella')
            mixed = dict(inventory['files']); mixed['resources/lib/modules/player.py'] = '0' * 64
            with patch.object(m, '_source_files', return_value=mixed), self.assertRaises(m.ProtectionError):
                m.verify_installed(home)

    def test_installer24_rejects_protected_package_before_native_setup(self):
        import types
        from test_youtube_refresh_install_flow import RefreshInstallFlow
        f = RefreshInstallFlow(); f.setUp(); self.addCleanup(f.doCleanups)
        kodi, config, modules = f.f.f.environment()
        path = f.packaged()
        with zipfile.ZipFile(path) as z: data = {n:z.read(n) for n in z.namelist()}
        marker = json.loads(data['userdata/blacklanturn-build.json'])
        marker.update(managed_update_policy='kodi-version-epoch-1', installer_min_version='1.0.25')
        data['userdata/blacklanturn-build.json'] = json.dumps(marker).encode()
        with zipfile.ZipFile(path, 'w') as z:
            for n, raw in data.items(): z.writestr(n, raw)
        old = types.ModuleType('old24'); old.__file__ = str(LIB / 'platform_compatibility.py')
        exec(compile((ROOT / 'tests/fixtures/platform_compatibility_1_0_24.py').read_text(), old.__file__, 'exec'), old.__dict__)
        with patch.dict('sys.modules', modules), self.assertRaises(old.CompatibilityError):
            old.prepare(path, kodi, home=config.HOME)
        self.assertEqual(kodi.requests, [])


if __name__ == '__main__':
    unittest.main()

class RowLayoutProtocol(unittest.TestCase):
    setUp=ManagedVersions.setUp
    def test_registration_protocol_accepts_exact_new_floor_and_old_recovery_floor(self):
        marker={'managed_update_policy':self.policy['policy'],'inplace_update_policy':'bundled-code-1','bundle_registration_policy':'new-bundles-1','youtube_refresh_patch':'youtube-freshness-2'}
        with patch.object(self.m,'verify_archive_metadata'):
            for floor in ('1.0.39','1.0.40'):
                self.assertEqual(self.m.prepare_policy(dict(marker,installer_min_version=floor),None),floor)
            with self.assertRaises(ValueError):self.m.prepare_policy(dict(marker,installer_min_version='1.0.41'),None)
