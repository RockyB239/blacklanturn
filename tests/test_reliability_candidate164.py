"""The personal candidate must remain compatible with real managed update checks."""
from pathlib import Path
import copy,hashlib,importlib.util,json,unittest
ROOT=Path(__file__).resolve().parents[1]

def sha(raw):return hashlib.sha256(raw).hexdigest()
def tree(files):return sha(json.dumps(files,sort_keys=True,separators=(',',':')).encode())

class CandidatePolicy(unittest.TestCase):
 def module(self):
  p=ROOT/'tools/build_reliability_candidate164.py'
  self.assertTrue(p.is_file(),'Candidate package integration is missing')
  s=importlib.util.spec_from_file_location('candidate164',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
 def fixture(self):
  files={'addon.xml':b'<addon id="plugin.video.umbrella" version="6.7.99"/>','resources/lib/modules/source_preferences.py':b'original preference code','resources/lib/modules/sources.py':b'original source code','unchanged.py':b'preserved'}
  hashes={n:sha(v) for n,v in files.items()}
  return files,{'version':'6.7.99','files':hashes,'archive_variants':{},'installed_tree_sha256':{'6.7.99':[tree(hashes)]}}
 def test_new_complete_variant_keeps_all_accepted_old_trees(self):
  files,policy=self.fixture();original=copy.deepcopy(policy);overlays={n:b'patched '+files[n] for n in files if n.endswith(('source_preferences.py','sources.py'))}
  result=self.module().extend_policy(policy,files,overlays)
  expected={n:sha(overlays.get(n,v)) for n,v in files.items()}
  self.assertEqual(result['archive_variants']['reliability164'],expected)
  self.assertIn(tree(expected),result['installed_tree_sha256']['6.7.99'])
  self.assertIn(tree(policy['files']),result['installed_tree_sha256']['6.7.99']);self.assertEqual(policy,original)
 def test_unknown_or_partial_source_is_not_relabelled_as_reviewed(self):
  module=self.module();files,policy=self.fixture();overlays={n:b'patched' for n in files if n.endswith(('source_preferences.py','sources.py'))}
  changed=dict(files,**{'unchanged.py':b'foreign code'})
  with self.assertRaises(ValueError):module.extend_policy(policy,changed,overlays)
  with self.assertRaises(ValueError):module.extend_policy(policy,files,{next(iter(overlays)):b'partial patch'})
 def test_qualification_requires_visual_receipts_for_the_actual_candidate_source(self):
  module=self.module();report={'source_sha256':'c'*64};before={'source_sha256':'b'*64};after={'source_sha256':'a'*64}
  result=module.qualify(report,before,after)
  self.assertFalse(result['passed']);self.assertIn('source',' '.join(result['failures']).lower())
 def test_qualification_binds_playback_to_its_actual_entry_point_source(self):
  routes=('Home','Shows','Movies','Shows genre','Movies genre','Shows deep rows','Movies deep rows','Playback return','Options return')
  receipt={'passed':True,'protocol':'blacklanturn-visible-v1','device':'mac','source_sha256':'a'*64,'playback_source_sha256':'b'*64,'profile_scope':'fixture','samples':[dict(route=route,cache='warm',visible_seconds=.3,remote_seconds=.08,visible_cards=4,artwork_visible=True,artwork_reviewed=True,frame_sha256='b'*64) for route in routes for _ in range(3)]}
  result=self.module().qualify({'source_sha256':'a'*64,'playback_source_sha256':'c'*64},receipt,receipt)
  self.assertFalse(result['passed'],'A different playback entry point cannot qualify the package')

if __name__=='__main__':unittest.main()
