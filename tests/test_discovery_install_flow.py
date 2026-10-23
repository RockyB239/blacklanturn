import json,types,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
import test_network_install_flow as network
ROOT=Path(__file__).resolve().parents[1]
POLICY=dict(network.POLICY,preferences_policy='playback-trakt-youtube-umbrella-network-autoplay-1',autoplay_patch='same-show-source-1',installer_min_version='1.0.22',discovery_patch='discovery-first-page-1')
CAT=json.loads((ROOT/'installer-source/plugin.program.blacklanturninstaller/resources/discovery-lineup.json').read_text())
class DiscoveryInstallFlow(unittest.TestCase):
 def setUp(self):self.f=network.NetworkInstallFlow();self.f.setUp();self.addCleanup(self.f.doCleanups)
 def package(self,change=None):
  path=self.f.packaged(policy=POLICY)
  with zipfile.ZipFile(path) as z:data={n:z.read(n) for n in z.namelist()}
  data['userdata/addon_data/script.blacklanturn.preview/rows.json']=json.dumps(dict(CAT['defaults'],PreviewMode='manual',Saved=[])).encode()
  data['addons/script.blacklanturn.preview/addon.xml']=b'<addon id="script.blacklanturn.preview" version="0.1.86"/>'
  if change:change(data)
  with zipfile.ZipFile(path,'w') as z:
   for n,v in data.items():z.writestr(n,v)
  return path
 def test_standard_update_migrates_old_defaults_and_keeps_credentials_preferences(self):
  k,cfg,mods=self.f.f.environment();self.package();h=Path(cfg.HOME)
  p=h/'userdata/addon_data/script.blacklanturn.preview/rows.json';p.parent.mkdir(parents=True,exist_ok=True)
  old=json.loads((ROOT/'tests/fixtures/discovery-legacy-defaults.json').read_text());old.update(PreviewMode='manual',RatingSources=['imdb'],Saved=[{'id':9}],custom='keep');p.write_text(json.dumps(old))
  self.f.f.install(cfg,mods)
  self.assertFalse((h/'userdata/keep-before-preflight.txt').exists())
  actual=json.loads(p.read_text());self.assertEqual(actual['Movies'],CAT['defaults']['Movies']);self.assertEqual(actual['PreviewMode'],'manual');self.assertEqual(actual['Saved'],[{'id':9}]);self.assertEqual(actual['custom'],'keep')
  values=self.f.f.values(h/'userdata/addon_data/plugin.video.umbrella/settings.xml')
  for key,value in self.f.f.credentials.items():self.assertEqual(values[key],value)
  self.assertEqual(values['remove.hdr'],'true');self.assertEqual(self.f.f.values(h/'userdata/guisettings.xml')['locale.audiolanguage'],'English')
 def test_old_installer_refuses_before_cleanup_or_native_setup(self):
  k,cfg,mods=self.f.f.environment();path=self.package();m=types.ModuleType('old_preflight');m.__file__=str(network.umbrella_fixture.LIB/'platform_compatibility.py')
  exec(compile((ROOT/'tests/fixtures/platform_compatibility_1_0_21.py').read_text(),m.__file__,'exec'),m.__dict__)
  with patch.dict('sys.modules',mods),self.assertRaises(m.CompatibilityError):m.prepare(path,k,home=cfg.HOME)
  self.assertEqual(k.requests,[]);self.assertTrue((Path(cfg.HOME)/'userdata/keep-before-preflight.txt').exists())
 def test_unknown_or_weaker_preference_policy_cannot_use_discovery_to_bypass_safety(self):
  for preference in ('unknown-future-policy','playback-trakt-1'):
   self.f=network.NetworkInstallFlow();self.f.setUp();self.addCleanup(self.f.doCleanups)
   k,cfg,mods=self.f.f.environment();path=self.package()
   with zipfile.ZipFile(path) as z:data={n:z.read(n) for n in z.namelist()}
   policy=json.loads(data['userdata/blacklanturn-build.json']);policy['preferences_policy']=preference;data['userdata/blacklanturn-build.json']=json.dumps(policy).encode()
   with zipfile.ZipFile(path,'w') as z:
    for n,v in data.items():z.writestr(n,v)
   from resources.libs import platform_compatibility
   with patch.dict('sys.modules',mods),self.assertRaises(platform_compatibility.CompatibilityError):platform_compatibility.prepare(path,k,home=cfg.HOME)
   self.assertTrue((Path(cfg.HOME)/'userdata/keep-before-preflight.txt').exists());self.assertEqual(k.requests,[])

 def test_wrong_packaged_defaults_fail_before_cleanup(self):
  k,cfg,mods=self.f.f.environment();self.package(lambda data:data.__setitem__('userdata/addon_data/script.blacklanturn.preview/rows.json',b'{"Movies":[],"Shows":[]}'))
  self.f.f.install(cfg,mods);self.assertTrue((Path(cfg.HOME)/'userdata/keep-before-preflight.txt').exists());self.assertEqual(k.requests,[])
if __name__=='__main__':unittest.main()
