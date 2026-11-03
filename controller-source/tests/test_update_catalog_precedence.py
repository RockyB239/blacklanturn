import copy,hashlib,json,time,unittest
from pathlib import Path
from unittest.mock import patch
import test_update_notes_runtime as runtime_tests

class CatalogPrecedence(unittest.TestCase):
 def setUp(self):
  self.h=runtime_tests.HomeUpdatesRuntimeTests();self.h.setUp();self.addCleanup(self.h.doCleanups);self.ui=self.h.ui;self.root=Path(self.h.temp.name);self.profile=self.root/'userdata/addon_data/script.blacklanturn.preview';self.profile.mkdir(parents=True)
  self.ui.home_path=lambda:self.root;self.ui.profile_path=lambda:self.profile
  self.entry=copy.deepcopy(self.h.state['available']);self.old=copy.deepcopy(self.entry)
  self.old['files']['addons/script.skinvariables/addon.xml']=hashlib.sha256(b'old stock version').hexdigest()
  stock=self.root/'addons/script.skinvariables/addon.xml';stock.parent.mkdir(parents=True);stock.write_bytes(b'newer stock version')
  (self.root/'userdata/blacklanturn-releases.json').write_text(json.dumps({'schema':1,'releases':[self.old]}))
  self.marker={'schema':3,'edition':'apple','build_version':'1.1.20','release_revision':0};(self.root/'userdata/blacklanturn-build.json').write_text(json.dumps(self.marker))
  (self.root/'userdata/blacklanturn-install-complete.json').write_text(json.dumps({'schema':1,'id':self.entry['id'],'edition':'apple','version':'1.1.20','revision':0,'complete':True}))
  self.h.state['seen']=['available:prior'];self.h.state['enabled']=False;self.ui.releases.write_state(self.h.path,self.h.state)
 def cache(self,source=None):
  (self.profile/'release-catalog-cache.json').write_text(json.dumps({'source':source or self.ui.catalog_source(),'fetched':time.time(),'catalog':{'schema':1,'releases':[self.entry]}}))
 def test_cached_operational_proofs_override_same_id_bundled_archive_proofs(self):
  self.cache()
  with patch.object(self.ui.releases,'fetch_catalog',side_effect=AssertionError('Fresh cache must not fetch')):state=self.ui.sample()
  self.assertEqual(state['installed']['version'],'1.1.20');self.assertEqual(state['completed']['files'],self.entry['files']);self.assertIsNone(state['available']);self.assertFalse(state['enabled']);self.assertIn('available:prior',state['seen'])
 def test_managed_file_tampering_still_prevents_completion(self):
  self.cache();(self.root/'addons/example/main.py').write_text('not the accepted patch')
  state=self.ui.sample();self.assertEqual(state['installed']['version'],'1.1.19');self.assertIsNone(state['completed'])
 def test_wrong_feed_cache_cannot_replace_bundled_proofs(self):
  self.cache('https://unrelated.invalid/feed')
  with patch.object(self.ui.releases,'fetch_catalog',side_effect=OSError('offline')):state=self.ui.sample()
  self.assertEqual(state['installed']['version'],'1.1.19');self.assertIsNone(state['completed'])
 def test_offline_bundled_only_still_verifies_matching_release(self):
  (self.root/'addons/script.skinvariables/addon.xml').write_bytes(b'old stock version')
  with patch.object(self.ui.releases,'fetch_catalog',side_effect=OSError('offline')):state=self.ui.sample()
  self.assertEqual(state['installed']['version'],'1.1.20');self.assertEqual(state['completed']['files'],self.old['files'])
