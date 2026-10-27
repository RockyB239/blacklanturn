"""A bundled Installer joins the same preserving, recoverable code transaction."""
import errno
import importlib.util
import json
import os
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch

import test_inplace_update as fixture
from test_inplace_update import LIB, meta


class InstallerTransaction(unittest.TestCase):
    setUp = fixture.InPlace.setUp
    seed = fixture.InPlace.seed
    saved = fixture.InPlace.saved
    archive = fixture.InPlace.archive
    def prepare(self):
        try:
            return fixture.InPlace.prepare(self)
        except self.m.UpdateError as exc:
            self.fail('Supported bundled Installer was rejected: '+str(exc))

    def test_active_writer_is_reported_as_busy_without_touching_its_staging(self):
        plan = self.prepare()
        try:
            try:
                self.m.recover(self.home)
            except self.m.UpdateError as exc:
                self.assertEqual(type(exc).__name__, 'UpdateBusy')
            else:
                self.fail('Recovery acquired the active updater lock')
            self.assertTrue(Path(plan['work']).exists())
        finally:
            self.m.cancel(plan)

    def test_lock_io_error_is_not_misreported_as_an_active_writer(self):
        with patch.object(self.m.fcntl, 'flock', side_effect=OSError(errno.EIO, 'lock I/O failed')):
            try:
                with self.assertRaises(OSError): self.m.recover(self.home)
            except self.m.UpdateError as exc:
                self.fail('Lock I/O error was hidden as updater contention: '+str(exc))

    def bundled_installer(self, installed='1.0.32', bundled='1.0.33'):
        aid = self.m.SELF
        self.enabled_before = True
        self.kodi_requests = []
        def details(raw):
            request = json.loads(raw)
            self.kodi_requests.append(request)
            if request.get('method') == 'Addons.GetAddonDetails' and request.get('params', {}).get('addonid') == aid and (self.home/'addons'/aid).is_dir():
                return json.dumps({'result': {'addon': {'addonid': aid, 'version': installed, 'enabled': self.enabled_before}}})
            return json.dumps({'error': {'message': 'not installed'}})
        self.kodi.executeJSONRPC = details
        self.seed(aid, installed, {'obsolete.py': b'old installer'})
        self.seed('script.blacklanturn.preview', '0.1.94', {'installer_recovery.py': b'controller recovery hook'})
        # The outgoing source is a real independent cold-recovery entry point.
        for name in ('inplace_update', 'standard_addons', 'archive_paths', 'portable_lock', 'component_update', 'stream_io'):
            destination = self.home/'addons'/aid/'resources/libs'/(name+'.py')
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes((LIB/(name+'.py')).read_bytes())
        self.data['addons/'+aid+'/addon.xml'] = meta(aid, bundled)
        self.data['addons/'+aid+'/lib/new.py'] = b'new installer'
        # Opposite archive order and sorted journal order cannot choose commit order.
        self.data = {k:self.data[k] for k in sorted(self.data)}
        return aid

    def tree(self, aid):
        root = self.home/'addons'/aid
        return {p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts}

    def old_marker(self):
        self.assertEqual(json.loads((self.home/'userdata/blacklanturn-build.json').read_text()), self.marker)

    def test_installer_updates_its_whole_tree_with_addons_and_preserves_all_user_data(self):
        aid = self.bundled_installer()
        result = self.m.apply(self.prepare())
        self.assertIn(aid, result['updated'])
        self.assertEqual((self.home/'addons'/aid/'lib/new.py').read_bytes(), b'new installer')
        self.assertFalse((self.home/'addons'/aid/'obsolete.py').exists())
        self.assertEqual((self.home/'addons'/self.aid/'lib/new.py').read_bytes(), b'new code')
        self.assertEqual(self.saved(), self.before)

    def test_newer_installer_is_retained_without_any_tree_changes(self):
        aid = self.bundled_installer(installed='1.0.34', bundled='1.0.33')
        before = self.tree(aid)
        result = self.m.apply(self.prepare())
        self.assertIn(aid, result['retained'])
        self.assertNotIn(aid, result['updated'])
        self.assertEqual(self.tree(aid), before)

    def test_changed_installer_at_equal_version_is_replaced_as_complete_tree(self):
        aid = self.bundled_installer(installed='1.0.33', bundled='1.0.33')
        result = self.m.apply(self.prepare())
        self.assertIn(aid, result['updated'])
        self.assertFalse((self.home/'addons'/aid/'obsolete.py').exists())

    def test_absent_installer_without_known_registration_state_refuses_update(self):
        aid = self.bundled_installer()
        shutil.rmtree(self.home/'addons'/aid)
        with self.assertRaises(self.m.UpdateError): fixture.InPlace.prepare(self)
        self.assertFalse((self.home/'addons'/aid).exists())
        self.old_marker()

    def test_self_update_requires_existing_recovery_capable_controller(self):
        for missing in ('old93', 'missing_hook'):
            with self.subTest(missing=missing):
                aid = self.bundled_installer()
                controller = self.home/'addons/script.blacklanturn.preview'
                if missing == 'old93': (controller/'addon.xml').write_bytes(meta('script.blacklanturn.preview', '0.1.93'))
                else: (controller/'installer_recovery.py').unlink()
                before = {name:self.tree(name) for name in (aid, self.aid, 'script.blacklanturn.preview')}
                with self.assertRaisesRegex(self.m.UpdateError, 'Update to BlackLanturn Build 1.1.27 before updating the Installer with the build'):
                    fixture.InPlace.prepare(self)
                for name in before: self.assertEqual(self.tree(name), before[name])
                self.assertEqual(self.saved(), self.before)
                self.old_marker()
                self.assertFalse((self.home/'addons/.blacklanturn-update').exists())

    def test_self_update_refuses_linked_existing_controller_files(self):
        aid = self.bundled_installer()
        controller = self.home/'addons/script.blacklanturn.preview'
        (controller/'installer_recovery.py').unlink()
        (controller/'installer_recovery.py').symlink_to(self.home/'userdata/sources.xml')
        before = self.tree(aid)
        with self.assertRaises(self.m.UpdateError): fixture.InPlace.prepare(self)
        self.assertEqual(self.tree(aid), before)
        self.assertEqual(self.saved(), self.before)
        self.old_marker()

    def test_retained_installer_does_not_require_existing_controller_recovery_hook(self):
        aid = self.bundled_installer(installed='1.0.34', bundled='1.0.33')
        controller = self.home/'addons/script.blacklanturn.preview'
        (controller/'addon.xml').write_bytes(meta('script.blacklanturn.preview', '0.1.93'))
        (controller/'installer_recovery.py').unlink()
        plan = self.prepare()
        try: self.assertIn(aid, plan['retained'])
        finally: self.m.cancel(plan)

    def test_changed_installer_journal_snapshots_exact_enabled_and_disabled_state(self):
        for enabled in (True, False):
            with self.subTest(enabled=enabled):
                aid = self.bundled_installer()
                self.enabled_before = enabled
                plan = self.prepare()
                try:
                    entry = plan['state']['addons'][aid]
                    self.assertIs(entry.get('enabled_before'), enabled)
                    durable = json.loads((Path(plan['work'])/'journal.json').read_bytes())
                    self.assertIs(durable['addons'][aid].get('enabled_before'), enabled)
                    self.assertEqual(self.kodi_requests, [{'jsonrpc':'2.0', 'id':1, 'method':'Addons.GetAddonDetails', 'params':{'addonid':aid, 'properties':['enabled']}}])
                finally:
                    self.m.cancel(plan)

    def test_unknown_installer_enabled_state_refuses_without_replacing_code(self):
        for value in (None, 0, 1, 'true', 'false'):
            with self.subTest(value=value):
                aid = self.bundled_installer()
                self.enabled_before = value
                before = self.tree(aid)
                with self.assertRaises(self.m.UpdateError): fixture.InPlace.prepare(self)
                self.assertEqual(self.tree(aid), before)
                self.old_marker()
                self.assertFalse((self.home/'addons/.blacklanturn-update').exists())

    def test_retained_newer_or_identical_installer_does_not_query_enabled_state(self):
        for identical in (False, True):
            with self.subTest(identical=identical):
                aid = self.bundled_installer(installed='1.0.34', bundled='1.0.34' if identical else '1.0.33')
                if identical:
                    prefix = 'addons/'+aid+'/'
                    self.data = {name:raw for name,raw in self.data.items() if not name.startswith(prefix)}
                    self.data.update({prefix+name:raw for name,raw in self.tree(aid).items()})
                plan = self.prepare()
                try:
                    self.assertIn(aid, plan['retained'])
                    self.assertNotIn(aid, plan['state']['addons'])
                    self.assertEqual(self.kodi_requests, [])
                finally:
                    self.m.cancel(plan)

    def recover_with(self, callback):
        try:
            return self.m.recover(self.home, before_recover=callback)
        except TypeError as exc:
            self.fail('Recovery cannot preserve registration before removing its journal: '+str(exc))

    def test_recovery_callback_saves_journal_before_cleanup_under_exclusive_lock(self):
        plan = self.prepare()
        work = Path(plan['work'])
        expected = (work/'journal.json').read_bytes()
        self.m.release(plan)
        saved = self.root/'pending-registration.json'
        def snapshot():
            saved.write_bytes((work/'journal.json').read_bytes())
            with self.assertRaises(self.m.UpdateBusy): self.m._lock(self.home)
        self.assertTrue(self.recover_with(snapshot))
        self.assertEqual(saved.read_bytes(), expected)
        self.assertFalse(work.exists())

    def test_recovery_callback_failure_keeps_journal_and_releases_lock_for_retry(self):
        plan = self.prepare()
        work = Path(plan['work'])
        expected = (work/'journal.json').read_bytes()
        self.m.release(plan)
        def fail_snapshot():
            raise RuntimeError('pending registration could not be saved')
        with self.assertRaises(self.m.UpdateError): self.recover_with(fail_snapshot)
        self.assertEqual((work/'journal.json').read_bytes(), expected)
        self.assertTrue(self.m.recover(self.home))

    def test_busy_recovery_does_not_run_registration_snapshot_callback(self):
        plan = self.prepare()
        snapshots = []
        try:
            with self.assertRaises(self.m.UpdateBusy): self.recover_with(lambda: snapshots.append('saved'))
            self.assertEqual(snapshots, [])
        finally:
            self.m.cancel(plan)

    def test_installer_is_replaced_after_every_other_tree_regardless_of_archive_order(self):
        aid = self.bundled_installer()
        extra = 'zzz.last.addon'
        self.seed(extra, '1')
        self.data['addons/'+extra+'/addon.xml'] = meta(extra, '2')
        self.data['addons/'+extra+'/new.py'] = b'new'
        plan = self.prepare()
        moved = []
        real = os.replace
        def record(src, dst):
            if Path(src).parent == Path(plan['work'])/'new': moved.append(Path(src).name)
            return real(src, dst)
        with patch.object(self.m.os, 'replace', side_effect=record):
            self.m.apply(plan)
        self.assertEqual(moved, ['script.module.bundled', extra, aid])

    def test_installer_rename_failure_restores_every_tree_and_release_metadata(self):
        aid = self.bundled_installer()
        before = {a:self.tree(a) for a in (aid, self.aid)}
        plan = self.prepare()
        real = os.replace
        def fail(src, dst):
            if Path(src) == Path(plan['work'])/'new'/aid: raise OSError('installer rename failed')
            return real(src, dst)
        with patch.object(self.m.os, 'replace', side_effect=fail):
            with self.assertRaises(self.m.UpdateError): self.m.apply(plan)
        for a in before: self.assertEqual(self.tree(a), before[a])
        self.old_marker()
        self.assertFalse((self.home/'userdata/blacklanturn-install-complete.json').exists())
        self.assertEqual(self.saved(), self.before)
        self.assertFalse(Path(plan['work']).exists())

    def crash_after_installer_old_move(self):
        aid = self.bundled_installer()
        before = {a:self.tree(a) for a in (aid, self.aid)}
        plan = self.prepare()
        real = os.replace
        def crash(src, dst):
            value = real(src, dst)
            if Path(dst) == Path(plan['work'])/'old'/aid: raise KeyboardInterrupt('process lost after Installer moved')
            return value
        with patch.object(self.m.os, 'replace', side_effect=crash):
            with self.assertRaises(KeyboardInterrupt): self.m.apply(plan)
        self.m.release(plan)
        self.assertFalse((self.home/'addons'/aid).exists())
        return aid, before, plan

    def test_process_loss_recovers_from_independently_loaded_backup_installer(self):
        aid, before, plan = self.crash_after_installer_old_move()
        source = Path(plan['work'])/'old'/aid/'resources/libs/inplace_update.py'
        spec = importlib.util.spec_from_file_location('cold_backup_installer', source)
        cold = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cold)
        self.assertTrue(cold.recover(self.home))
        for a in before: self.assertEqual(self.tree(a), before[a])
        self.old_marker()
        self.assertEqual(self.saved(), self.before)

    def test_recovery_restores_installer_first_and_resumes_if_later_rollback_is_interrupted(self):
        aid, before, plan = self.crash_after_installer_old_move()
        restored = []
        real = os.replace
        def interrupt(src, dst):
            value = real(src, dst)
            if Path(src).parent == Path(plan['work'])/'old':
                restored.append(Path(src).name)
                if Path(src).name != aid: raise KeyboardInterrupt('recovery process lost')
            return value
        with patch.object(self.m.os, 'replace', side_effect=interrupt):
            with self.assertRaises(KeyboardInterrupt): self.m.recover(self.home)
        self.assertEqual(restored[0], aid)
        self.assertEqual(self.tree(aid), before[aid])
        self.assertTrue(self.m.recover(self.home))
        for a in before: self.assertEqual(self.tree(a), before[a])
        self.old_marker()
        self.assertEqual(self.saved(), self.before)
        self.assertFalse(Path(plan['work']).exists())


if __name__ == '__main__': unittest.main()
