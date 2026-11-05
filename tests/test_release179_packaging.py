"""Release boundary checks: reject drift and forbid profile/private overlays."""
import importlib.util
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
import zipfile

SPEC = importlib.util.spec_from_file_location('release179', Path(__file__).resolve().parents[1] / 'compatibility/responsiveness179/release179.py')
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)


class ReleaseBoundaries(unittest.TestCase):
    def test_overlay_requires_exact_before_and_after(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'selection.py'
            source.write_bytes(b'approved')
            target = 'addons/plugin.video.themoviedb.helper/selection.py'
            item = {'target': target, 'source': str(source), 'before_sha256': release.sha(b'old'),
                    'sha256': release.sha(b'approved')}
            self.assertEqual(release.read_overlays([item], {target: b'old'}, root), {target: b'approved'})
            with self.assertRaisesRegex(ValueError, 'baseline'):
                release.read_overlays([item], {target: b'other'}, root)
            source.write_bytes(b'unreviewed')
            with self.assertRaisesRegex(ValueError, 'candidate'):
                release.read_overlays([item], {target: b'old'}, root)

    def test_no_userdata_private_or_unrelated_addon_overlay(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'file'
            source.write_bytes(b'new')
            for target in ['userdata/guisettings.xml', 'addons/plugin.video.blacklanturn.fights/main.py',
                           'addons/other/main.py', 'addons/plugin.video.youtube/../outside']:
                item = {'target': target, 'source': str(source), 'before_sha256': release.sha(b'old'),
                        'sha256': release.sha(b'new')}
                with self.subTest(target=target), self.assertRaisesRegex(ValueError, 'overlay path'):
                    release.read_overlays([item], {target: b'old'}, root)

    def test_duplicate_overlay_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'file'
            source.write_bytes(b'new')
            target = 'addons/plugin.video.youtube/file'
            item = {'target': target, 'source': str(source), 'before_sha256': release.sha(b'old'),
                    'sha256': release.sha(b'new')}
            with self.assertRaisesRegex(ValueError, 'Duplicate'):
                release.read_overlays([item, item], {target: b'old'}, root)

    def test_new_helper_module_requires_baseline_absence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'preview_transport.py'
            source.write_bytes(b'new module')
            target = 'addons/plugin.video.youtube/resources/lib/youtube_plugin/kodion/network/preview_transport.py'
            item = {'target': target, 'source': str(source), 'before_sha256': None,
                    'sha256': release.sha(b'new module')}
            self.assertEqual(release.read_overlays([item], {}, root), {target: b'new module'})
            with self.assertRaisesRegex(ValueError, 'baseline'):
                release.read_overlays([item], {target: b'foreign module'}, root)

    def test_edition_specific_overlay_uses_only_its_exact_baseline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            items = []
            target = 'addons/plugin.video.youtube/player_client.py'
            for label in ('general', 'apple'):
                source = root / label
                source.write_bytes((label + '-new').encode())
                items.append({'target': target, 'source': str(source), 'before_sha256': release.sha(label.encode()),
                              'sha256': release.sha(source.read_bytes()), 'editions': [label]})
            self.assertEqual(release.read_overlays(items, {target: b'general'}, root, 'general'), {target: b'general-new'})
            self.assertEqual(release.read_overlays(items, {target: b'apple'}, root, 'apple'), {target: b'apple-new'})

    def test_metadata_new_revision_retains_provenance(self):
        upstream = b'<addon id="plugin.video.youtube" version="7.4.4"/>'
        prior = upstream.replace(b'7.4.4', b'1:7.4.4+blacklanturn.1')
        policy = {'addons': {'plugin.video.youtube': [
            {'upstream_version': '7.4.4', 'managed_version': '1:7.4.4+blacklanturn.1',
             'upstream_sha256': release.sha(upstream), 'managed_sha256': release.sha(prior)}]}}
        new = release.next_metadata('plugin.video.youtube', prior, policy)
        self.assertIn(b'1:7.4.4+blacklanturn.2', new)
        self.assertEqual(len(policy['addons']['plugin.video.youtube']), 2)
        self.assertEqual(policy['addons']['plugin.video.youtube'][0]['upstream_sha256'], release.sha(upstream))
        self.assertEqual(release.next_metadata('plugin.video.youtube', prior, policy), new)
        self.assertEqual(len(policy['addons']['plugin.video.youtube']), 2)
        with self.assertRaisesRegex(ValueError, 'metadata'):
            release.next_metadata('plugin.video.youtube', b'<addon version="unknown"/>', policy)

    def test_installer54_accepts_new_minimum_and_keeps53_baseline_support(self):
        project = Path(__file__).resolve().parents[1]
        source = project
        installer = release.inventory(source / 'installer-source' / release.INSTALLER)
        prior_source = (source / 'compatibility/responsiveness179/legacy-managed-versions53.py').read_bytes()
        baselines = Path(os.environ.get('BLACKLANTURN_RELEASE61_BASELINES', project / 'baselines'))
        if not (baselines / release.full_name('General', release.BASE_VERSION)).exists():
            self.skipTest('Download exact public61-r1 baselines for native compatibility fixtures')
        data = {label: release.baseline(baselines / release.full_name(edition, release.BASE_VERSION), label)
                for label, (edition, _) in release.BASELINES.items()}
        updated = release.update_support(copy.deepcopy(installer), data, set())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            release.write_tree(root / 'new', updated)
            release.write_tree(root / 'old', {'resources/libs/managed_versions.py': prior_source,
                                              'resources/managed-versions.json': installer['resources/managed-versions.json']})
            new = release.load('new_policy179_test', root / 'new/resources/libs/managed_versions.py')
            old = release.load('old_policy179_test', root / 'old/resources/libs/managed_versions.py')
            marker = json.loads(data['general'][release.MARKER])
            base = baselines / release.full_name('General', release.BASE_VERSION)
            with zipfile.ZipFile(base) as archive:
                self.assertEqual(new.prepare_policy(marker, archive), '1.0.53')
                marker.update(installer_min_version='1.0.54', responsiveness_patch='preview-services-1')
                with self.assertRaisesRegex(ValueError, 'Update BlackLanturn Installer'):
                    old.prepare_policy(marker, archive)
                self.assertEqual(new.prepare_policy(marker, archive), '1.0.54')
                marker['responsiveness_patch'] = 'unknown'
                with self.assertRaisesRegex(ValueError, 'Update BlackLanturn Installer'):
                    new.prepare_policy(marker, archive)

    def test_changed_helper_tree_and_baseline_remain_independently_accepted(self):
        project = Path(__file__).resolve().parents[1]
        source = project
        installer = release.inventory(source / 'installer-source' / release.INSTALLER)
        baselines = Path(os.environ.get('BLACKLANTURN_RELEASE61_BASELINES', project / 'baselines'))
        if not (baselines / release.full_name('General', release.BASE_VERSION)).exists():
            self.skipTest('Download exact public61-r1 baselines for native compatibility fixtures')
        data = {label: release.baseline(baselines / release.full_name(edition, release.BASE_VERSION), label)
                for label, (edition, _) in release.BASELINES.items()}
        aid = 'plugin.video.themoviedb.helper'
        prefix = 'addons/' + aid + '/'
        target = prefix + 'resources/tmdbhelper/lib/sync/providers/selection.py'
        candidate = (source / 'compatibility/reliability178/helper-selection.py').read_bytes()
        original_tree = {name: raw for name, raw in data['general'].items() if name.startswith(prefix)}
        for files in data.values():
            files[target] = candidate
        updated = release.update_support(copy.deepcopy(installer), data, {aid})
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            release.write_tree(root / 'installer', updated)
            managed = release.load('managed179_helper_test', root / 'installer/resources/libs/managed_addons.py')
            release.write_tree(root / 'profile', {name: raw for name, raw in data['general'].items() if name.startswith(prefix)})
            managed._verify_installed_helper(root / 'profile')
            self.assertIn(b'+blacklanturn.2', data['general'][prefix + 'addon.xml'])
            release.write_tree(root / 'profile', original_tree)
            managed._verify_installed_helper(root / 'profile')
            (root / 'profile' / target).write_bytes(candidate)
            # Complete historical/new trees are accepted, mixed trees are not.
            # Metadata normalizes by exact provenance, so a changed body with
            # old metadata still resolves to the same new normalized tree.
            managed._verify_installed_helper(root / 'profile')
            (root / 'profile' / target).write_bytes(b'foreign implementation')
            with self.assertRaises(managed.ProtectionError):
                managed._verify_installed_helper(root / 'profile')

    def test_youtube_keeps_both_edition_versions(self):
        project = Path(__file__).resolve().parents[1]
        source = project
        installer = release.inventory(source / 'installer-source' / release.INSTALLER)
        baselines = Path(os.environ.get('BLACKLANTURN_RELEASE61_BASELINES', project / 'baselines'))
        if not (baselines / release.full_name('General', release.BASE_VERSION)).exists():
            self.skipTest('Download exact public61-r1 baselines for native compatibility fixtures')
        data = {label: release.baseline(baselines / release.full_name(edition, release.BASE_VERSION), label)
                for label, (edition, _) in release.BASELINES.items()}
        updated = release.update_support(installer, data, {'plugin.video.youtube'})
        key = 'addons/plugin.video.youtube/addon.xml'
        self.assertIn(b'1:7.4.4+blacklanturn.2', data['general'][key])
        self.assertIn(b'1:7.4.4a+blacklanturn.2', data['apple'][key])
        policy = json.loads(updated['resources/managed-versions.json'])
        self.assertEqual(len(policy['addons']['plugin.video.youtube']), 4)

    def test_snapshot_drift_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            release.write_tree(root, {'pipeline/release179.py': Path(release.__file__).read_bytes(), 'source/file': b'frozen'})
            doc = {'versions': release.VERSIONS, 'files': release.record(release.inventory(root))}
            (root / 'source-manifest.json').write_bytes(release.encoded(doc))
            self.assertEqual(release.verify_snapshot(root), doc)
            (root / 'source/file').write_bytes(b'drift')
            with self.assertRaisesRegex(ValueError, 'drifted'):
                release.verify_snapshot(root)

    def test_already_adopted_release_versions_are_reproducible(self):
        files = {'addon.xml': b'<addon id="script.blacklanturn.preview" version="0.1.126"/>'}
        before = dict(files)
        release.bump_addon(files, release.CONTROLLER, '0.1.125', '0.1.126')
        self.assertEqual(files, before)

    def test_active_feed_limit_retains_complete_edition_pairs(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        entries = [{'version': '1.1.' + str(version), 'revision': 0, 'edition': edition,
                    'id': f'{edition}-{version}', 'proof': 'x' * 100}
                   for version in range(12, 0, -1) for edition in ('general', 'apple')]
        original = copy.deepcopy(entries)
        validator = SimpleNamespace(MAX_BYTES=1800, validate_catalog=lambda feed: None)
        with patch.object(release, 'FEED_TARGET_BYTES', 1600):
            raw = release.validated_feed(validator, entries)
        feed = json.loads(raw)['releases']
        self.assertLessEqual(len(raw), 1600)
        self.assertEqual({e['id'] for e in feed[:2]}, {'general-12', 'apple-12'})
        for version in {e['version'] for e in feed}:
            self.assertEqual({e['edition'] for e in feed if e['version'] == version}, {'general', 'apple'})
        self.assertEqual(entries, original)

    def test_canonical54_shared_minimum_agrees_for_helper_coco_and_managed_policy(self):
        import sys
        from types import SimpleNamespace
        from unittest.mock import patch
        project = Path(__file__).resolve().parents[1]
        source = project
        baselines = Path(os.environ.get('BLACKLANTURN_RELEASE61_BASELINES', project / 'baselines'))
        if not (baselines / release.full_name('General', release.BASE_VERSION)).exists():
            self.skipTest('Download exact public61-r1 baselines for native compatibility fixtures')
        lib = source / 'installer-source' / release.INSTALLER / 'resources/libs'
        versions = release.load('canonical_versions179_minimum', lib / 'managed_versions.py')
        base = baselines / release.full_name('General', release.BASE_VERSION)
        stub = SimpleNamespace(_versions=versions, HELPER='plugin.video.themoviedb.helper',
                               PREFIX='addons/plugin.video.themoviedb.helper/', ProtectionError=ValueError)
        with zipfile.ZipFile(base) as archive:
            marker = json.loads(archive.read(release.MARKER))
            marker.update(installer_min_version='1.0.54', responsiveness_patch='preview-services-1')
            self.assertEqual(versions.prepare_policy(marker, archive), '1.0.54')
            with patch.dict(sys.modules, {'resources.libs': SimpleNamespace(managed_addons=stub)}):
                for name in ('helper_providers', 'cocoscrapers_policy'):
                    module = release.load('canonical179_' + name, lib / (name + '.py'))
                    with patch.object(module, 'verify_archive'), patch.object(module, 'verify_installed'):
                        module.prepare(marker, archive, Path('/disposable-profile'))
                        marker['responsiveness_patch'] = 'unknown'
                        with self.assertRaises(ValueError):
                            module.prepare(marker, archive, Path('/disposable-profile'))
                        marker['responsiveness_patch'] = 'preview-services-1'


if __name__ == '__main__':
    unittest.main()
