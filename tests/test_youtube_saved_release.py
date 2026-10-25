"""The release may only promote the exact Mac/Fire tested controller."""
import copy,importlib.util,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def gate():
 s=importlib.util.spec_from_file_location('saved_release_gate',ROOT/'tools/verify_youtube_saved.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
class SavedRelease(unittest.TestCase):
 def setUp(self):
  self.receipt=json.loads((ROOT/'controller-source/release121-native-verification.json').read_text());self.manifest=json.loads((ROOT/'controller-source/manifest91.json').read_text())
 def test_exact_native_tested_source_is_accepted(self):self.assertTrue(gate().verify(self.receipt,self.manifest,historical=True))
 def test_missing_device_or_lost_history_or_wrong_source_is_rejected(self):
  for mutation in ('device','history','source','fetch','focus'):
   r=copy.deepcopy(self.receipt)
   if mutation=='device':del r['devices']['fire']
   elif mutation=='history':r['devices']['fire']['history_preserved']=False
   elif mutation=='source':r['files']['youtube_saved.py']='0'*64
   elif mutation=='fetch':r['devices']['mac']['fresh_feed_calls']=1
   else:r['devices']['fire']['refresh_focus_retained']=False
   with self.subTest(mutation=mutation),self.assertRaises(AssertionError):gate().verify(r,self.manifest,historical=True)
