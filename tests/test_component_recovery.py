import types,unittest
from pathlib import Path
from unittest.mock import patch
from test_inplace_update import InPlace
class ComponentRecovery(unittest.TestCase):
 setUp=InPlace.setUp;seed=InPlace.seed;saved=InPlace.saved;archive=InPlace.archive
 def test_process_loss_reconstruction_is_inside_recovery_owned_staging(self):
  real=self.m._module;captured=[];held=[];lock=self.m._lock
  def acquire(home):
   p=lock(home);held.append(p);return p
  def expand(path,home,directory):
   orphan=Path(directory)/'reconstruction.zip';orphan.write_bytes(b'partial large archive');captured.append(orphan);raise KeyboardInterrupt('process exit')
  fake=types.SimpleNamespace(is_component=lambda p:True,expand=expand)
  try:
   with patch.object(self.m,'_module',side_effect=lambda name:fake if name=='component_update' else real(name)),patch.object(self.m,'_lock',side_effect=acquire):
    with self.assertRaises(KeyboardInterrupt):self.m.prepare(self.archive(),self.home,self.kodi)
   self.assertEqual(captured[0].parent,self.home/'addons/.blacklanturn-update')
  finally:
   for plan in held:self.m.release(plan)
  self.assertTrue(self.m.recover(self.home));self.assertFalse(captured[0].exists());self.assertEqual(self.saved(),self.before)
