"""Actual OpenWizard cleanup/extract with synthetic accounts and complete packaged YouTube."""
import hashlib,importlib.util,json,sqlite3,types,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
import test_network_install_flow as fixture
ROOT=Path(__file__).resolve().parents[1];LIB=ROOT/'installer-source/plugin.program.blacklanturninstaller/resources/libs'
POLICY=dict(fixture.POLICY,preferences_policy='playback-trakt-youtube-umbrella-network-autoplay-1',autoplay_patch='same-show-source-1',discovery_patch='discovery-first-page-1',youtube_refresh_patch='youtube-freshness-1',installer_min_version='1.0.23')
class RefreshInstallFlow(unittest.TestCase):
 def setUp(self):
  self.f=fixture.NetworkInstallFlow();self.f.setUp();self.addCleanup(self.f.doCleanups);self.addCleanup(self.f.f.tearDown)
 def packaged(self,edition='apple',mutate=None):
  baseline=ROOT/'baselines'
  if not baseline.is_dir():baseline=ROOT.parents[1]/'helper-managed-release-1.1.2/artifacts'
  label='General' if edition=='general' else 'Apple-TV-Mac'
  with zipfile.ZipFile(baseline/f'BlackLanturn-{label}-Kodi21-1.1.2.zip') as z:
   data={n:z.read(n) for n in z.namelist() if n.startswith('addons/plugin.video.youtube/')}
  key='addons/plugin.video.youtube/resources/lib/youtube_plugin/kodion/sql_store/function_cache.py'
  data[key]=(ROOT/'compatibility/youtube-refresh/candidate/function_cache.py').read_bytes()
  data['userdata/addon_data/plugin.video.youtube/settings.xml']=b'<settings><setting id="kodion.history.remote">true</setting><setting id="kodion.history.local">true</setting></settings>'
  defaults=json.loads((LIB.parent/'playback-defaults.json').read_text())['addon_data/plugin.video.youtube/settings.xml']
  import xml.etree.ElementTree as E
  tree=E.fromstring(data['userdata/addon_data/plugin.video.youtube/settings.xml'])
  for k,v in defaults.items():E.SubElement(tree,'setting',id=k).text=v
  data['userdata/addon_data/plugin.video.youtube/settings.xml']=E.tostring(tree)
  catalogue=json.loads((LIB.parent/'discovery-lineup.json').read_text())
  data['userdata/addon_data/script.blacklanturn.preview/rows.json']=json.dumps(catalogue['defaults']).encode()
  # Existing network fixture supplies all other complete managed code/defaults.
  original=self.f.f.packaged
  def package(change=None,policy=None):
   def merge(d):
    if change:change(d)
    d.update(data)
    if mutate:mutate(d)
   return original(change=merge,policy=dict(POLICY,edition=edition))
  with patch.object(self.f.f,'packaged',package):return self.f.packaged()
 def test_standard_preserves_explicit_history_privacy_and_authorizations(self):
  k,cfg,mods=self.f.f.environment();self.packaged();h=Path(cfg.HOME)
  p=h/'userdata/addon_data/plugin.video.youtube/settings.xml';p.write_bytes(p.read_bytes().replace(b'</settings>',b'<setting id="kodion.history.remote">false</setting></settings>'))
  self.f.f.install(cfg,mods)
  self.assertFalse((h/'userdata/keep-before-preflight.txt').exists(),'Did not install')
  self.assertEqual(self.f.f.values(p)['kodion.history.remote'],'false')
  self.assertEqual((h/'userdata/addon_data/plugin.video.youtube/access_manager.json').read_bytes(),b'{"fixture":{"refresh_token":"private-refresh"}}')
  with sqlite3.connect(h/'userdata/Database/Addons33.db') as db:self.assertIn(('plugin.video.youtube',1),db.execute('select addonID,updateRule from update_rules').fetchall())
 def test_account_only_clean_uses_history_default_and_preserves_selected_accounts(self):
  k,cfg,mods=self.f.f.environment(auth_only=True);self.packaged();h=Path(cfg.HOME);self.f.f.install(cfg,mods)
  self.assertFalse((h/'userdata/keep-before-preflight.txt').exists(),'Did not install')
  self.assertEqual(self.f.f.values(h/'userdata/addon_data/plugin.video.youtube/settings.xml')['kodion.history.remote'],'true')
  self.assertTrue((h/'userdata/addon_data/plugin.video.youtube/access_manager.json').is_file())
 def test_installer22_rejects_new_payload_before_setup(self):
  k,cfg,mods=self.f.f.environment();path=self.packaged();m=types.ModuleType('old22');m.__file__=str(LIB/'platform_compatibility.py');exec(compile((ROOT/'tests/fixtures/platform_compatibility_1_0_22.py').read_text(),m.__file__,'exec'),m.__dict__)
  with patch.dict('sys.modules',mods),self.assertRaises(m.CompatibilityError):m.prepare(path,k,home=cfg.HOME)
  self.assertEqual(k.requests,[])
 def test_missing_or_unknown_history_patch_fails_without_cleanup(self):
  k,cfg,mods=self.f.f.environment()
  def change(d):
   p=json.loads(d['userdata/blacklanturn-build.json']);p['youtube_refresh_patch']='unknown';d['userdata/blacklanturn-build.json']=json.dumps(p).encode()
  # Mutate policy via direct archive rewrite after packaging.
  path=self.packaged()
  with zipfile.ZipFile(path) as z:d={n:z.read(n) for n in z.namelist()}
  change(d)
  with zipfile.ZipFile(path,'w') as z:
   for n,b in d.items():z.writestr(n,b)
  self.f.f.install(cfg,mods);self.assertTrue((Path(cfg.HOME)/'userdata/keep-before-preflight.txt').exists());self.assertEqual(k.requests,[])
