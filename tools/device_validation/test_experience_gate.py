"""Release acceptance must measure visible usability rather than empty fast lists."""
import copy,importlib.util,unittest
from pathlib import Path

class ExperienceGate(unittest.TestCase):
 def gate(self):
  path=Path(__file__).with_name('experience_gate.py')
  self.assertTrue(path.exists(),'Visible-experience acceptance gate is missing')
  spec=importlib.util.spec_from_file_location('experience_gate',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
 def receipt(self,device='mac'):
  routes=('Home','Shows','Movies','Shows genre','Movies genre','Shows deep rows','Movies deep rows','Playback return','Options return')
  return {'passed':True,'protocol':'blacklanturn-visible-v1','device':device,'source_sha256':'a'*64,'profile_scope':'test-account-scope', 'samples':[dict(route=route,cache='warm',visible_seconds=.3,remote_seconds=.08,visible_cards=4,artwork_visible=True,artwork_reviewed=True,frame_sha256='b'*64) for route in routes for _ in range(3)]}
 def test_equivalent_visible_samples_pass(self):
  r=self.receipt();self.assertTrue(self.gate().compare(r,r)['passed'])
 def test_missing_artwork_cannot_count_as_fast(self):
  before=self.receipt();after=copy.deepcopy(before);after['samples'][0].update(visible_seconds=.001,artwork_visible=False)
  result=self.gate().compare(before,after);self.assertFalse(result['passed']);self.assertIn('artwork',' '.join(result['failures']).lower())
 def test_metadata_only_frame_is_not_accepted(self):
  before=self.receipt();after=copy.deepcopy(before);after['samples'][0]['artwork_reviewed']=False
  self.assertFalse(self.gate().compare(before,after)['passed'])
 def test_deep_row_regression_fails_even_with_fast_home(self):
  before=self.receipt();after=copy.deepcopy(before)
  for s in after['samples']:
   if s['route']=='Shows deep rows':s['visible_seconds']=1.5
  result=self.gate().compare(before,after);self.assertFalse(result['passed']);self.assertIn('Shows deep rows',' '.join(result['failures']))
 def test_remote_lag_is_separate_from_artwork(self):
  before=self.receipt();after=copy.deepcopy(before)
  for s in after['samples']:s['remote_seconds']=.9
  self.assertFalse(self.gate().compare(before,after)['passed'])
 def test_different_devices_accounts_protocols_and_missing_source_fail(self):
  before=self.receipt()
  for change in ({'device':'fire'},{'profile_scope':'other-account'},{'protocol':'other'},{'source_sha256':''}):
   after=copy.deepcopy(before);after.update(change);self.assertFalse(self.gate().compare(before,after)['passed'],change)
 def test_cold_and_failed_samples_are_not_cached_acceptance(self):
  before=self.receipt()
  for change in ({'cache':'cold'},{'visible_cards':0},{'visible_seconds':float('nan')},{'remote_seconds':-1},{'frame_sha256':'x'}):
   after=copy.deepcopy(before);after['samples'][0].update(change);self.assertFalse(self.gate().compare(before,after)['passed'],change)
if __name__=='__main__':unittest.main()
