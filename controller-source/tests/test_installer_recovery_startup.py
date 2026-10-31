"""Keep ordinary startup light while retaining recovery path safety checks."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parents[1]/'addon/installer_recovery.py'


class RecoveryStartup(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)/'home'
        (self.home/'addons').mkdir(parents=True)
        spec = importlib.util.spec_from_file_location('recovery_startup_test', SOURCE)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def test_ordinary_startup_does_not_load_recovery_parsers(self):
        # A fresh process catches import cost even when other tests use JSON/XML.
        result = subprocess.run(
            [sys.executable, '-c', '''
import sys
sys.path.insert(0, sys.argv[1])
import installer_recovery
assert installer_recovery.recover_installer(sys.argv[2]) is False
print(','.join(name for name in ('json', 'xml.etree.ElementTree') if name in sys.modules))
''', str(SOURCE.parent), str(self.home)],
            capture_output=True, text=True, check=True,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
        self.assertEqual(result.stdout.strip(), '', 'Ordinary startup loaded recovery-only parsers')
        self.assertEqual(list((self.home/'addons').iterdir()), [])

    def test_dangling_recovery_paths_are_still_refused(self):
        for name in ('.blacklanturn-update', '.blacklanturn-installer-registration.json'):
            with self.subTest(name=name):
                link = self.home/'addons'/name
                link.symlink_to(self.home/'missing')
                try:
                    with self.assertRaises(self.module.RecoveryError):
                        self.module.recover_installer(self.home)
                    self.assertTrue(link.is_symlink())
                finally:
                    link.unlink()

    def test_malformed_installer_xml_keeps_pending_registration(self):
        pending = self.home/'addons/.blacklanturn-installer-registration.json'
        pending.write_text('{"schema":1,"addon":"plugin.program.blacklanturninstaller","enabled":true}')
        addon = self.home/'addons/plugin.program.blacklanturninstaller'
        addon.mkdir()
        (addon/'addon.xml').write_text('<addon')
        original = pending.read_bytes()
        with self.assertRaises(self.module.RecoveryError):
            self.module.recover_installer(self.home, kodi=object())
        self.assertEqual(pending.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
