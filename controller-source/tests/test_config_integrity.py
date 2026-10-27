"""Protect existing row preferences when startup reads fail or saves overlap."""
import ast,copy,importlib.util,json,sys,tempfile,unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace,MethodType
from unittest.mock import patch
ROOT=Path(__file__).parents[1]/'addon'
from discovery_core import migrate_pages
from navigation_core import migrate_navigation
class ConfigIntegrity(unittest.TestCase):
 def runtime(self):
  s=importlib.util.spec_from_file_location('config_runtime_test',ROOT/'live_runtime.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
 def method(self,name,ns):
  cls=next(n for n in ast.parse((ROOT/'live_review.py').read_text()).body if isinstance(n,ast.ClassDef) and n.name=='LiveReview');fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name==name);exec(compile(ast.Module(body=[fn],type_ignores=[]),'controller-config','exec'),ns);return ns[name]
 def startup(self,folder,loader):
  ns={'json':json,'STORE':Path(folder),'read_controller_config':loader,'migrate_pages':migrate_pages,'migrate_navigation':migrate_navigation,'event':lambda *a,**k:None,'tmdb':lambda *a,**k:'plugin://plugin.video.test/'+str(a)}
  owner=SimpleNamespace(config={},setProperty=lambda *a:None,invalidate_row_results=lambda:None);owner.save=MethodType(self.method('save',ns),owner)
  cls=next(n for n in ast.parse((ROOT/'live_review.py').read_text()).body if isinstance(n,ast.ClassDef) and n.name=='LiveReview');fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='onInit');stmts=fn.body
  start=next((i for i,n in enumerate(stmts) if isinstance(n,ast.Assign) and any(isinstance(x,ast.Attribute) and x.attr=='config_loaded' for x in n.targets)),None)
  self.assertIsNotNone(start,'Startup does not distinguish failed reads from writable preferences')
  end=next(i for i,n in enumerate(stmts[start:],start) if isinstance(n,ast.Assign) and any(isinstance(x,ast.Attribute) and x.attr=='snapshot_cache' for x in n.targets))
  owner.configure_icon_resources=lambda:None;ns['self']=owner;exec(compile(ast.Module(body=stmts[start:end],type_ignores=[]),'controller-startup-config','exec'),ns);return owner
 def test_transient_read_failure_cannot_replace_existing_preferences_with_fallback(self):
  for error in (FileNotFoundError('temporarily unavailable'),json.JSONDecodeError('partial','{',1)):
   with self.subTest(error=type(error).__name__),tempfile.TemporaryDirectory() as folder:
    p=Path(folder)/'rows.json';original=json.dumps({'Home':[{'label':'Owner row'}],'Movies':[],'Shows':[],'Saved':[{'title':'Retain'}],'PreviewMode':'manual'});p.write_text(original)
    def fail(path):raise error
    owner=self.startup(folder,fail);self.assertFalse(owner.config_loaded);self.assertIs(owner.save(),False);self.assertEqual(p.read_text(),original)
 def test_valid_preferences_migrate_without_losing_unknown_fields(self):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)/'rows.json';values={'Home':[],'Movies':[],'Shows':[],'Saved':[{'id':7}],'PrivatePreference':{'keep':'unchanged'}};p.write_text(json.dumps(values));owner=self.startup(folder,lambda path:json.loads(path.read_text()));actual=json.loads(p.read_text())
   self.assertTrue(owner.config_loaded);self.assertEqual(actual['Saved'],values['Saved']);self.assertEqual(actual['PrivatePreference'],values['PrivatePreference']);self.assertEqual(actual['DiscoverySchema'],2)
 def test_concurrent_saves_are_complete_and_do_not_share_a_temporary_file(self):
  m=self.runtime();save=getattr(m,'write_controller_config',None);self.assertTrue(callable(save),'Missing unique atomic controller writer')
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)/'rows.json';p.write_text('{"Saved":[7]}');values=[{'Saved':[7],'choice':i,'blob':'x'*(i*500+1000)} for i in range(32)]
   with ThreadPoolExecutor(max_workers=8) as pool:list(pool.map(lambda value:save(p,value),values))
   self.assertIn(json.loads(p.read_text()),values);self.assertEqual([x.name for x in Path(folder).iterdir()],['rows.json'])
 def test_replace_failure_leaves_original_and_removes_only_owned_temp(self):
  m=self.runtime();save=getattr(m,'write_controller_config',None);self.assertTrue(callable(save),'Missing atomic controller writer')
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)/'rows.json';p.write_text('{"Saved":[7]}')
   with patch('os.replace',side_effect=OSError('fixture failure')),self.assertRaises(OSError):save(p,{'Saved':[8]})
   self.assertEqual(p.read_text(),'{"Saved":[7]}');self.assertEqual([x.name for x in Path(folder).iterdir()],['rows.json'])
 def test_reader_rejects_nonobject_without_changing_disk(self):
  m=self.runtime();read=getattr(m,'read_controller_config',None);self.assertTrue(callable(read),'Missing validated controller reader')
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)/'rows.json';p.write_text('[1,2]')
   with self.assertRaises(ValueError):read(p)
   self.assertEqual(p.read_text(),'[1,2]')
