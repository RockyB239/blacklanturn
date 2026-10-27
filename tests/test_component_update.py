import importlib.util,json,tempfile,unittest,zipfile,shutil
from pathlib import Path
ROOT=Path(__file__).parents[1]
class ComponentUpdate(unittest.TestCase):
 def module(self):
  spec=importlib.util.spec_from_file_location('components_test',ROOT/'installer-source/plugin.program.blacklanturninstaller/resources/libs/component_update.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
 def test_smaller_package_reconstructs_identical_target_and_refuses_drift(self):
  m=self.module()
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);home=root/'home';home.mkdir();base=root/'base.zip';target=root/'target.zip';component=root/'component.zip'
   old={'addons/script.same/addon.xml':b'<addon id="script.same"/>','addons/script.same/data':b'unchanged'*1000,'addons/script.new/addon.xml':b'<addon id="script.new"/>','addons/script.new/main.py':b'old','userdata/blacklanturn-build.json':json.dumps({'release_id':'old'}).encode()}
   new=dict(old);new['addons/script.new/main.py']=b'new';new['userdata/blacklanturn-build.json']=json.dumps({'release_id':'new'}).encode()
   for path,data in ((base,old),(target,new)):
    with zipfile.ZipFile(path,'w') as z:
     for n,raw in data.items():z.writestr(n,raw)
   with zipfile.ZipFile(base) as z:z.extractall(home)
   m.build(base,target,component)
   with zipfile.ZipFile(component) as z:self.assertTrue(all(info.date_time==(2026,10,16,0,0,0) for info in z.infolist()))
   self.assertLess(component.stat().st_size,target.stat().st_size)
   expanded=m.expand(component,home,root)
   try:
    with zipfile.ZipFile(expanded) as z:self.assertEqual({n:z.read(n) for n in z.namelist()},new)
   finally:expanded.unlink()
   (home/'addons/script.same/data').write_bytes(b'changed')
   with self.assertRaises(ValueError):m.expand(component,home,root)
 def test_wrong_base_release_cannot_apply_partial_update(self):
  m=self.module()
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);(root/'userdata').mkdir();(root/'userdata/blacklanturn-build.json').write_text('{"release_id":"wrong"}')
   archive=root/'component.zip'
   with zipfile.ZipFile(archive,'w') as z:z.writestr('userdata/blacklanturn-components.json',json.dumps({'schema':1,'base':'old','target':'new','addons':{},'retained':{}}))
   with self.assertRaises(ValueError):m.expand(archive,root,root)

class ComponentOffer(unittest.TestCase):
 def test_real_catalog_checksum_field_selects_component_asset(self):
  import ast,re,sys,types
  from unittest.mock import patch
  p=ROOT/'installer-source/plugin.program.blacklanturninstaller/resources/libs/check.py'
  node=next(n for n in ast.parse(p.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='check_components')
  response=types.SimpleNamespace(text='name="BlackLanturn General"\nupdatebase="old"\nupdateurl="https://example.com/update.zip"\nupdatesha256="'+'a'*64+'"')
  common=types.ModuleType('resources.libs.common');common.tools=types.SimpleNamespace(open_url=lambda source:response)
  ns={'re':re,'CONFIG':types.SimpleNamespace(BUILDFILE='https://example.com/catalog')};exec(compile(ast.Module(body=[node],type_ignores=[]),str(p),'exec'),ns)
  with patch.dict(sys.modules,{'resources':types.ModuleType('resources'),'resources.libs':types.ModuleType('resources.libs'),'resources.libs.common':common}):
   self.assertEqual(ns['check_components']('BlackLanturn General','old'),{'url':'https://example.com/update.zip','sha256':'a'*64})
   self.assertIsNone(ns['check_components']('BlackLanturn General','wrong'))
