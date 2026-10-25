"""In-place updates replace bundled code only; saved and third-party data stay put."""
import importlib.util,json,os,shutil,sys,tempfile,types,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
R=Path(__file__).resolve().parents[1]
LIB=R/'installer-source/plugin.program.blacklanturninstaller/resources/libs'
def meta(aid,version='1',deps=''):
 return ('<addon id="'+aid+'" version="'+version+'"><requires><import addon="xbmc.python" version="3.0.1"/>'+deps+'</requires><extension point="xbmc.python.module" library="lib"/></addon>').encode()
class InPlace(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name).resolve();self.home=self.root/'home';(self.home/'addons').mkdir(parents=True);(self.home/'userdata').mkdir()
  spec=importlib.util.spec_from_file_location('inplace_test',LIB/'inplace_update.py');self.m=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.m)
  self.marker={'schema':3,'edition':'apple','build_version':'1.1.23','release_revision':0,'release_id':'blacklanturn-apple-1.1.23-r0','release_notices':'curated-releases-1'}
  (self.home/'userdata/blacklanturn-build.json').write_text(json.dumps(self.marker))
  self.aid='script.module.bundled';self.seed(self.aid,'1',{'obsolete.py':b'old'})
  self.seed('plugin.video.user','7',{'private.py':b'custom code'})
  for rel in ('guisettings.xml','sources.xml','profiles.xml','advancedsettings.xml','playercorefactory.xml','favourites.xml','Database/MyVideos131.db','addon_data/plugin.video.user/settings.xml','addon_data/plugin.video.youtube/0/history.sqlite','addon_data/plugin.video.umbrella/settings.xml','addon_data/script.blacklanturn.preview/rows.json'):
   p=self.home/'userdata'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(('personal:'+rel).encode())
  self.before=self.saved();self.data={'addons/'+self.aid+'/addon.xml':meta(self.aid,'2'),'addons/'+self.aid+'/lib/new.py':b'new code','userdata/guisettings.xml':b'BUILD DEFAULT MUST NEVER REPLACE','userdata/addon_data/plugin.video.umbrella/settings.xml':b'BUILD AUTH MUST NEVER REPLACE'}
  self.target=dict(self.marker,build_version='1.1.24',release_id='blacklanturn-apple-1.1.24-r0')
  self.kodi=types.SimpleNamespace(executeJSONRPC=lambda req:json.dumps({'error':{'message':'not installed'}}))
  self.compat=types.SimpleNamespace(prepare=lambda *a,**k:{'policy':self.target,'addon_ids':[self.aid]})
  self.libs=types.ModuleType('resources.libs');self.libs.platform_compatibility=self.compat
  self.modules={'resources':types.ModuleType('resources'),'resources.libs':self.libs,'resources.libs.platform_compatibility':self.compat}
  self.resources=patch.dict(sys.modules,self.modules);self.resources.start();self.addCleanup(self.resources.stop)
 def seed(self,aid,v,extra=None,deps=''):
  p=self.home/'addons'/aid;p.mkdir(parents=True,exist_ok=True);(p/'addon.xml').write_bytes(meta(aid,v,deps));(p/'lib').mkdir(exist_ok=True);(p/'lib/main.py').write_bytes(b'original module')
  for n,raw in (extra or {}).items():(p/n).write_bytes(raw)
 def saved(self):return {p.relative_to(self.home).as_posix():p.read_bytes() for p in (self.home/'userdata').rglob('*') if p.is_file() and p.name not in ('blacklanturn-build.json','blacklanturn-releases.json','blacklanturn-install-complete.json')}|{p.relative_to(self.home).as_posix():p.read_bytes() for p in (self.home/'addons/plugin.video.user').rglob('*') if p.is_file()}
 def archive(self):
  self.data['userdata/blacklanturn-build.json']=json.dumps(self.target).encode();self.data['userdata/blacklanturn-releases.json']=b'{"schema":1,"releases":[]}'
  p=self.root/'build.zip'
  with zipfile.ZipFile(p,'w') as z:
   for n,raw in self.data.items():z.writestr(n,raw)
  return p
 def prepare(self):return self.m.prepare(self.archive(),self.home,self.kodi)
 def test_updates_complete_tree_without_touching_any_saved_or_unrelated_data(self):
  plan=self.prepare();self.m.apply(plan)
  self.assertEqual(self.saved(),self.before);self.assertFalse((self.home/'addons'/self.aid/'obsolete.py').exists());self.assertEqual((self.home/'addons'/self.aid/'lib/new.py').read_bytes(),b'new code')
  self.assertEqual(json.loads((self.home/'userdata/blacklanturn-build.json').read_text()),self.target)
  self.assertTrue(json.loads((self.home/'userdata/blacklanturn-install-complete.json').read_text())['complete'])
 def test_downloaded_userdata_is_never_staged(self):
  plan=self.prepare();self.assertFalse((Path(plan['work'])/'new/userdata/guisettings.xml').exists());self.m.cancel(plan)
 def test_newer_ordinary_addon_is_retained_as_a_whole_tree(self):
  self.seed(self.aid,'5',{'custom.py':b'newer'});old={p.relative_to(self.home/'addons'/self.aid).as_posix():p.read_bytes() for p in (self.home/'addons'/self.aid).rglob('*') if p.is_file()}
  plan=self.prepare();self.m.apply(plan)
  self.assertEqual({p.relative_to(self.home/'addons'/self.aid).as_posix():p.read_bytes() for p in (self.home/'addons'/self.aid).rglob('*') if p.is_file()},old)
 def test_addon_not_previously_installed_is_added(self):
  shutil.rmtree(self.home/'addons'/self.aid);self.m.apply(self.prepare());self.assertTrue((self.home/'addons'/self.aid/'lib/new.py').exists())
 def test_wrong_edition_refuses_before_any_change(self):
  self.target['edition']='general'
  with self.assertRaises(self.m.UpdateError):self.prepare()
  self.assertEqual(self.saved(),self.before)
 def test_fresh_profile_requires_install_instead_of_update(self):
  (self.home/'userdata/blacklanturn-build.json').unlink()
  with self.assertRaises(self.m.UpdateError):self.prepare()
 def test_build_downgrade_refuses(self):
  self.target['build_version']='1.1.20'
  with self.assertRaises(self.m.UpdateError):self.prepare()
 def test_foreign_dependency_minimum_prevents_breaking_user_addon(self):
  self.seed('plugin.video.user','7',deps='<import addon="'+self.aid+'" version="3"/>')
  with self.assertRaises(self.m.UpdateError):self.prepare()
 def test_unchanged_native_api_dependencies_remain_kodi_owned(self):
  self.seed('inputstream.adaptive','21.5',deps='<import addon="kodi.binary.global.main" version="2.0.0"/>')
  self.m.apply(self.prepare());self.assertTrue((self.home/'addons/inputstream.adaptive/addon.xml').exists())
 def test_missing_dependency_refuses(self):
  self.data['addons/'+self.aid+'/addon.xml']=meta(self.aid,'2','<import addon="script.module.missing" version="1"/>')
  with self.assertRaises(self.m.UpdateError):self.prepare()
 def test_concurrent_update_refuses_without_discarding_first_staging(self):
  plan=self.prepare()
  try:
   with self.assertRaises(self.m.UpdateError):self.prepare()
   self.assertTrue(Path(plan['work']).exists())
  finally:self.m.cancel(plan)
 def test_target_link_refuses_without_following_link(self):
  root=self.home/'addons'/self.aid;shutil.rmtree(root);root.symlink_to(self.home/'addons/plugin.video.user',target_is_directory=True)
  with self.assertRaises(self.m.UpdateError):self.prepare()
 def test_linked_userdata_refuses(self):
  root=self.home/'userdata';root.rename(self.home/'saved');root.symlink_to(self.home/'saved',target_is_directory=True)
  with self.assertRaises(self.m.UpdateError):self.prepare()
 def test_stage_failure_changes_no_installed_files(self):
  with patch.object(self.m,'_write',side_effect=OSError('disk full')):
   with self.assertRaises(self.m.UpdateError):self.prepare()
  self.assertTrue((self.home/'addons'/self.aid/'obsolete.py').exists());self.assertEqual(self.saved(),self.before)
 def test_rename_failure_rolls_back_all_code_and_marker(self):
  plan=self.prepare();real=os.replace
  def fail(src,dst):
   if str(src).endswith('/new/'+self.aid):raise OSError('injected rename failure')
   return real(src,dst)
  with patch.object(self.m.os,'replace',side_effect=fail):
   with self.assertRaises(self.m.UpdateError):self.m.apply(plan)
  self.assertTrue((self.home/'addons'/self.aid/'obsolete.py').exists());self.assertEqual(json.loads((self.home/'userdata/blacklanturn-build.json').read_text()),self.marker);self.assertEqual(self.saved(),self.before)
 def test_crash_after_old_tree_move_recovers_previous_complete_tree(self):
  plan=self.prepare();real=os.replace
  def crash(src,dst):
   result=real(src,dst)
   if str(dst).endswith('/old/'+self.aid):raise KeyboardInterrupt('simulated process exit')
   return result
  with patch.object(self.m.os,'replace',side_effect=crash):
   with self.assertRaises(KeyboardInterrupt):self.m.apply(plan)
  self.m.release(plan);self.assertTrue(self.m.recover(self.home));self.assertTrue((self.home/'addons'/self.aid/'obsolete.py').exists());self.assertEqual(self.saved(),self.before)
 def test_commit_metadata_failure_rolls_back(self):
  plan=self.prepare();real=self.m._write
  def fail(path,raw):
   if str(path).endswith('blacklanturn-install-complete.json'):raise OSError('disk full')
   return real(path,raw)
  with patch.object(self.m,'_write',side_effect=fail):
   with self.assertRaises(self.m.UpdateError):self.m.apply(plan)
  self.assertTrue((self.home/'addons'/self.aid/'obsolete.py').exists());self.assertEqual(json.loads((self.home/'userdata/blacklanturn-build.json').read_text()),self.marker)
 def test_change_after_preflight_refuses_before_replacement(self):
  plan=self.prepare();(self.home/'addons'/self.aid/'obsolete.py').write_bytes(b'changed by another updater')
  with self.assertRaises(self.m.UpdateError):self.m.apply(plan)
  self.assertEqual((self.home/'addons'/self.aid/'obsolete.py').read_bytes(),b'changed by another updater')
 def test_untrusted_archive_path_refuses(self):
  self.data['addons/'+self.aid+'/../../userdata/damage']=b'bad'
  with self.assertRaises(self.m.UpdateError):self.prepare()
 def test_committed_cleanup_still_holds_writer_lock(self):
  plan=self.prepare();original=self.m.shutil.rmtree;observed=[]
  def cleanup(path,*a,**k):
   if Path(path)==Path(plan['work']):
    try:
     second=self.m._lock(self.home)
    except self.m.UpdateError:observed.append('locked')
    else:
     self.m.release(second);observed.append('unlocked')
   return original(path,*a,**k)
  with patch.object(self.m.shutil,'rmtree',side_effect=cleanup):self.m.apply(plan)
  self.assertEqual(observed,['locked'])
 def test_interrupted_rollback_of_new_addon_can_resume(self):
  shutil.rmtree(self.home/'addons'/self.aid);plan=self.prepare();real_write=self.m._write;real_remove=self.m.shutil.rmtree
  def fail_metadata(path,raw):
   if str(path).endswith('blacklanturn-install-complete.json'):raise OSError('commit failed')
   return real_write(path,raw)
  def interrupt_delete(path,*a,**kw):
   root=Path(path)
   if root in (Path(plan['work']),self.home/'addons'/self.aid):
    candidates=list(root.rglob('addon.xml'))
    if candidates:candidates[0].unlink()
    raise KeyboardInterrupt('interrupted rollback cleanup')
   return real_remove(path,*a,**kw)
  with patch.object(self.m,'_write',side_effect=fail_metadata),patch.object(self.m.shutil,'rmtree',side_effect=interrupt_delete):
   with self.assertRaises(KeyboardInterrupt):self.m.apply(plan)
  self.m.recover(self.home);self.assertFalse((self.home/'addons'/self.aid).exists());self.assertEqual(self.saved(),self.before)
 def test_no_cleanup_accounts_settings_or_skin_helpers_are_called(self):
  source=(LIB/'inplace_update.py').read_text();self.assertNotIn('install.wipe(',source);self.assertNotIn('extract.all(',source);self.assertNotIn('authorizations.restore(',source);self.assertNotIn('skin_to_default(',source)
