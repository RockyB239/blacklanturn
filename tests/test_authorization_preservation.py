import ast,importlib.util,json,tempfile,unittest,xml.etree.ElementTree as E
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'installer-source/plugin.program.blacklanturninstaller/resources/libs'
import sys
sys.path.insert(0,str(ROOT.parents[1]))
class AuthorizationPreservation(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.home=Path(self.tmp.name)
  spec=importlib.util.spec_from_file_location('auth',ROOT/'authorizations.py');self.m=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.m)
 def settings(self,aid,data):
  p=self.home/'userdata/addon_data'/aid/'settings.xml';p.parent.mkdir(parents=True,exist_ok=True);r=E.Element('settings',version='2')
  for k,v in data.items():E.SubElement(r,'setting',id=k).text=v
  E.ElementTree(r).write(p,encoding='utf-8');return p
 def test_current_umbrella_and_helper_tokens_survive_without_preferences(self):
  aid='plugin.video.umbrella';p=self.settings(aid,{'trakt.user.token':'t','alldebridtoken':'a','torboxtoken':'b','mdblist.token':'m','cache.traktpopular':'120','remove.hdr':'true'})
  h='plugin.video.themoviedb.helper';q=self.settings(h,{'trakt_token':'{"access":"secret"}','tmdb_user_token':'tmdb','mdblist_apikey':'key','pagemulti_trakt':'9'})
  snap=self.m.capture(self.home,[aid,h],{'trakt','debrid','login'})
  self.settings(aid,{'remove.hdr':'false'});self.settings(h,{'pagemulti_trakt':'1'})
  self.m.restore(self.home,snap,[aid,h]);d={x.get('id'):x.text for x in E.parse(p).getroot()};v={x.get('id'):x.text for x in E.parse(q).getroot()}
  self.assertEqual(d,{'remove.hdr':'false','trakt.user.token':'t','alldebridtoken':'a','torboxtoken':'b','mdblist.token':'m'});self.assertEqual(v['pagemulti_trakt'],'1');self.assertEqual(v['trakt_token'],'{"access":"secret"}')
 def test_disabled_categories_and_absent_build_addons_not_preserved(self):
  a='plugin.video.umbrella';self.settings(a,{'trakt.user.token':'t','alldebridtoken':'a'})
  s=self.m.capture(self.home,[a],{'trakt'});self.settings(a,{})
  self.m.restore(self.home,s,[a]);d={x.get('id'):x.text for x in E.parse(self.home/'userdata/addon_data'/a/'settings.xml').getroot()};self.assertEqual(d,{'trakt.user.token':'t'})
  self.assertEqual(self.m.capture(self.home,[],{'trakt','login','debrid'})['settings'],{})
 def test_youtube_private_account_json_preserved_exactly(self):
  d=self.home/'userdata/addon_data/plugin.video.youtube';d.mkdir(parents=True)
  raw=b'{"access_manager":{"users":{"0":{"refresh_token":"secret"}}}}';(d/'access_manager.json').write_bytes(raw);(d/'api_keys.json').write_text('{"keys":{"user":{"api_key":"private"}}}')
  s=self.m.capture(self.home,['plugin.video.youtube'],{'login'});(d/'access_manager.json').unlink();self.m.restore(self.home,s,['plugin.video.youtube']);self.assertEqual((d/'access_manager.json').read_bytes(),raw)
  self.assertEqual(self.m.capture(self.home,['plugin.video.youtube'],set())['files'],{})
 def test_malformed_selected_auth_file_stops_before_wipe(self):
  p=self.home/'userdata/addon_data/plugin.video.youtube/access_manager.json';p.parent.mkdir(parents=True);p.write_text('{broken')
  with self.assertRaises(self.m.AuthorizationError):self.m.capture(self.home,['plugin.video.youtube'],{'login'})
 def test_untrusted_snapshot_cannot_restore_extra_file_or_setting(self):
  for s in [{'schema':1,'settings':{'plugin.video.umbrella':{'remove.hdr':'true'}},'files':{}},{'schema':1,'settings':{},'files':{'../../escape':'value'}}]:
   with self.assertRaises(self.m.AuthorizationError):self.m.restore(self.home,s,['plugin.video.umbrella'])
 def test_read_only_snapshot_roundtrip_and_size_limit(self):
  self.settings('script.trakt',{'authorization':'secret','user':'name','scrobble_movie':'false'});s=self.m.capture(self.home,['script.trakt'],{'trakt'});p=self.home/'private.json';self.m.save(p,s);self.assertEqual(self.m.load(p),s);self.assertEqual(p.stat().st_mode&0o777,0o600)
  p.write_text('x'*(self.m.MAX_BYTES+1))
  with self.assertRaises(self.m.AuthorizationError):self.m.load(p)
 def test_wizard_saves_before_cleanup_restores_before_restart(self):
  t=ast.parse((ROOT/'wizard.py').read_text());fn=next(n for c in t.body if isinstance(c,ast.ClassDef) for n in c.body if isinstance(n,ast.FunctionDef) and n.name=='build');calls=[ast.unparse(n.func) for n in ast.walk(fn) if isinstance(n,ast.Call)]
  for name in ['authorizations.prepare','authorizations.restore']:self.assertIn(name,calls)
  s=ast.unparse(fn);self.assertLess(s.index('authorizations.prepare('),s.index('install.wipe('));self.assertLess(s.index('authorizations.restore('),s.index('tools.kill_kodi('))

 def test_new_build_restore_is_not_overwritten_by_legacy_startup(self):
  startup=(ROOT.parents[1]/'startup.py').read_text()
  self.assertIn("CONFIG.get_setting('authorizationsrestored') != 'true'",startup)
  wizard=(ROOT/'wizard.py').read_text()
  self.assertIn('install.wipe(accounts_prepared=protected_helper, auth_only=auth_only)',wizard)
  self.assertIn("CONFIG.set_setting('authorizationsrestored', 'true' if protected_helper else 'false')",wizard)
 def test_password_based_accounts_keep_complete_login_not_just_token(self):
  aid='plugin.video.umbrella';values={'opensubsusername':'u','opensubspassword':'p','opensubstoken':'t','tmdbusername':'u','tmdbpassword':'p','tmdb.sessionid':'s'}
  self.settings(aid,values);snap=self.m.capture(self.home,[aid],{'login'});self.assertEqual(snap['settings'][aid],values)
 def test_failed_install_retry_reuses_original_pending_authorizations(self):
  aid='plugin.video.umbrella';self.settings(aid,{'trakt.user.token':'original'});pending=self.home/'private/pending.json'
  first=self.m.prepare(self.home,[aid],{'trakt'},pending);self.settings(aid,{})
  second=self.m.prepare(self.home,[aid],{'trakt'},pending);self.assertEqual(second,first);self.assertEqual(second['settings'][aid]['trakt.user.token'],'original')
  with self.assertRaises(self.m.AuthorizationError):self.m.prepare(self.home,[aid],{'login'},pending)
  self.m.restore(self.home,second,[aid]);self.m.commit(pending,self.home/'private/last-success.json');self.assertFalse(pending.exists())
  self.settings(aid,{'trakt.user.token':'new-account'});third=self.m.prepare(self.home,[aid],{'trakt'},pending);self.assertEqual(third['settings'][aid]['trakt.user.token'],'new-account')
 def test_malformed_pending_is_rejected_before_cleanup(self):
  p=self.home/'pending.json';p.write_text(json.dumps({'schema':1,'addon_ids':['plugin.video.umbrella'],'categories':['trakt'],'settings':None,'files':{}}))
  with self.assertRaises(self.m.AuthorizationError):self.m.prepare(self.home,['plugin.video.umbrella'],{'trakt'},p)
 def test_restore_skip_flag_is_only_set_with_successful_install(self):
  s=(ROOT/'wizard.py').read_text();self.assertIn("CONFIG.set_setting('authorizationsrestored', 'false')",s)
  self.assertLess(s.index("CONFIG.set_setting('installed', 'true')"),s.index("CONFIG.set_setting('authorizationsrestored', 'true' if protected_helper else 'false')"))

 def test_native_virtual_account_xml_is_captured_and_restored(self):
  from unittest.mock import patch
  import types
  path=self.home/'userdata/addon_data/plugin.video.themoviedb.helper/settings.xml';key=str(path);store={key:b'<settings><setting id="trakt_token">original-private-token</setting><setting id="trakt_watchedindicators">true</setting></settings>'}
  class File:
   def __init__(self,path,mode=None):self.path=path
   def size(self):return len(store[self.path])
   def readBytes(self):return store[self.path]
   def write(self,text):store[self.path]=text.encode();return True
   def close(self):pass
  fake=types.SimpleNamespace(exists=lambda p:p in store,File=File,mkdirs=lambda p:True,delete=lambda p:store.pop(p,None))
  # The module must support native VFS-backed settings; ordinary Path.exists is false.
  io=getattr(self.m,'store',None);self.assertIsNotNone(io,'Account preservation ignores virtual XML')
  with patch.object(io,'xbmcvfs',fake):
   snap=self.m.capture(self.home,['plugin.video.themoviedb.helper'],{'trakt'});self.assertEqual(snap['settings']['plugin.video.themoviedb.helper']['trakt_token'],'original-private-token')
   store[key]=b'<settings><setting id="trakt_watchedindicators">true</setting></settings>';self.m.restore(self.home,snap,['plugin.video.themoviedb.helper']);values={n.get('id'):n.text for n in E.fromstring(store[key])};self.assertEqual(values['trakt_token'],'original-private-token');self.assertEqual(values['trakt_watchedindicators'],'true')

from test_compatibility import CompatibilityTests,Kodi
from unittest.mock import patch
class AccountOnlyCleanup(CompatibilityTests):
 def test_account_only_cleanup_resets_native_preferences_and_removes_old_python_modules(self):
  cfg,mods=self.install_environment(Kodi());h=Path(cfg.HOME)
  native=h/'addons/inputstream.adaptive/native.so';native.parent.mkdir(parents=True);native.write_bytes(b'native')
  prefs=h/'userdata/addon_data/inputstream.adaptive/settings.xml';prefs.parent.mkdir(parents=True);prefs.write_text('old preferences')
  stale=h/'addons/script.module.web-pdb/stale.py';stale.parent.mkdir(parents=True);stale.write_text('stale')
  with patch.dict(__import__('sys').modules,mods):mods['resources.libs.install'].wipe(auth_only=True)
  self.assertTrue(native.exists());self.assertFalse(prefs.exists());self.assertFalse(stale.exists())
 def test_disabled_whitelist_cannot_skip_packaged_addons_after_wipe(self):
  cfg,mods=self.install_environment(Kodi());h=Path(cfg.HOME);cfg.KEEPWHITELIST='false'
  stale=h/'addons/skin.test/old.py';stale.parent.mkdir(parents=True);stale.write_text('old')
  source=self.archive(None,{'addons/skin.test/new.py':'new release'})
  mods['resources.libs.whitelist']=__import__('types').SimpleNamespace(whitelist=lambda mode:[('Skin','skin.test','skin.test')])
  mods['resources.libs.common.tools'].convert_size=lambda value:str(value)
  with patch.dict(__import__('sys').modules,mods):
   mods['resources.libs.install'].wipe(auth_only=True)
   spec=importlib.util.spec_from_file_location('extract_whitelist_test',ROOT/'extract.py');ex=importlib.util.module_from_spec(spec);spec.loader.exec_module(ex);result=ex.all(str(source),cfg.HOME)
  self.assertEqual(result[:2],(100,0));self.assertEqual((h/'addons/skin.test/new.py').read_text(),'new release');self.assertFalse(stale.exists())
