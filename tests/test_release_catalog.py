import hashlib,importlib.util,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('catalog_builder',ROOT/'tools/build_release.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
class ReleaseCatalog(unittest.TestCase):
 def test_catalog_is_derived_from_exact_package_and_excludes_personal_files(self):
  fn=getattr(b,'release_entry',None);self.assertTrue(callable(fn),'Builder does not emit curated release metadata')
  data={n:b'code' for n in b.RELEASE_PROOFS};data['userdata/blacklanturn-build.json']=json.dumps({'edition':'general','build_version':'1.1.20','release_id':'blacklanturn-general-1.1.20-r0','release_revision':0}).encode();data['userdata/addon_data/plugin.video.youtube/access_manager.json']=b'private'
  entry=fn(data,'General');self.assertEqual(entry['id'],'blacklanturn-general-1.1.20-r0');self.assertIn('1.1.20',entry['title']);self.assertIn('Important',entry['summary']);self.assertNotIn('private',json.dumps(entry));self.assertEqual(entry['files']['addons/script.blacklanturn.preview/filtered_pages.py'],hashlib.sha256(b'code').hexdigest())
  self.assertTrue(all(n.startswith('addons/') for n in entry['files']));data['addons/script.blacklanturn.preview/filtered_pages.py']=b'changed';self.assertNotEqual(entry['files'],fn(data,'General')['files'])
 def test_missing_required_proof_or_wrong_edition_refuses_catalog(self):
  fn=getattr(b,'release_entry',None);self.assertTrue(callable(fn),'Builder does not emit curated release metadata')
  with self.assertRaises((ValueError,KeyError)):fn({},'General')
  with self.assertRaises(ValueError):fn({},'Unknown')
