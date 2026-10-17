"""A release must contain the exact repaired source and matching managed provider."""
import hashlib,json,unittest,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class RepairedRelease(unittest.TestCase):
 def test_controller_has_reviewed_repair_and_preview_safety(self):
  addon=ROOT/'controller-source/addon'
  self.assertEqual(ET.parse(addon/'addon.xml').getroot().get('version'),'0.1.72')
  self.assertEqual(hashlib.sha256((addon/'live_review.py').read_bytes()).hexdigest(),'19958907b7ee5365864a3aa9b99d16edd3e70dc2cbe0fd58f7ea96ab97476c3c')
  self.assertTrue((addon/'page_ahead.py').is_file())
  manifest=json.loads((ROOT/'controller-source/manifest72.json').read_text())
  self.assertEqual(manifest['controller'],'0.1.72')
  self.assertEqual(manifest['files'],{str(p.relative_to(addon)):hashlib.sha256(p.read_bytes()).hexdigest() for p in addon.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo')})
 def test_managed_provider_and_installer_require_repaired_payload(self):
  source=ROOT/'installer-source/plugin.program.blacklanturninstaller'
  self.assertEqual(ET.parse(source/'addon.xml').getroot().get('version'),'1.0.12')
  manifest=json.loads((source/'resources/managed-helper.json').read_text())
  self.assertEqual(manifest['search_patch'],'search-batch-1')
  path='resources/tmdbhelper/lib/items/directories/tmdb/lists_search.py'
  digest=hashlib.sha256((ROOT/'compatibility/helper-empty-cache/candidate/lists_search.py').read_bytes()).hexdigest()
  self.assertEqual(digest,'3cc1c1165fd57b233b868fb35e4ceca1cf2449a85a44fb5b9f04cde4b6ae2862')
  self.assertEqual(manifest['files'][path],digest)
if __name__=='__main__':unittest.main()
