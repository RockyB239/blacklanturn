import json
import os
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / 'addon'))
import icon_packs


class IconPackScanning(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.pack = self.root / 'silver'
        self.pack.mkdir()
        self.write_descriptor('silver')
        self.addCleanup(icon_packs.configure, [])

    def write_descriptor(self, directory):
        (self.root / 'blacklanturn-icons.json').write_text(json.dumps({
            'schema': 1,
            'packs': [{'id': 'silver', 'label': 'Silver', 'directory': directory}],
            'icons': [],
        }))

    def test_real_assets_are_registered_without_per_asset_path_stat_calls(self):
        # Reintroducing Path.is_symlink/is_file on each asset restores 2N stats.
        for name in ('home', 'movies', 'shows'):
            (self.pack / (name + '.png')).write_bytes(b'png')
        original_stat = Path.stat
        calls = []

        def counted_stat(path, *args, **kwargs):
            if path.parent == self.pack:
                calls.append(path.name)
            return original_stat(path, *args, **kwargs)

        with patch.object(Path, 'stat', counted_stat):
            icon_packs.configure([self.root])
        self.assertEqual(icon_packs._assets['silver'], {
            name: str(self.pack / (name + '.png')) for name in ('home', 'movies', 'shows')
        })
        self.assertEqual(calls, [], 'Asset enumeration must reuse directory entry metadata')

    def test_only_regular_lowercase_png_files_are_registered(self):
        (self.pack / 'home.png').write_bytes(b'png')
        for name in ('UPPER.png', 'upper.PNG', 'under_score.png', 'photo.jpg'):
            (self.pack / name).write_bytes(b'ignored')
        (self.pack / 'folder.png').mkdir()
        (self.pack / 'linked.png').symlink_to(self.pack / 'home.png')
        (self.pack / 'broken.png').symlink_to(self.root / 'missing')
        outside = self.root / 'outside.png'
        outside.write_bytes(b'outside')
        (self.pack / 'escape.png').symlink_to(outside)
        if hasattr(os, 'mkfifo'):
            os.mkfifo(self.pack / 'pipe.png')
        icon_packs.configure([self.root])
        self.assertEqual(icon_packs._assets['silver'], {'home': str(self.pack / 'home.png')})

    def test_cap_counts_rejected_entries_and_closes_directory(self):
        # The first 255 entries are rejected; only slot 256 may be registered.
        for number in range(255):
            (self.pack / ('%03d.txt' % number)).write_bytes(b'ignored')
        (self.pack / 'included.png').write_bytes(b'png')
        (self.pack / 'later.png').write_bytes(b'png')
        original_scandir = os.scandir
        original_iterdir = Path.iterdir
        closed = []

        @contextmanager
        def ordered_scandir(path):
            with original_scandir(path) as stream:
                entries = sorted(stream, key=lambda entry: entry.name)
                try:
                    yield iter(entries)
                finally:
                    if Path(path) == self.pack:
                        closed.append(True)

        def ordered_iterdir(path):
            return iter(sorted(original_iterdir(path)))

        with patch.object(os, 'scandir', ordered_scandir), patch.object(Path, 'iterdir', ordered_iterdir):
            icon_packs.configure([self.root])
        self.assertEqual(icon_packs._assets['silver'], {'included': str(self.pack / 'included.png')})
        self.assertEqual(closed, [True])

    def test_missing_and_linked_pack_directories_are_not_registered(self):
        for directory in ('missing', 'linked', '../outside'):
            if directory == 'linked':
                (self.root / 'linked').symlink_to(self.pack, target_is_directory=True)
            self.write_descriptor(directory)
            icon_packs.configure([self.root])
            self.assertNotIn('silver', dict(icon_packs.PACK_CHOICES))

    def test_directory_scan_errors_are_not_silently_accepted(self):
        original_scandir = os.scandir
        original_iterdir = Path.iterdir

        def denied_scandir(path):
            if Path(path) == self.pack:
                raise PermissionError('pack unreadable')
            return original_scandir(path)

        def denied_iterdir(path):
            if path == self.pack:
                raise PermissionError('pack unreadable')
            return original_iterdir(path)

        with patch.object(os, 'scandir', denied_scandir), patch.object(Path, 'iterdir', denied_iterdir):
            with self.assertRaises(PermissionError):
                icon_packs.configure([self.root])
        self.assertNotIn('silver', dict(icon_packs.PACK_CHOICES))


if __name__ == '__main__':
    unittest.main()
