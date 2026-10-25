import copy,json,unittest
from pathlib import Path
from unittest.mock import patch
from tools import verify_release129 as gate,verify_current_install129 as native
class Release129(unittest.TestCase):
 def test_exact_source(self):
  self.assertTrue(gate.verify_source(json.loads((gate.ROOT/'controller-source/manifest95.json').read_text()),gate.inventory(gate.ROOT/'installer-source/plugin.program.blacklanturninstaller')))
 def test_unrelated_transaction_change_rejected(self):
  original=gate.inventory;installer=original(gate.ROOT/'installer-source/plugin.program.blacklanturninstaller');installer['resources/libs/inplace_update.py']='f'*64
  with patch.object(gate,'inventory',side_effect=lambda p:installer if p.name=='plugin.program.blacklanturninstaller'else original(p)),self.assertRaises(AssertionError):gate.verify_source(json.loads((gate.ROOT/'controller-source/manifest95.json').read_text()),installer)
 def test_missing_native_evidence_rejected(self):
  with self.assertRaises(AssertionError):native.verify_presentation({}, {}, {})
 def test_inherited_paths_still_exact(self):
  self.assertTrue(native.verify_inherited(json.loads((gate.ROOT/'controller-source/manifest95.json').read_text())['files'],gate.inventory(gate.ROOT/'installer-source/plugin.program.blacklanturninstaller')))
