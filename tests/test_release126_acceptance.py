"""Current native feature evidence cannot certify unrelated source or devices."""
import copy, importlib.util, json, unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
class Release126Acceptance(unittest.TestCase):
 def gate(self):
  spec=importlib.util.spec_from_file_location('release126_gate',ROOT/'tools/verify_release126.py')
  self.assertTrue(Path(spec.origin).is_file(),'Missing source-bound release126 feature gate')
  gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate);return gate
 def inputs(self):
  gate=self.gate();receipt=json.loads((ROOT/'controller-source/release126-feature-verification.json').read_text())
  manifest=json.loads((ROOT/'controller-source/manifest93.json').read_text());return gate,receipt,manifest
 def test_real_evidence_matches_current_implementation(self):
  gate,receipt,manifest=self.inputs();self.assertTrue(gate.verify(receipt,manifest,historical=True))
 def test_source_ui_device_and_evidence_drift_are_rejected(self):
  gate,receipt,manifest=self.inputs()
  for mode in ('controller','installer','normalization','device','discovery','preview','preservation','evidence'):
   bad=copy.deepcopy(receipt)
   if mode=='controller':bad['files']['preview_fallback.py']='0'*64
   elif mode=='installer':bad['installer_files']['resources/libs/gui/updates.py']='0'*64
   elif mode=='normalization':bad['normalization']['controller']['tested_files']['addon.xml']='0'*64
   elif mode=='device':bad['native_devices']=['mac','fire']
   elif mode=='discovery':bad['native']['recommendations_and_paging']=False
   elif mode=='preview':bad['native']['correct_secondary_preview_played']=False
   elif mode=='preservation':bad['preservation']['history_preserved']=False
   else:bad['evidence']['discovery']['sha256']='not-a-digest'
   with self.subTest(mode=mode),self.assertRaises(AssertionError):gate.verify(bad,manifest)
 def test_changed_current_runtime_cannot_hide_behind_recorded_manifest(self):
  gate,receipt,manifest=self.inputs();actual=gate.inventory(ROOT/'controller-source/addon');actual['related_titles.py']='0'*64
  inventory=gate.inventory
  def altered(root):return actual if root==ROOT/'controller-source/addon' else inventory(root)
  with patch.object(gate,'inventory',altered),self.assertRaises(AssertionError):gate.verify(receipt,manifest)

 def test_historical_proof_uses_immutable126_source_instead_of_new_startup(self):
  gate,receipt,manifest=self.inputs()
  with patch.object(gate,'inventory',return_value={'new_recovery.py':'0'*64}):
   self.assertTrue(gate.verify(receipt,manifest,historical=True))
  bad=copy.deepcopy(receipt);bad['files']['related_titles.py']='0'*64
  with self.assertRaises(AssertionError):gate.verify(bad,manifest,historical=True)
