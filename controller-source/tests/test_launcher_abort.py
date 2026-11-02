"""Real launcher behavior against Kodi 21.3's per-instance abort-event contract.

The unavailable Kodi native boundary is represented by a weak callback registry:
new Monitors start unset and only existing instances receive an abort broadcast.
This follows a3a448d26b Monitor.cpp:20/31/58 and XBPython.cpp:277/540.
The launcher and CoreSettingsReturn gate are executed unchanged from disk.
"""
import json
import os
from pathlib import Path
import runpy
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import weakref

BASE = Path(__file__).resolve().parents[1] / 'addon'
SOURCE = Path(os.environ.get('BL_LAUNCHER_SOURCE', str(BASE / 'default.py'))).resolve()


class HostAbortBoundary:
    def __init__(self):
        self.callbacks = weakref.WeakSet()

    def Monitor(self):
        callbacks = self.callbacks

        class PerInstanceMonitor:
            def __init__(self):
                self.event = threading.Event()
                callbacks.add(self)

            def abortRequested(self):
                return self.event.is_set()

            def waitForAbort(self, timeout):
                return self.event.wait(timeout)

        return PerInstanceMonitor()

    def notify_abort(self):
        for callback in list(self.callbacks):
            callback.event.set()


class GuiReadAfterAbortBudget(BaseException):
    pass


class LauncherAbortContract(unittest.TestCase):
    def run_launcher(self, request=None, playback=None, abort_in_modal=False,
                     abort_while_away=False, return_normally=False):
        host = HostAbortBoundary()
        observed = {'dispatch': [], 'players': [], 'windows': [], 'gui_reads': 0,
                    'sleep_calls': 0, 'returned': False}
        props = {'BlackLanturn.Preview.Running': '1'}
        home = SimpleNamespace(getProperty=lambda key: props.get(key, ''),
                               setProperty=props.__setitem__,
                               clearProperty=lambda key: props.pop(key, None))

        class Review:
            def __init__(self, *args):
                self.core_settings_request = request if not observed['windows'] else None
                self.playback_request = playback if not observed['windows'] else None
                self.playback_return = None
                self.playback_options = {}
                observed['windows'].append(self)

            def doModal(self):
                if abort_in_modal:
                    host.notify_abort()

        def read_window():
            observed['gui_reads'] += 1
            if observed['gui_reads'] > 3:
                raise GuiReadAfterAbortBudget()
            if return_normally and observed['gui_reads'] >= 2:
                return 10000
            return 10016

        def sleep(milliseconds):
            self.assertEqual(milliseconds, 100)
            observed['sleep_calls'] += 1
            if abort_while_away and observed['sleep_calls'] == 1:
                host.notify_abort()

        def play(*args, **kwargs):
            observed['players'].append(args)
            return False

        with tempfile.TemporaryDirectory(prefix='bl-abort-contract-') as scratch:
            kodi = SimpleNamespace(Monitor=host.Monitor,
                                   getSkinDir=lambda: 'skin.blacklanturn.preview',
                                   executebuiltin=lambda command: observed['dispatch'].append(command),
                                   executeJSONRPC=lambda raw: observed['dispatch'].append(json.loads(raw)),
                                   sleep=sleep)
            native = {'xbmc': kodi,
                      'xbmcgui': SimpleNamespace(Window=lambda window: home,
                                                 getCurrentWindowId=read_window,
                                                 Dialog=lambda: SimpleNamespace(notification=lambda *a: None)),
                      'xbmcvfs': SimpleNamespace(translatePath=lambda path: scratch),
                      'xbmcaddon': SimpleNamespace(Addon=lambda addon: SimpleNamespace(getAddonInfo=lambda key: scratch)),
                      'live_runtime': SimpleNamespace(validate_paths=lambda *a: Path(scratch), SkinStartupGate=object),
                      'installer_recovery': SimpleNamespace(recover_installer=lambda *a: False, RecoveryError=type('RecoveryError', (Exception,), {})),
                      'live_review': SimpleNamespace(LiveReview=Review),
                      'playback_runtime': SimpleNamespace(play_and_wait=play)}
            with patch.dict(sys.modules, native), patch.object(sys, 'argv', ['default.py']), patch.object(sys, 'path', list(sys.path)):
                sys.path.insert(0, str(BASE))
                entry = runpy.run_path(str(SOURCE))
                try:
                    entry['run_live_review']()
                except GuiReadAfterAbortBudget:
                    pass
                else:
                    observed['returned'] = True
        return observed

    def test_backend_wait_observes_abort_delivered_between_poll_checks(self):
        """A quit while away in PlayerSettings must not poll a stopped GUI forever."""
        observed = self.run_launcher(request={'target': 'PlayerSettings', 'category': 0, 'row': 0},
                                     abort_while_away=True)
        self.assertTrue(observed['returned'], 'Launcher kept polling the backend after host abort')
        self.assertEqual(observed['gui_reads'], 1)
        self.assertEqual(len(observed['windows']), 1)

    def test_modal_abort_does_not_activate_a_pending_settings_request(self):
        observed = self.run_launcher(request={'target': 'PlayerSettings', 'category': 0, 'row': 0},
                                     abort_in_modal=True)
        self.assertEqual(observed['dispatch'], [], 'Launcher activated settings after shutdown')
        self.assertTrue(observed['returned'])

    def test_modal_abort_does_not_start_pending_provider_playback(self):
        observed = self.run_launcher(playback='plugin://plugin.video.example/?play=1', abort_in_modal=True)
        self.assertEqual(observed['players'], [], 'Launcher started provider playback after shutdown')
        self.assertTrue(observed['returned'])

    def test_ordinary_backend_return_reopens_the_existing_selection(self):
        request = {'target': 'PlayerSettings', 'category': 4, 'row': 1, 'section': 'Movies'}
        observed = self.run_launcher(request=request, return_normally=True)
        self.assertTrue(observed['returned'])
        self.assertEqual(observed['dispatch'], ['ActivateWindow(PlayerSettings)'])
        self.assertEqual(len(observed['windows']), 2)
        self.assertEqual(observed['windows'][1].resume_backend, request)


if __name__ == '__main__':
    unittest.main(verbosity=2)
