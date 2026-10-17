"""Regression for native tvOS XML omitted by a cached directory listing."""
import importlib.util,tempfile,types,unittest,xml.etree.ElementTree as E
from pathlib import Path
HERE=Path(__file__).parent
class Storage:
 def __init__(self,raw):
  self.raw=raw;self.bad_cache=False;self.writes=0
  owner=self
  class File:
   def __init__(self,path):self.path=path
   def size(self):return 0 if owner.bad_cache else len(owner.raw)
   def readBytes(self):return b'' if owner.bad_cache else owner.raw
   def close(self):pass
  self.File=File
 def listdir(self,path):
  self.bad_cache=not path.endswith('/')
  return [],[] if self.bad_cache else ['settings.xml']
class NativeStorageTests(unittest.TestCase):
 def module(self):
  path=HERE/'native_storage.py';self.assertTrue(path.is_file(),'No maintained safe native XML read helper')
  spec=importlib.util.spec_from_file_location('native_storage',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
 def test_read_repairs_false_missing_cache_without_rewriting_settings(self):
  m=self.module();raw=b'<settings><setting id="authorization">fake-account</setting></settings>';vfs=Storage(raw);vfs.listdir('/owned/userdata/probe');self.assertEqual(vfs.File('/owned/userdata/probe/settings.xml').readBytes(),b'')
  self.assertEqual(m.read_xml(vfs,'/owned/userdata/probe/settings.xml'),raw);self.assertEqual(vfs.writes,0)
 def test_list_directory_always_normalizes_its_trailing_separator(self):
  m=self.module();vfs=Storage(b'<settings/>')
  for path in ['/owned/userdata/probe','/owned/userdata/probe/','/owned/userdata/probe///']:
   self.assertEqual(m.listdir(vfs,path),([],['settings.xml']))
 def test_invalid_xml_stops_without_any_write(self):
  m=self.module();vfs=Storage(b'<settings>')
  with self.assertRaises(ValueError):m.read_xml(vfs,'/owned/userdata/probe/settings.xml')
  self.assertEqual(vfs.writes,0)
 def test_oversize_xml_stops_before_read(self):
  m=self.module();vfs=Storage(b'x'*101)
  with self.assertRaises(ValueError):m.read_xml(vfs,'/owned/userdata/probe/settings.xml',max_bytes=100)
 def test_required_checks_are_active_under_optimized_python(self):
  m=self.module();scope={};exec(compile((HERE/'native_storage.py').read_text(),'native_storage.py','exec',optimize=2),scope)
  with self.assertRaises(RuntimeError):scope['require'](False,'Expected rejection')

class NativeProbeTests(unittest.TestCase):
 def test_owned_probe_checks_execute_under_optimized_python_and_keep_real_xml(self):
  import ast
  path=HERE/'native_storage_probe.py';self.assertTrue(path.is_file(),'No maintained owned-only native regression probe')
  self.assertFalse(any(isinstance(n,ast.Assert) for n in ast.walk(ast.parse(path.read_text()))),'Native checks are disabled by Kodi optimization')
  scope={'__name__':'storage_probe_test','__file__':str(path)};exec(compile(path.read_text(),str(path),'exec',optimize=2),scope)
  class VFS:
   def __init__(self):
    self.values={};self.bad={};owner=self
    class File:
     def __init__(self,path,mode=None):self.path=str(path)
     def size(self):return len(self.readBytes())
     def readBytes(self):return b'' if owner.bad.get(str(Path(self.path).parent)) else owner.values.get(self.path,b'')
     def write(self,text):owner.values[self.path]=text.encode();owner.bad[str(Path(self.path).parent)]=False;return True
     def close(self):pass
    self.File=File
   def listdir(self,path):
    parent=path.rstrip('/');self.bad[parent]=not path.endswith('/');return [],[] if self.bad[parent] else [Path(k).name for k in self.values if str(Path(k).parent)==parent]
   def exists(self,path):return path in self.values
   def delete(self,path):return self.values.pop(str(path),None) is not None
  import sys
  sys.path.insert(0,str(HERE));self.addCleanup(sys.path.remove,str(HERE))
  with tempfile.TemporaryDirectory() as folder:
   home=Path(folder);(home/'userdata').mkdir();vfs=VFS()
   for name in scope['PROTECTED_XML']:vfs.values[str(home/'userdata'/name)]=b'<settings><setting id="account">fake-private-value</setting></settings>'
   before=dict(vfs.values);result=scope['run'](vfs,home);self.assertTrue(result['passed']);self.assertTrue(result['legacy_trigger_reproduced']);self.assertEqual(vfs.values,before);self.assertEqual(list((home/'userdata').iterdir()),[])
