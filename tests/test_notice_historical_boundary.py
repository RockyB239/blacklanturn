"""Historical visual proof is scoped to unchanged notice code, not new install-core code."""
import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tools import verify_release_notices as gate
ROOT=Path(__file__).resolve().parents[1]
class HistoricalNoticeBoundary(unittest.TestCase):
 def setUp(self):
  self.receipt=json.loads((ROOT/'controller-source/release-notices-native-verification.json').read_text());self.manifest=json.loads((ROOT/'controller-source/manifest90.json').read_text())
 def test_reminder_ui_requires_new_proof_while_unchanged_engine_uses_history(self):
  with self.assertRaises(AssertionError):gate.verify(self.receipt,self.manifest,historical=True)
  current=gate.inventory(ROOT/'controller-source/addon');changed=('update_notes_ui.py','resources/skins/Default/1080i/UpdateNotice.xml')
  reminder={'passed':True,'native_kodi_launches':2,'protected_settings_paths_compared':8,'files':{n:current[n] for n in changed},'cases':dict.fromkeys(('later_repeats_next_session','same_session_once','never_only_this_release','future_release_not_suppressed','completed_once','button_visible','settings_preserved','legacy_later_not_suppressed'),True)}
  self.assertTrue(gate.verify(self.receipt,self.manifest,historical=True,reminder_receipt=reminder))
  reminder['files']['update_notes_ui.py']='0'*64
  with self.assertRaises(AssertionError):gate.verify(self.receipt,self.manifest,historical=True,reminder_receipt=reminder)
 def test_notice_state_change_still_requires_fresh_native_notice_acceptance(self):
  receipt=copy.deepcopy(self.receipt);receipt['installer_files']['resources/libs/release_notice_state.py']='0'*64
  with self.assertRaises(AssertionError):gate.verify(receipt,self.manifest,historical=True)
