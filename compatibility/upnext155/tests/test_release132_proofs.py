"""Run against rebuilt full55 archives; old774-proof inputs must fail."""
import hashlib
import json
import os
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET
import zipfile

BASE = Path(__file__).resolve().parents[1]
WORKSPACE = BASE.parents[2]
ARTIFACTS = Path(os.environ.get('UPNEXT132_RELEASE_DIR', str(WORKSPACE / 'work/release155-2026-11-01/packages/artifacts')))


class Release132Proofs(unittest.TestCase):
    def test_both56_editions_bundle_complete132_and_exact782_proofs(self):
        for edition in ('General', 'Apple-TV-Mac'):
            with self.subTest(edition=edition), zipfile.ZipFile(ARTIFACTS / ('BlackLanturn-' + edition + '-Kodi21-1.1.57.zip')) as archive:
                entry = json.loads(archive.read('userdata/blacklanturn-releases.json'))['releases'][0]
                self.assertEqual(len(entry['files']), 782)
                self.assertEqual(ET.fromstring(archive.read('addons/service.upnext/addon.xml')).get('version'), '1.3.2')
                manifest = json.loads((BASE / 'SOURCE-MANIFEST.json').read_text())
                actual = {n[len('addons/service.upnext/'):]: hashlib.sha256(archive.read(n)).hexdigest()
                          for n in archive.namelist() if n.startswith('addons/service.upnext/') and not n.endswith('/')}
                self.assertEqual(actual, manifest['files'])
                self.assertEqual({n[len('addons/service.upnext/'):]: digest for n, digest in entry['files'].items() if n.startswith('addons/service.upnext/')}, manifest['files'])
                self.assertIn('resources/lib/watchtimer.py', actual)
                for name, digest in entry['files'].items():
                    self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(), digest, name)


if __name__ == '__main__': unittest.main()
