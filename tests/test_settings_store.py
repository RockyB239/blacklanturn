import importlib.util,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
LIB=Path(__file__).resolve().parents[1]/'installer-source/plugin.program.blacklanturninstaller/resources/libs'
class SettingsStore(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.path=Path(self.tmp.name)/'settings.xml'
  s=importlib.util.spec_from_file_location('store_test',LIB/'settings_store.py');self.m=importlib.util.module_from_spec(s);s.loader.exec_module(self.m)
 def fake(self,values):
  class File:
   def __init__(self,path,mode=None):self.path=path
   def size(self):return len(values[self.path])
   def readBytes(self):return values[self.path]
   def write(self,text):values[self.path]=text.encode();return True
   def close(self):pass
  return types.SimpleNamespace(exists=lambda p:p in values,File=File,delete=lambda p:bool(values.pop(p,None)))
 def test_tvos_native_xml_is_authoritative_even_with_physical_shadow(self):
  self.path.write_bytes(b'physical-shadow');values={str(self.path):b'native-settings'}
  with patch.object(self.m,'xbmcvfs',self.fake(values)),patch.object(self.m,'TVOS',True,create=True):
   self.assertEqual(self.m.read(self.path),b'native-settings');self.m.write(self.path,b'updated-native');self.assertEqual(values[str(self.path)],b'updated-native');self.assertEqual(self.m.read(self.path),b'updated-native')
 def test_missing_xml_on_normal_platform_is_private_atomic_file(self):
  with patch.object(self.m,'xbmcvfs',self.fake({})),patch.object(self.m,'TVOS',False,create=True):
   self.m.write(self.path,b'private-settings');self.assertEqual(self.path.read_bytes(),b'private-settings');self.assertEqual(self.path.stat().st_mode&0o777,0o600)
 def test_tvos_missing_native_xml_does_not_use_stale_physical_file(self):
  self.path.write_bytes(b'stale')
  with patch.object(self.m,'xbmcvfs',self.fake({})),patch.object(self.m,'TVOS',True,create=True):self.assertFalse(self.m.exists(self.path))

 def test_native_inventory_includes_virtual_xml_and_evicted_addon_settings(self):
  h=self.path.parent;u=h/'userdata';u.mkdir();(h/'addons/plugin.test').mkdir(parents=True)
  values={str(u/'guisettings.xml'):b'gui',str(u/'addon_data/plugin.test/settings.xml'):b'addon'}
  fake=self.fake(values);fake.listdir=lambda p:([],['guisettings.xml'] if p==str(u)+'/' else [])
  with patch.object(self.m,'xbmcvfs',fake),patch.object(self.m,'TVOS',True):
   self.assertEqual(set(self.m.native_userdata_xml(h)),set(map(Path,values)))
   for path in self.m.native_userdata_xml(h):self.m.delete(path)
   self.assertFalse(values)
