import hashlib,json,unittest,xml.etree.ElementTree as E
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class UpdateNotesRelease(unittest.TestCase):
 def test_current_versions_and_exact_state_module(self):
  addon=ROOT/'controller-source/addon'
  self.assertEqual(E.parse(addon/'addon.xml').getroot().get('version'),'0.1.92')
  source=ROOT/'installer-source/plugin.program.blacklanturninstaller'
  self.assertEqual(E.parse(source/'addon.xml').getroot().get('version'),'1.0.30')
  self.assertEqual((addon/'update_notes.py').read_bytes(),(source/'resources/libs/update_notes_state.py').read_bytes())
 def test_notes_source_is_bounded_and_nonempty(self):
  notes=json.loads((ROOT/'controller-source/addon/update-releases.json').read_text())
  self.assertIn('0.1.88',notes['script.blacklanturn.preview']) # legacy content is inert; new UI uses curated catalog
  for versions in notes.values():
   for entry in versions.values():
    self.assertTrue(entry['summary']);self.assertLessEqual(len(entry['summary']),6)
    self.assertTrue(all(len(x)<=240 and 'http' not in x for x in entry['summary']))
 def test_current_manifest_and_history_immutable(self):
  addon=ROOT/'controller-source/addon';manifest=json.loads((ROOT/'controller-source/manifest92.json').read_text())
  actual={p.relative_to(addon).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in addon.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
  self.assertEqual(actual,manifest['files'])
  self.assertEqual(json.loads((ROOT/'controller-source/manifest87.json').read_text())['controller'],'0.1.87')
 def test_native_gate_rejects_missing_receipt_and_stale_source(self):
  import importlib.util,copy
  spec=importlib.util.spec_from_file_location('update_notes_gate',ROOT/'tools/verify_release_notices.py');gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
  manifest=json.loads((ROOT/'controller-source/manifest90.json').read_text())
  with self.assertRaises(AssertionError):gate.verify({},manifest)
  receipt={'schema':1,'feature':'curated-release-notices-1','passed':True,'controller':'0.1.90','installer':'1.0.27','runtime':'21.3','native_devices':['mac'],'files':manifest['files'],'native':{'mac':dict.fromkeys(gate.CASES,True)},'automated':dict.fromkeys(('playback_deferral','monitor_error_isolation','no_inventory','failed_install_no_success'),True)}
  source=ROOT/'installer-source/plugin.program.blacklanturninstaller'
  receipt['installer_files']={p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo')}
  for mode in ('source','installer','case','device'):
   bad=copy.deepcopy(receipt)
   if mode=='source':bad['files']['update_notes.py']='0'*64
   elif mode=='installer':bad['installer_files']['resources/libs/gui/navigation.py']='0'*64
   elif mode=='case':bad['native']['mac'][gate.CASES[0]]=False
   else:bad['native_devices']=['apple']
   with self.subTest(mode=mode),self.assertRaises(AssertionError):gate.verify(bad,manifest)

 def test_branded_installer_tools_exposes_notes_action(self):
  import ast,types
  source=ROOT/'installer-source/plugin.program.blacklanturninstaller/resources/libs/gui/navigation.py'
  fn=next(n for n in ast.parse(source.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='tools_menu')
  rows=[]
  ns={'CONFIG':types.SimpleNamespace(ADDON_ID='plugin.program.blacklanturninstaller'),
      'tools':types.SimpleNamespace(platform=lambda:'osx'),
      'directory':types.SimpleNamespace(_add_menu_item=lambda label,params,*a:rows.append((label,params))),
      'producer':lambda p:None}
  exec(compile(ast.Module(body=[fn],type_ignores=[]),str(source),'exec'),ns);ns['tools_menu']()
  self.assertIn(('What’s new & update notices',{'mode':'updatenotes'}),rows)
