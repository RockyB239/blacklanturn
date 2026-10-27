"""A temporary update lease must not become a saved preference or stale blocker."""
import importlib.util,sys,types,unittest,time,threading,tempfile
from pathlib import Path
from unittest.mock import patch
LIB=Path(__file__).parents[1]/'installer-source/plugin.program.blacklanturninstaller/resources/libs'
class Activity(unittest.TestCase):
 def module(self):
  path=LIB/'update_activity.py';self.assertTrue(path.exists(),'Temporary activity lease missing')
  spec=importlib.util.spec_from_file_location('activity_test',path);m=importlib.util.module_from_spec(spec)
  spec.loader.exec_module(m);return m
 def test_context_renews_and_clears_on_exception_without_settings(self):
  m=self.module();values={};window=types.SimpleNamespace(getProperty=lambda k:values.get(k,''),setProperty=lambda k,v:values.__setitem__(k,v),clearProperty=lambda k:values.pop(k,None))
  with self.assertRaises(ValueError):
   with m.hold(window=window):
    self.assertTrue(m.active(window=window));raise ValueError('download failed')
  self.assertFalse(m.active(window=window));self.assertEqual(values,{})
 def test_expired_malformed_and_foreign_owner_are_handled(self):
  m=self.module();values={};window=types.SimpleNamespace(getProperty=lambda k:values.get(k,''),setProperty=lambda k,v:values.__setitem__(k,v),clearProperty=lambda k:values.pop(k,None))
  for raw in ('bad','{}','[1]', '{"owner":"x","until":0}'):
   values[m.KEY]=raw;self.assertFalse(m.active(window=window))
  with m.hold(window=window):values[m.KEY]='foreign-owner'
  self.assertEqual(values[m.KEY],'foreign-owner')
 def test_unavailable_gui_never_blocks_browsing(self):
  m=self.module()
  with patch.dict(sys.modules,{'xbmcgui':None}):self.assertFalse(m.active())

 def test_second_writer_is_refused_without_clearing_first_lease(self):
  m=self.module();values={};w=types.SimpleNamespace(getProperty=lambda k:values.get(k,''),setProperty=lambda k,v:values.__setitem__(k,v),clearProperty=lambda k:values.pop(k,None))
  with tempfile.TemporaryDirectory() as folder:
   with m.hold(window=w,lock_path=Path(folder)/'activity.lock'):
    with self.assertRaises(RuntimeError):
     with m.hold(window=w,lock_path=Path(folder)/'activity.lock'):pass
    self.assertTrue(m.active(window=w))
   self.assertFalse(m.active(window=w))
