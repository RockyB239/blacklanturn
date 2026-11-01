"""Public132 input/compatibility contracts; no Kodi, network or personal data."""
import ast
from datetime import datetime
import os
from pathlib import Path
import unittest
import types
import xml.etree.ElementTree as ET

ROOT = Path(os.environ.get('UPNEXT132_SOURCE', str(Path(__file__).resolve().parents[1] / 'source/service.upnext')))


class UpNext132(unittest.TestCase):
    def timer(self):
        path = ROOT / 'resources/lib/watchtimer.py'
        self.assertTrue(path.is_file(), 'Official132 watch timer must be part of the complete source tree')
        module = types.ModuleType('upstream132_watchtimer')
        exec(compile(path.read_bytes(), str(path), 'exec'), module.__dict__)
        return module.WatchTimer()

    def test_official132_metadata_keeps_kodi21_python_service_contract(self):
        root = ET.parse(ROOT / 'addon.xml').getroot()
        self.assertEqual(root.get('id'), 'service.upnext')
        self.assertEqual(root.get('version'), '1.3.2')
        self.assertEqual(root.get('provider-name'), 'im85288')
        self.assertEqual([n.attrib for n in root.findall('./requires/import')], [{'addon': 'xbmc.python', 'version': '3.0.0'}])
        service = root.find("extension[@point='xbmc.service']")
        self.assertIsNotNone(service)
        self.assertTrue((ROOT / service.get('library')).is_file())

    def test_new_optional_behaviors_default_off_and_keep_public_defaults(self):
        settings = {n.get('id'): n.get('default', n.findtext('default')) for n in ET.parse(ROOT / 'resources/settings.xml').getroot().iter('setting') if n.get('id')}
        expected = {'selectOpensPlaybackControls': 'false', 'stillWatchingMinutes': '0',
                    'bedtimeEnabled': 'false', 'bedtimeHour': '23', 'bedtimeMinute': '0'}
        self.assertEqual({k: settings.get(k) for k in expected}, expected)

    def test_watch_timer_counts_progress_and_excludes_pauses_seeks_and_file_switches(self):
        timer = self.timer()
        for now, position in [(0, 0), (1, 1), (2, 2)]: timer.observe('episode-a', position, now=now)
        self.assertEqual(timer.elapsed, 2)
        timer.observe('episode-a', 90, now=3)  # Seek is not watched time.
        timer.observe('episode-a', 90, paused=True, now=20)
        timer.observe('episode-a', 91, now=30)
        timer.observe('episode-b', 0, now=31)
        self.assertEqual(timer.elapsed, 2)
        timer.observe('episode-b', 1, now=32)
        self.assertEqual(timer.elapsed, 3)

    def test_watch_limit_is_inert_by_default_and_due_only_when_enabled(self):
        timer = self.timer(); timer.elapsed = 60
        now = datetime(2026, 11, 1, 12)
        self.assertFalse(timer.due(0, False, 23, 0, now=now))
        self.assertTrue(timer.due(1, False, 23, 0, now=now))
        timer.reset(); self.assertFalse(timer.due(1, False, 23, 0, now=now))

    def test_optional_bedtime_acknowledgement_does_not_repeat_until_next_night(self):
        timer = self.timer()
        self.assertFalse(timer.due(0, True, 23, 0, now=datetime(2026, 11, 1, 22, 59)))
        self.assertTrue(timer.due(0, True, 23, 0, now=datetime(2026, 11, 1, 23, 1)))
        timer.reset(acknowledge_bedtime=True)
        self.assertFalse(timer.due(0, True, 23, 0, now=datetime(2026, 11, 1, 23, 2)))
        self.assertTrue(timer.due(0, True, 23, 0, now=datetime(2026, 11, 2, 23, 1)))

    def test_optional_controls_support_existing_direct_watch_now3012_skin_contract(self):
        tree = ast.parse((ROOT / 'resources/lib/upnext.py').read_text())
        methods = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'prepare_playback_controls']
        self.assertEqual(len(methods), 1, 'Official132 must preserve its explicit custom-skin fallback')
        calls = []; target = object()
        class Button:
            def __init__(self, *args, **kwargs): calls.append(('button', args[:4]))
            def setNavigation(self, *args): calls.append(('nav', args))
        class Window:
            def getControl(self, cid):
                calls.append(('control', cid))
                if cid == 20: raise RuntimeError('This skin uses direct buttons')
                if cid == 3012: return target
                raise AssertionError(cid)
            def addControl(self, control): calls.append(('added', control))
            def setFocus(self, control): calls.append(('focused', control))
        ns = {'ControlButton': Button}
        exec(compile(ast.fix_missing_locations(ast.Module(body=methods, type_ignores=[])), 'upstream132-controls', 'exec'), ns)
        window = Window(); ns['prepare_playback_controls'](window)
        self.assertEqual([n for n in calls if n[0] == 'control'], [('control', 20), ('control', 3012)])
        self.assertIn(('button', (-1000, -1000, 1, 1)), calls)
        self.assertIn(('nav', (target, target, target, target)), calls)
        self.assertIs(calls[-1][1], window.playback_control)

    def test_all_official_python_sources_compile_without_kodi_imports(self):
        paths = list(ROOT.rglob('*.py')); self.assertGreaterEqual(len(paths), 15)
        for path in paths:
            with self.subTest(path=str(path.relative_to(ROOT))): compile(path.read_bytes(), str(path), 'exec')


if __name__ == '__main__': unittest.main()
