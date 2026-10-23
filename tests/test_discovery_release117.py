import copy,importlib.util,json,unittest,zipfile,io
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,ROOT/path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
B=load('discovery_builder','tools/build_release.py');V=load('discovery_verifier','tools/verify_release.py')
CAT=json.loads((ROOT/'installer-source/plugin.program.blacklanturninstaller/resources/discovery-lineup.json').read_text())
class DiscoveryRelease(unittest.TestCase):
 def test_clean_defaults_are_tested_catalogue_with_unrelated_preferences_untouched(self):
  key='userdata/addon_data/script.blacklanturn.preview/rows.json';data={key:b'{"Movies":[],"Shows":[],"Saved":[],"PreviewMode":"manual","custom":42}','userdata/keep':b'keep'}
  fn=getattr(B,'apply_discovery_defaults',None);self.assertTrue(callable(fn));fn(data);cfg=json.loads(data[key])
  for k,v in CAT['defaults'].items():self.assertEqual(cfg[k],v)
  self.assertEqual(cfg['PreviewMode'],'manual');self.assertEqual(cfg['custom'],42);self.assertEqual(data['userdata/keep'],b'keep')
 def inputs(self):return json.loads((ROOT/'controller-source/discovery-native-verification.json').read_text()),json.loads((ROOT/'controller-source/manifest86.json').read_text())
 def test_release_receipt_binds_exact_source_and_mac_only_native_checks(self):
  fn=getattr(V,'verify_discovery_acceptance',None);self.assertTrue(callable(fn),'Missing discovery release gate');fn(*self.inputs())
 def test_changed_component_or_missing_acceptance_cannot_pass(self):
  fn=getattr(V,'verify_discovery_acceptance',None);self.assertTrue(callable(fn),'Missing discovery release gate');receipt,manifest=self.inputs()
  for field in ('next_back_stable_order','vertical_focus','watch_refresh_stable_order_focus','restored_provider_zero_vs_fresh_start','settings_authorizations_preserved'):
   bad=copy.deepcopy(receipt);bad['acceptance'][field]=False
   with self.assertRaises(AssertionError):fn(bad,manifest)
  bad=copy.deepcopy(manifest);bad['files']['discovery_order.py']='0'*64
  with self.assertRaises(AssertionError):fn(receipt,bad)
 def test_remote_platform_claims_are_rejected(self):
  fn=getattr(V,'verify_discovery_acceptance',None);self.assertTrue(callable(fn),'Missing discovery release gate');r,m=self.inputs();r['devices']=['mac','fire']
  with self.assertRaises(AssertionError):fn(r,m)
if __name__=='__main__':unittest.main()

class RollingDiscoveryWindows(unittest.TestCase):
 def test_rolling_rows_keep_refreshing_without_a_rebuild(self):
  from urllib.parse import parse_qs,urlsplit
  for section,label,field,days in [('Movies','Recently released','primary_release_date',365),('Shows','New series','first_air_date',730)]:
   row=next(r for r in CAT['defaults'][section] if r['label']==label);q=parse_qs(urlsplit(row['path']).query)
   self.assertEqual(q[field+'.gte'],['t-'+str(days)])
   self.assertEqual(q[field+'.lte'],['t+0'])
 def test_classics_keep_fixed_historical_boundaries(self):
  from urllib.parse import parse_qs,urlsplit
  for section,label,field in [('Movies','Classics worth revisiting','primary_release_date'),('Shows','Classic TV','first_air_date')]:
   row=next(r for r in CAT['defaults'][section] if r['label']==label)
   self.assertEqual(parse_qs(urlsplit(row['path']).query)[field+'.lte'],['1999-12-31'])
