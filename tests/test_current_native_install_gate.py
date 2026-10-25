"""A historical UI receipt cannot stand in for current installation acceptance."""
import copy,hashlib,tempfile,unittest
from pathlib import Path
from tools import verify_current_install as gate
class CurrentNativeInstallGate(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.root=Path(self.t.name)
  self.artifacts={}
  for n in gate.NAMES:
   (self.root/n).write_bytes(n.encode());self.artifacts[n]=hashlib.sha256(n.encode()).hexdigest()
  self.receipt={'passed':True,'network_blocked':True,'personal_profile_denied':True,'personal_profile_accessed':False,'artifacts':self.artifacts,'cases':[]}
  for e in ('General','Apple-TV-Mac'):
   for m in ('clean','standard','update'):
    self.receipt['cases'].append({'edition':e,'mode':m,'passed':True,'source_files_exact':3800,'release_state_verified':True,'native_registry_preserved':True,'synthetic_history_choice_preserved':True,'payload_sha256':self.artifacts['BlackLanturn-'+e+'-Kodi21-1.1.25.zip'],'installer_sha256':self.artifacts[gate.INSTALLER],'synthetic_playback_state_paths_preserved':12 if m!='clean' else 0,'clean_cleared_synthetic_playback_state':m=='clean','native_managed_versions_verified':m=='update','all_saved_data_unchanged':m=='update','unrelated_addon_unchanged':m=='update'})
 def test_exact_current_four_case_native_receipt_passes(self):self.assertTrue(gate.verify(self.receipt,self.root))
 def test_missing_or_duplicate_case_refuses(self):
  for change in ('missing','duplicate'):
   r=copy.deepcopy(self.receipt)
   if change=='missing':r['cases'].pop()
   else:r['cases'][-1]=r['cases'][0]
   with self.subTest(change=change),self.assertRaises(AssertionError):gate.verify(r,self.root)
 def test_source_changed_after_acceptance_refuses(self):
  (self.root/gate.INSTALLER).write_bytes(b'changed')
  with self.assertRaises(AssertionError):gate.verify(self.receipt,self.root)
 def test_missing_sandbox_or_preservation_refuses(self):
  for key in ('passed','network_blocked','personal_profile_denied'):
   r=copy.deepcopy(self.receipt);r[key]=False
   with self.subTest(key=key),self.assertRaises(AssertionError):gate.verify(r,self.root)
  r=copy.deepcopy(self.receipt);r['cases'][1]['synthetic_playback_state_paths_preserved']=0
  with self.assertRaises(AssertionError):gate.verify(r,self.root)
