"""Gate contract tests using sanitized native runs; never device access."""
import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from statistics import median
from unittest.mock import patch
from tools import verify_release
PROTOCOL='cached-native-first-usable-row-v2'
SECTIONS=('Home','Shows','Movies','YouTube','My Stuff')
class NativePerformanceV2(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);original=verify_release.ROOT
  for name in ('controller-source/manifest82.json','controller-source/manifest83.json','controller-source/native-performance-v2-82.json','controller-source/native-performance-v2-83.json','installer-source/plugin.program.blacklanturninstaller/resources/managed-helper.json'):
   path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes((original/name).read_bytes())
  self.manifest=json.loads((self.root/'controller-source/manifest83.json').read_text())
  self.runs={key:json.loads((self.root/f'controller-source/native-performance-v2-{version}.json').read_text()) for key,version in (('before',82),('after',83))}
  self.speed={'protocol':PROTOCOL,'metric':'gui_load_invocation_to_native_control_readiness','before_controller':'0.1.82','after_controller':'0.1.83','native_receipts':{},'sections':{},'max_observation_gap_seconds':{}}
  for role,version in (('before',82),('after',83)):
   path=f'controller-source/native-performance-v2-{version}.json';self.speed['native_receipts'][role]={'path':path,'sha256':hashlib.sha256((self.root/path).read_bytes()).hexdigest()};self.speed['max_observation_gap_seconds'][role]=self.runs[role]['observation']['max_observation_gap_seconds']
  for section in SECTIONS:
   a=[v['first_usable_seconds'] for v in self.runs['before']['visits'] if v['section']==section];b=[v['first_usable_seconds'] for v in self.runs['after']['visits'] if v['section']==section];limit=max(median(a)*.2,.35)
   self.speed['sections'][section]={'before_seconds':a,'after_seconds':b,'before_median':median(a),'after_median':median(b),'allowed_increase_seconds':limit,'within_tolerance':median(b)-median(a)<=limit+1e-9}
  self.patch=patch.object(verify_release,'ROOT',self.root);self.patch.start();self.addCleanup(self.patch.stop)
 def check(self):
  gate=getattr(verify_release,'verify_fire_browsing_v2',None);self.assertTrue(callable(gate),'Missing explicitly versioned v2 native performance gate');return gate(self.speed,self.manifest)
 def store(self,role):
  p=self.root/self.speed['native_receipts'][role]['path'];p.write_text(json.dumps(self.runs[role]));self.speed['native_receipts'][role]['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
 def reject(self,mutate,role='after'):
  self.check()
  original_runs=copy.deepcopy(self.runs);original_speed=copy.deepcopy(self.speed)
  try:
   mutate(self.runs[role]);self.store(role)
   with self.assertRaises(AssertionError):self.check()
  finally:
   self.runs=original_runs;self.speed=original_speed
   for key in self.runs:self.store(key)
 def test_genuine_sanitized_native_runs_pass_with_reported_observation_gaps(self):
  self.check();self.assertAlmostEqual(self.speed['max_observation_gap_seconds']['after'],.7183885380072752)
 def test_public_reference_digest_and_fixed_filenames_are_bound(self):
  self.check()
  original=copy.deepcopy(self.speed)
  for field,value in (('sha256','0'*64),('path','controller-source/manifest83.json')):
   with self.subTest(field=field):
    self.speed=copy.deepcopy(original);self.speed['native_receipts']['after'][field]=value
    with self.assertRaises(AssertionError):self.check()
 def test_current_and_historical_full_source_inventory_and_loaded_versions_required(self):
  for field in ('source_files','helper_files'):
   with self.subTest(field=field):self.reject(lambda r:r[field].pop(next(iter(r[field]))))
  for field,value in (('loaded_version','0.1.82'),('controller','0.1.82'),('source_exact',False),('helper_source_exact',False)):
   with self.subTest(field=field):self.reject(lambda r:r.update({field:value}))
 def test_current_helper_inventory_cannot_replace_missing_historical_inventory(self):
  path=self.root/'installer-source/plugin.program.blacklanturninstaller/resources/managed-helper.json'
  manifest=json.loads(path.read_text())
  self.assertNotEqual(manifest['upstream_version'],'6.17.9')
  self.check()
  del manifest['legacy_files']['6.17.9'];path.write_text(json.dumps(manifest))
  with self.assertRaisesRegex(AssertionError,'historical Helper6.17.9 inventory'):self.check()
 def test_before_source_cannot_claim_current_controller(self):self.reject(lambda r:r['source_files'].update(self.manifest['files']),'before')
 def test_loaded_origins_preservation_and_preview_conditions_required(self):
  for key,value in (('settings_preserved',False),('save_method_restored',False),('completed',False),('measurement_valid',False),('preview_suppression','normal'),('preservation_scope','all personal device/history data'),('loaded_method_origins',{'load_section':'elsewhere.py'})):
   with self.subTest(key=key):self.reject(lambda r:r.update({key:value}))
 def test_all_fifteen_ordered_successful_visits_required(self):
  for change in ('missing','reordered','failed','duplicate'):
   def mutate(r):
    if change=='missing':r['visits'].pop()
    elif change=='reordered':r['visits'][0],r['visits'][1]=r['visits'][1],r['visits'][0]
    elif change=='failed':r['visits'][-1]['passed']=False
    else:r['visits'][-1]=copy.deepcopy(r['visits'][0])
   with self.subTest(change=change):self.reject(mutate)
 def test_arrival_must_be_actual_last_sample_with_first_nonempty_native_row(self):
  for field,value in (('focus',900),('native_count',0),('native_visible',False),('native_path_sha256','0'*64),('data_path_sha256',hashlib.sha256(b'').hexdigest()),('generation',0),('loading',True),('nav',True),('startup_idle',True),('position',999),('row_states',['ready','empty'])):
   def mutate(r):
    v=r['visits'][4];v['arrival'][field]=value;v['samples'][-1][field]=value
   with self.subTest(field=field):self.reject(mutate)
 def test_no_personalized_media_values_or_unhashed_paths_in_public_receipt(self):
  for field in ('native_label','native_path','data_path'):
   def mutate(r):r['visits'][0]['samples'][0][field]='private-value'
   with self.subTest(field=field):self.reject(mutate)
 def test_times_are_finite_positive_and_recomputed_from_native_timestamps(self):
  for value in (True,float('nan'),float('inf'),0,-1,1234):
   with self.subTest(value=value):self.reject(lambda r:r['visits'][0].update(first_usable_seconds=value))
 def test_probe_and_load_timestamps_must_have_gui_dispatch_provenance(self):
  for change in ('generation','outside_dispatch','early_observation','missing_dispatch','wrong_thread'):
   def mutate(r):
    v=r['visits'][0]
    if change=='generation':v['generation_after_load']=v['before']['generation']
    elif change=='outside_dispatch':v['samples'][-1]['dispatch']['started_at']=v['samples'][-1]['observed_at']+1
    elif change=='early_observation':v['samples'][-1]['observed_at']=v['load_started_at']-1
    elif change=='missing_dispatch':r['dispatch_log']=[]
    else:v['dispatch']['thread']=-1
   with self.subTest(change=change):self.reject(mutate)
 def test_no_dropped_first_ready_sample_or_fabricated_sample_counts(self):
  for change in ('count','arrival','earlier_ready'):
   def mutate(r):
    v=r['visits'][1]
    if change=='count':v['sample_count']-=1
    elif change=='arrival':v['arrival']['observed_at']+=1
    else:v['samples'][0]=copy.deepcopy(v['arrival'])
   with self.subTest(change=change):self.reject(mutate)
 def test_observation_gaps_recomputed_and_never_claimed_as_40ms_precision(self):
  for change in ('run_gap','visit_gap','precision','overall_gap'):
   def mutate(r):
    if change=='run_gap':r['observation']['max_observation_gap_seconds']=.04
    elif change=='visit_gap':r['visits'][1]['max_observation_gap_seconds']=.04
    elif change=='precision':r['observation']['precision']='40ms'
    else:self.speed['max_observation_gap_seconds']['after']=.04
   with self.subTest(change=change):self.reject(mutate)
 def test_aggregate_samples_cannot_override_native_evidence(self):
  self.check();self.speed['sections']['Shows']['after_seconds']=[.01]*3
  with self.assertRaises(AssertionError):self.check()
 def test_same_threshold_rejects_slow_native_timings_even_with_matching_summary(self):
  def scale(value):
   if isinstance(value,list):return [scale(v) for v in value]
   if not isinstance(value,dict):return value
   return {k:(v*10 if k.endswith('_at') or k in ('first_usable_seconds','max_observation_gap_seconds') else scale(v)) for k,v in value.items()}
  self.runs['after']=scale(self.runs['after']);self.store('after');self.speed['max_observation_gap_seconds']['after']*=10
  for name,section in self.speed['sections'].items():
   section['after_seconds']=[v*10 for v in section['after_seconds']];section['after_median']*=10;section['within_tolerance']=False
  with self.assertRaisesRegex(AssertionError,'slowed beyond tolerance'):self.check()
 def test_candidate_entrypoint_rejects_v1_before_other_release_gates(self):
  from test_usability_release112 import Release112Acceptance
  fixture=Release112Acceptance();fixture.setUp();r=fixture.receipt;r['files']=copy.deepcopy(self.manifest['files'])
  (self.root/'controller-source/usability-release112-verification.json').write_text(json.dumps(r))
  with self.assertRaisesRegex(AssertionError,'requires native performance v2'):verify_release.verify(self.root/'artifacts')
 def test_full_v2_wrapper_reads_bound_receipts_and_rejects_digest_drift(self):
  from test_usability_release112 import Release112Acceptance
  fixture=Release112Acceptance();fixture.setUp();r=fixture.receipt;r['files']=copy.deepcopy(self.manifest['files']);r['devices']['fire']['browsing_speed']=self.speed
  verify_release.verify_release112_acceptance(r,self.manifest,require_v2=True)
  self.speed['native_receipts']['after']['sha256']='0'*64
  with self.assertRaisesRegex(AssertionError,'SHA differs'):verify_release.verify_release112_acceptance(r,self.manifest,require_v2=True)
 def test_full_release_requires_v2_but_historical_fixture_can_use_v1(self):
  from test_usability_release112 import Release112Acceptance
  fixture=Release112Acceptance();fixture.setUp();verify_release.verify_release112_acceptance(fixture.receipt,fixture.manifest)
  with self.assertRaises(AssertionError):verify_release.verify_release112_acceptance(fixture.receipt,fixture.manifest,require_v2=True)
if __name__=='__main__':unittest.main()
