import subprocess
import tempfile
import unittest
from pathlib import Path

LAUNCHER = Path(__file__).parents[1] / 'Launch-BlackLanturn-Test.command'


class TestLauncher(unittest.TestCase):
    def launch_fixture(self, status):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            launcher = root / LAUNCHER.name
            process_list = root / 'process-list'
            process_list.write_text('#!/bin/sh\nprintf "%s\\n" /usr/bin/fixture\n')
            process_list.chmod(0o755)
            launcher.write_text(LAUNCHER.read_text().replace('/bin/ps -axo comm=', '"' + str(process_list) + '"'))
            binary = root / 'BlackLanturn-Test.app/Contents/MacOS/Kodi'
            binary.parent.mkdir(parents=True)
            (root / 'evidence').mkdir()
            binary.write_text('#!/bin/sh\nprintf "argument=%s\\n" "$1"\nexit ' + str(status) + '\n')
            binary.chmod(0o755)
            result = subprocess.run(['/bin/zsh', str(launcher)], capture_output=True, text=True)
            return result, (root / 'evidence/startup-console.log').read_text()

    def test_failed_start_explains_status_and_log_without_losing_exit_code(self):
        result, log = self.launch_fixture(137)
        self.assertEqual(result.returncode, 137)
        self.assertIn('137', result.stderr)
        self.assertIn('startup-console.log', result.stderr)
        self.assertIn('signature', result.stderr.lower())
        self.assertEqual(log, 'argument=-p\n')

    def test_success_stays_quiet_and_uses_portable_profile(self):
        result, log = self.launch_fixture(0)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, '')
        self.assertEqual(log, 'argument=-p\n')

    def test_guard_refuses_to_launch_when_kodi_is_running(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            launcher = root / LAUNCHER.name
            process_list = root / 'process-list'
            process_list.write_text('#!/bin/sh\nprintf "%s\\n" /Applications/Kodi.app/Contents/MacOS/Kodi\n')
            process_list.chmod(0o755)
            launcher.write_text(LAUNCHER.read_text().replace('/bin/ps -axo comm=', '"' + str(process_list) + '"'))
            result = subprocess.run(['/bin/zsh', str(launcher)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn('Quit Kodi normally', result.stdout)
            self.assertFalse((root / 'evidence').exists())

    def test_guard_refuses_to_launch_when_process_list_is_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            launcher = root / LAUNCHER.name
            process_list = root / 'process-list'
            process_list.write_text('#!/bin/sh\nexit 1\n')
            process_list.chmod(0o755)
            launcher.write_text(LAUNCHER.read_text().replace('/bin/ps -axo comm=', '"' + str(process_list) + '"'))
            result = subprocess.run(['/bin/zsh', str(launcher)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn('Cannot check', result.stderr)
            self.assertFalse((root / 'evidence').exists())
