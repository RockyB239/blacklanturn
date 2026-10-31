"""Startup reads must not load the atomic-write helper dependency tree."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ADDON = Path(__file__).resolve().parents[1] / 'addon'


class StartupTempfileBoundary(unittest.TestCase):
    def test_startup_imports_and_reads_leave_tempfile_unloaded(self):
        # A module-level tempfile import adds random/shutil/compression work to
        # startup even when the existing on-disk data only needs to be read.
        cases = (
            ('installer_recovery', None, 'assert m.recover_installer(path) is False'),
            ('public_rows', {'version': 2, 'scope': 'scope', 'rows': []},
             "assert m.PublicRowSnapshots(path, 'scope').get('missing') is None"),
            ('row_layout', {'version': 1, 'sections': {}},
             "assert m.RowLayouts(path).rows('Home', []) == []"),
            ('title_preferences', {'version': 1, 'titles': {}},
             "assert m.TitlePreferences(path).entries('hide') == []"),
            ('update_notes', None, 'assert m.read_state(path) == {}'),
            ('youtube_saved', {'version': 1, 'scope': 'scope', 'rows': []},
             "assert m.SavedRows(path, 'scope').get() == []"),
        )
        for module, document, action in cases:
            with self.subTest(module=module), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'state'
                if document is not None:
                    path.write_text(json.dumps(document))
                before = path.read_bytes() if path.exists() else None
                code = (
                    'import importlib,sys\n'
                    "assert 'tempfile' not in sys.modules\n"
                    'sys.path.insert(0,sys.argv[1])\n'
                    'm=importlib.import_module(sys.argv[2])\n'
                    'path=sys.argv[3]\n' + action + '\n'
                    "assert 'tempfile' not in sys.modules, 'Startup read imported tempfile'\n"
                )
                result = subprocess.run(
                    [sys.executable, '-I', '-S', '-c', code, str(ADDON), module, str(path)],
                    capture_output=True, text=True, timeout=15,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(path.read_bytes() if path.exists() else None, before)
                self.assertEqual(list(Path(directory).iterdir()), [path] if before is not None else [])


if __name__ == '__main__':
    unittest.main()
