"""Historical visual proof is scoped to unchanged notice code, not new install-core code."""
import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tools import verify_release_notices as gate
ROOT=Path(__file__).resolve().parents[1]
class HistoricalNoticeBoundary(unittest.TestCase):
 def setUp(self):
  self.receipt=json.loads((ROOT/'controller-source/release-notices-native-verification.json').read_text());self.manifest=json.loads((ROOT/'controller-source/manifest90.json').read_text())
 def test_unchanged_notice_source_can_reuse_visual_proof_separately_from_install_core(self):
  self.assertTrue(gate.verify(self.receipt,self.manifest,historical=True))
 def test_notice_state_change_still_requires_fresh_native_notice_acceptance(self):
  receipt=copy.deepcopy(self.receipt);receipt['installer_files']['resources/libs/release_notice_state.py']='0'*64
  with self.assertRaises(AssertionError):gate.verify(receipt,self.manifest,historical=True)
