"""The protected General YouTube version must retain real checksum/settings checks."""
from pathlib import Path
import importlib.util,sys,tempfile,types,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'compatibility/managed-updates/previewcheck'
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
class PreviewCheckManaged(unittest.TestCase):
 def setUp(self):self.c=module('guard',D/'candidate/check.py');self.code=(D/'tested-player_client.py').read_bytes()
 def test_protected_version_passes_the_exact_client_and_settings(self):
  self.assertEqual(self.c.inspect('1:7.4.4+blacklanturn.1',self.code,True,True),'verified')
 def test_protected_version_still_detects_replaced_source_and_disabled_settings(self):
  self.assertEqual(self.c.inspect('1:7.4.4+blacklanturn.1',self.code+b'\n',True,True),'replaced')
  for isa,dash in ((False,True),(True,False),(False,False)):
   self.assertEqual(self.c.inspect('1:7.4.4+blacklanturn.1',self.code,isa,dash),'settings')
 def test_unreviewed_epoch_brand_and_apple_variant_are_not_assumed_compatible(self):
  for v in ('1:7.4.4+blacklanturn.2','2:7.4.4+blacklanturn.1','1:7.4.4a+blacklanturn.1','7.5.0'):
   self.assertEqual(self.c.inspect(v,self.code,True,True),'review')
 def test_legacy_tested_version_remains_supported(self):
  self.assertEqual(self.c.inspect('7.4.4',self.code,True,True),'verified')
 def test_startup_runs_the_real_guard_for_protected_version_without_warning(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);p=root/'resources/lib/youtube_plugin/youtube/client/player_client.py';p.parent.mkdir(parents=True);p.write_bytes(self.code);warnings=[]
   class YouTube:
    def getAddonInfo(self,k):return {'version':'1:7.4.4+blacklanturn.1','path':str(root)}[k]
    def getSettingBool(self,k):return True
   class Monitor:
    def waitForAbort(self,n):return False
   class Dialog:
    def notification(self,*a):warnings.append(a)
   mods={'check':self.c,'xbmc':types.SimpleNamespace(Monitor=Monitor,LOGINFO=1,log=lambda *a:None,getCondVisibility=lambda k:True),'xbmcaddon':types.SimpleNamespace(Addon=lambda a:YouTube()),'xbmcgui':types.SimpleNamespace(Dialog=Dialog,NOTIFICATION_WARNING='warning'),'xbmcvfs':types.SimpleNamespace(translatePath=lambda p:p)}
   with patch.dict(sys.modules,mods):
    m=module('guard_runtime',D/'candidate/runtime.py');self.assertEqual(m.run(startup=True),'verified');self.assertEqual(warnings,[])
 def test_packaging_applies_only_to_complete_reviewed_general_checker(self):
  m=module('guard_packaging',ROOT/'tools/build_release.py');fn=getattr(m,'apply_preview_check',None);self.assertTrue(callable(fn),'Packaging must include the corrected General checker')
  prefix='addons/service.blacklanturn.previewcheck/';data={prefix+p.name:p.read_bytes() for p in (D/'upstream').iterdir() if p.is_file()};data['unrelated']=b'keep';fn(data)
  c=module('packaged_guard',D/'candidate/check.py');scope={};exec(compile(data[prefix+'check.py'],'check.py','exec'),scope);self.assertEqual(scope['inspect']('1:7.4.4+blacklanturn.1',self.code,True,True),'verified');self.assertEqual(data['unrelated'],b'keep')
  apple={'unrelated':b'keep'};fn(apple);self.assertEqual(apple,{'unrelated':b'keep'})
  for mutation in ('changed','missing'):
   data={prefix+p.name:p.read_bytes() for p in (D/'upstream').iterdir() if p.is_file()}
   if mutation=='changed':data[prefix+'runtime.py']+=b'\n'
   else:del data[prefix+'runtime.py']
   before=dict(data)
   with self.assertRaises(ValueError):fn(data)
   self.assertEqual(data,before)
