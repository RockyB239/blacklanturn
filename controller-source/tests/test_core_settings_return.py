import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
from backend_core import CoreSettingsReturn
class CoreReturn(unittest.TestCase):
 def test_does_not_restore_during_handoff_and_restores_after_core_back(self):
  gate=CoreSettingsReturn(0)
  self.assertEqual(gate.tick(10000,.1),'wait');self.assertEqual(gate.tick(10016,.2),'wait')
  self.assertEqual(gate.tick(10004,2),'wait');self.assertEqual(gate.tick(10000,3),'return')
 def test_failed_activation_has_a_bounded_return(self):
  gate=CoreSettingsReturn(0);self.assertEqual(gate.tick(10000,6),'failed')
 def test_nested_dialog_does_not_signal_back_until_home(self):
  gate=CoreSettingsReturn(0);gate.tick(10040,.1)
  self.assertEqual(gate.tick(10140,1),'wait');self.assertEqual(gate.tick(10040,2),'wait');self.assertEqual(gate.tick(10000,3),'return')
