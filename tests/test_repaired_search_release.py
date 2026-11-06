"""A release must contain the exact repaired source and matching managed provider."""
import hashlib,json,unittest,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class RepairedRelease(unittest.TestCase):
 def test_controller_has_reviewed_repair_and_preview_safety(self):
  addon=ROOT/'controller-source/addon'
  self.assertEqual(ET.parse(addon/'addon.xml').getroot().get('version'),'0.1.130')
  self.assertTrue((addon/'page_ahead.py').is_file())
  manifest=json.loads((ROOT/'controller-source/manifest122.json').read_text())
  self.assertEqual(manifest['controller'],'0.1.122')
  from tools.build_release165 import frozen_inventory
  self.assertEqual(manifest['files'],{name:hashlib.sha256(raw).hexdigest() for name,raw in frozen_inventory('controller-source/addon').items()})
 def test_managed_provider_and_installer_require_repaired_payload(self):
  source=ROOT/'installer-source/plugin.program.blacklanturninstaller'
  self.assertEqual(ET.parse(source/'addon.xml').getroot().get('version'),'1.0.55')
  manifest=json.loads((source/'resources/managed-helper.json').read_text())
  self.assertEqual(manifest['search_patch'],'search-batch-1')
  path='resources/tmdbhelper/lib/items/directories/tmdb/lists_search.py'
  digest=hashlib.sha256((ROOT/'compatibility/helper-empty-cache/candidate/lists_search.py').read_bytes()).hexdigest()
  self.assertEqual(digest,'3cc1c1165fd57b233b868fb35e4ceca1cf2449a85a44fb5b9f04cde4b6ae2862')
  current=json.loads((ROOT/'compatibility/addons151/manifest.json').read_text())['addons']['plugin.video.themoviedb.helper']
  self.assertEqual(manifest['files'][path],current['files'][path])
if __name__=='__main__':unittest.main()
