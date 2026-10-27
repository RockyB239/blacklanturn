import copy,importlib.util,json,unittest
from pathlib import Path
from historical_release_fixture import published129
ROOT=published129()
s=importlib.util.spec_from_file_location('refresh_release_gate',ROOT/'tools/verify_release.py');V=importlib.util.module_from_spec(s);s.loader.exec_module(V)
class Release118(unittest.TestCase):
 def inputs(self):return json.loads((ROOT/'controller-source/youtube-refresh-native-verification.json').read_text()),json.loads((ROOT/'controller-source/manifest87.json').read_text())
 def gate(self,*args):
  f=getattr(V,'verify_youtube_refresh_acceptance',None);self.assertTrue(callable(f),'Missing current source-bound freshness acceptance gate');f(*args,historical=True)
 def test_retained_v87_source_and_mac_history_progressive_proof_pass(self):self.gate(*self.inputs())
 def test_configuration_guard_cannot_pass_without_native_failure_and_normal_proof(self):
  r,m=self.inputs();r['configuration_guard']={'passed':False}
  f=getattr(V,'verify_youtube_refresh_acceptance')
  with self.assertRaises(AssertionError):f(r,m,historical=True)
 def test_stale_source_or_incomplete_history_or_progressive_proof_cannot_pass(self):
  r,m=self.inputs()
  for mode in ('files','cache','history','preview','focus','false_remote_claim'):
   b=copy.deepcopy(r)
   if mode=='files':b['files']['youtube_rows.py']='0'*64
   elif mode=='cache':b['cache']['candidate_sha256']='0'*64
   elif mode=='history':b['history']['full_video_remote_http_statuses']=[]
   elif mode=='preview':b['history']['preview_remote_reports']=1
   elif mode=='focus':b['acceptance']['native_behavior']['active_category_pinned']=False
   else:b['native_devices']=['mac','fire']
   f=getattr(V,'verify_youtube_refresh_acceptance',None);self.assertTrue(callable(f),'Missing current source-bound acceptance')
   with self.subTest(mode=mode),self.assertRaises(AssertionError):f(b,m,historical=True)
