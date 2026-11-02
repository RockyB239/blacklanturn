"""Actual Umbrella main/SettingsMonitor against Kodi's instance abort contract.

Startup network/account operations and thread scheduling are unavailable native
boundaries. The real main and real SettingsMonitor class execute from disk.
"""
import ast
import os
from pathlib import Path
import threading
from types import SimpleNamespace
import unittest
import weakref

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'compatibility/menus156/umbrella/service.py'
SOURCE = Path(os.environ.get('BL_UMBRELLA_SERVICE', str(BASE)))


class UnsignaledInfiniteWait(BaseException):
    pass


class StartupAbort(unittest.TestCase):
    def run_main(self, abort_during=None, already_aborted=False):
        callbacks = weakref.WeakSet()
        observed = {'work': [], 'starts': [], 'joins': [], 'wait_blocked': False,
                    'returned': False}

        def abort():
            for callback in list(callbacks):
                callback.event.set()

        class NativeMonitor:
            def __init__(self):
                self.event = threading.Event()
                # Abort may arrive after allocation but before registration.
                # Existing control.monitor gets it; this instance cannot replay it.
                if self.__class__.__name__ == 'SettingsMonitor' and abort_during == 'SettingsMonitorConstruction':
                    abort()
                callbacks.add(self)

            def abortRequested(self):
                return self.event.is_set()

            def waitForAbort(self, timeout=0):
                if abort_during is None and not already_aborted:
                    abort()  # A normal run receives shutdown after startup.
                if not self.event.is_set():
                    observed['wait_blocked'] = True
                    raise UnsignaledInfiniteWait()
                return True

        class Worker:
            def __init__(self, target, daemon=False):
                self.name = target.__self__.__class__.__name__

            def start(self):
                observed['starts'].append(self.name)
                if abort_during == 'thread:' + self.name:
                    abort()

            def join(self, timeout=None):
                observed['joins'].append((self.name, timeout))

        def stage(name):
            def run(self):
                observed['work'].append(name)
                if abort_during == name:
                    abort()
            return type(name, (), {'run': run})

        control = SimpleNamespace(monitor_class=NativeMonitor, monitor=NativeMonitor(),
                                  refresh_playAction=lambda: None, refresh_libPath=lambda: None,
                                  setting=lambda key: 'true' if key in ('library.service.update', 'general.checkAddonUpdates') else '',
                                  log=lambda *args: None)
        window = SimpleNamespace(setProperty=lambda *args: None, clearProperty=lambda *args: None)
        namespace = {'control': control, 'window': window, 'LOGINFO': 1, 'LOGDEBUG': 0,
                     'Thread': Worker}
        for name in ('CheckSettingsFile', 'SyncMyAccounts', 'PremAccntNotification',
                     'ReuseLanguageInvokerCheck', 'LibraryService', 'AddonCheckUpdate',
                     'VersionIsUpdateCheck', 'checkAutoStart', 'SyncServices'):
            namespace[name] = stage(name)
        source = ast.parse(SOURCE.read_text())
        nodes = [node for node in source.body
                 if (isinstance(node, ast.ClassDef) and node.name == 'SettingsMonitor')
                 or (isinstance(node, ast.FunctionDef) and node.name == 'main')
                 or (isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'properties' for target in node.targets))]
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE), 'exec'), namespace)
        if already_aborted:
            abort()
        try:
            namespace['main']()
        except UnsignaledInfiniteWait:
            pass
        else:
            observed['returned'] = True
        return observed

    def test_abort_during_account_sync_finishes_without_later_startup_work(self):
        observed = self.run_main(abort_during='SyncMyAccounts')
        self.assertTrue(observed['returned'], 'Startup created a fresh unset Monitor and waited after abort')
        self.assertEqual(observed['work'], ['CheckSettingsFile', 'SyncMyAccounts'])
        self.assertEqual(observed['starts'], [])

    def test_abort_during_premium_account_setup_finishes_without_late_threads(self):
        observed = self.run_main(abort_during='PremAccntNotification')
        self.assertTrue(observed['returned'], 'Premium startup lost abort before its keep-alive wait')
        self.assertEqual(observed['work'], ['CheckSettingsFile', 'SyncMyAccounts', 'PremAccntNotification'])
        self.assertEqual(observed['starts'], [])

    def test_abort_during_settings_file_setup_starts_no_account_work(self):
        observed = self.run_main(abort_during='CheckSettingsFile')
        self.assertTrue(observed['returned'])
        self.assertEqual(observed['work'], ['CheckSettingsFile'])
        self.assertEqual(observed['starts'], [])

    def test_abort_before_entry_does_not_wait_or_start_service_work(self):
        observed = self.run_main(already_aborted=True)
        self.assertTrue(observed['returned'])
        self.assertEqual(observed['work'], [])
        self.assertEqual(observed['starts'], [])

    def test_abort_after_library_launch_starts_no_update_or_account_worker(self):
        observed = self.run_main(abort_during='thread:LibraryService')
        self.assertTrue(observed['returned'])
        self.assertEqual(observed['work'], ['CheckSettingsFile', 'SyncMyAccounts', 'PremAccntNotification', 'ReuseLanguageInvokerCheck'])
        self.assertEqual(observed['starts'], ['LibraryService'])
        self.assertEqual(observed['joins'], [('LibraryService', 2)])

    def test_abort_during_settings_monitor_construction_cannot_enter_unset_wait(self):
        observed = self.run_main(abort_during='SettingsMonitorConstruction')
        self.assertTrue(observed['returned'], 'Late monitor registration lost an already-delivered abort')
        self.assertFalse(observed['wait_blocked'])

    def test_ordinary_startup_keeps_all_tasks_and_bounded_worker_cleanup(self):
        observed = self.run_main()
        self.assertTrue(observed['returned'])
        self.assertFalse(observed['wait_blocked'])
        self.assertEqual(observed['work'], ['CheckSettingsFile', 'SyncMyAccounts', 'PremAccntNotification',
                                          'ReuseLanguageInvokerCheck', 'AddonCheckUpdate',
                                          'VersionIsUpdateCheck', 'checkAutoStart'])
        self.assertEqual(observed['starts'], ['LibraryService', 'SyncServices'])
        self.assertEqual(observed['joins'], [('SyncServices', 2), ('LibraryService', 2)])


if __name__ == '__main__':
    unittest.main(verbosity=2)
