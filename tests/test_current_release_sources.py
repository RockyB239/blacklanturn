"""Current-source packaging gates; historical source fixtures stay historical."""
import copy,hashlib,importlib.util,json,tempfile,unittest,xml.etree.ElementTree as ET,zipfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('current_build',ROOT/'tools/build_release.py');BUILD=importlib.util.module_from_spec(spec);spec.loader.exec_module(BUILD)
EXPECTED={'plugin.video.themoviedb.helper':('1:6.18.2+blacklanturn.1',497),'plugin.video.umbrella':('1:6.7.97+blacklanturn.1',1686),'script.module.infotagger':('0.1.0',4),'script.module.cocoscrapers':('1.0.45',None),'script.skinvariables':('2.2.10',None),'resource.language.en_us':('11.0.84',4),'script.module.inputstreamhelper':('0.8.6',None)}
class CurrentReleaseSources(unittest.TestCase):
 def test_complete_current_addons_replace_stale_source_only(self):
  self.assertTrue(callable(getattr(BUILD,'apply_current_addons',None)),'Missing complete pinned current add-on packaging')
  data={'userdata/addon_data/plugin.video.umbrella/settings.xml':b'private fixture','addons/unrelated/file':b'keep'}
  data.update({'addons/'+aid+'/obsolete.py':b'stale' for aid in EXPECTED})
  BUILD.apply_current_addons(data)
  manifest=json.loads((ROOT/'compatibility/current-addons/manifest.json').read_text())['addons']
  for aid,(version,count) in EXPECTED.items():
   prefix='addons/'+aid+'/';files={n[len(prefix):]:raw for n,raw in data.items() if n.startswith(prefix)}
   self.assertEqual(ET.fromstring(files['addon.xml']).get('version'),version)
   if count:self.assertEqual(len(files),count)
   self.assertEqual({n:BUILD.sha(raw) for n,raw in files.items()},manifest[aid]['files'])
   self.assertNotIn('obsolete.py',files)
  self.assertEqual(data['userdata/addon_data/plugin.video.umbrella/settings.xml'],b'private fixture')
  self.assertEqual(data['addons/unrelated/file'],b'keep')
  helper=ET.fromstring(data['addons/plugin.video.themoviedb.helper/addon.xml'])
  deps={n.get('addon'):n.get('version') for n in helper.findall('./requires/import')}
  self.assertEqual(deps['xbmc.python'],'3.0.1');self.assertEqual(deps['script.module.infotagger'],'0.1.0')
 def test_current_addon_settings_schema_supports_every_curated_default(self):
  data={};BUILD.apply_current_addons(data)
  defaults=json.loads((ROOT/'installer-source/plugin.program.blacklanturninstaller/resources/playback-defaults.json').read_text())
  for name,fields in defaults.items():
   if not name.startswith('addon_data/'):continue
   aid=name.split('/')[1];path='addons/'+aid+'/resources/settings.xml'
   if path not in data:continue
   known={n.get('id') for n in ET.fromstring(data[path]).iter('setting')}
   self.assertFalse(set(fields)-known,(aid,'curated settings absent from current upstream',set(fields)-known))
 def test_foreign_archive_fails_atomically(self):
  self.assertTrue(callable(getattr(BUILD,'apply_current_addons',None)),'Missing exact-source pin gate')
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);target=root/'compatibility/current-addons';target.mkdir(parents=True)
   manifest=json.loads((ROOT/'compatibility/current-addons/manifest.json').read_text())
   (target/'manifest.json').write_text(json.dumps(manifest))
   first=next(iter(manifest['addons'].values()));(target/first['archive']).write_bytes(b'foreign')
   data={'userdata/keep':b'original'}
   with patch.object(BUILD,'ROOT',root),self.assertRaisesRegex(ValueError,'archive changed'):BUILD.apply_current_addons(data)
   self.assertEqual(data,{'userdata/keep':b'original'})
 def test_dependency_versions_are_enforced(self):
  self.assertTrue(callable(getattr(BUILD,'verify_dependency_closure',None)),'Missing dependency minimum audit')
  data={'addons/a/addon.xml':b'<addon id="a" version="1.0"><requires><import addon="b" version="2.0"/><import addon="xbmc.python" version="3.0.1"/></requires></addon>','addons/b/addon.xml':b'<addon id="b" version="1.0"/>'}
  with self.assertRaisesRegex(ValueError,'minimum'):BUILD.verify_dependency_closure(data)
  data['addons/b/addon.xml']=b'<addon id="b" version="2.1"/>';BUILD.verify_dependency_closure(data)
 def test_prior_native_receipt_remains_bound_to_historical_sources(self):
  self.assertTrue(callable(getattr(BUILD,'verify_prior_source_acceptance',None)),'Missing current source-bound evidence gate')
  receipt=json.loads((ROOT/'compatibility/current-addons/native-source-verification-6.18.1.json').read_text())
  BUILD.verify_prior_source_acceptance(receipt)
  self.assertEqual(receipt['release_install_acceptance'],False)
  bad=copy.deepcopy(receipt);bad['sources']['plugin.video.themoviedb.helper']['tree_sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'source'):BUILD.verify_prior_source_acceptance(bad)
 def test_current_host_contract_is_exact_and_does_not_claim_fire_acceptance(self):
  receipt=json.loads((ROOT/'compatibility/current-addons/current-source-contract.json').read_text())
  BUILD.verify_current_source_contract(receipt)
  bad=copy.deepcopy(receipt);bad['sources']['plugin.video.themoviedb.helper']['tree_sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'source'):BUILD.verify_current_source_contract(bad)
  bad=copy.deepcopy(receipt);bad['physical_fire_tested']=True
  with self.assertRaisesRegex(ValueError,'scope'):BUILD.verify_current_source_contract(bad)
if __name__=='__main__':unittest.main()
