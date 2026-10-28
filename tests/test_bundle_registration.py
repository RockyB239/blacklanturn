"""New bundled addons must be usable, without enabling disabled user addons."""
import importlib.util,json,types,unittest
from pathlib import Path
from unittest.mock import patch
from test_inplace_update import InPlace as Fixture,meta,LIB
class Registration(unittest.TestCase):
 setUp=Fixture.setUp;seed=Fixture.seed;saved=Fixture.saved;archive=Fixture.archive;prepare=Fixture.prepare
 def registrar(self,fail=None):
  p=LIB/'addon_registration.py';self.assertTrue(p.is_file(),'No native new-addon registration step')
  s=importlib.util.spec_from_file_location('registration_test',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
  self.flags={'plugin.video.user':False};self.calls=[]
  def rpc(raw):
   q=json.loads(raw);a=q.get('params',{});aid=a.get('addonid');self.calls.append((q['method'],aid))
   if q['method']=='Addons.GetAddonDetails':
    path=self.home/'addons'/aid/'addon.xml'
    if not path.exists():return json.dumps({'error':{'message':'not installed'}})
    import xml.etree.ElementTree as E
    return json.dumps({'result':{'addon':{'version':E.parse(path).getroot().get('version'),'enabled':self.flags.get(aid,False)}}})
   if q['method']=='Addons.SetAddonEnabled':
    if aid==fail:return json.dumps({'error':{'message':'injected native failure'}})
    self.flags[aid]=a['enabled'];return json.dumps({'result':'OK'})
   raise AssertionError(q)
  self.registration_kodi=types.SimpleNamespace(executeJSONRPC=rpc,executebuiltin=lambda *a,**k:None)
  return m.Registrar(self.registration_kodi)
 def test_new_bundled_module_enabled_and_existing_disabled_user_untouched(self):
  import shutil
  shutil.rmtree(self.home/'addons'/self.aid);registrar=self.registrar();plan=self.prepare();self.m.apply(plan,registrar=registrar)
  self.assertTrue(self.flags[self.aid]);self.assertFalse(self.flags['plugin.video.user']);self.assertEqual(self.saved(),self.before)
 def test_existing_disabled_bundled_module_stays_disabled(self):
  registrar=self.registrar();self.m.apply(self.prepare(),registrar=registrar);self.assertNotIn(self.aid,self.flags);self.assertFalse(self.flags['plugin.video.user'])
 def test_registration_failure_rolls_back_source_and_completion(self):
  import shutil
  shutil.rmtree(self.home/'addons'/self.aid);registrar=self.registrar(fail=self.aid)
  with self.assertRaises(self.m.UpdateError):self.m.apply(self.prepare(),registrar=registrar)
  self.assertFalse((self.home/'addons'/self.aid).exists());self.assertEqual(json.loads((self.home/'userdata/blacklanturn-build.json').read_text()),self.marker);self.assertFalse((self.home/'userdata/blacklanturn-install-complete.json').exists());self.assertEqual(self.saved(),self.before)
 def test_partial_registration_failure_restores_prior_enabled_flags(self):
  import shutil
  shutil.rmtree(self.home/'addons'/self.aid);other='script.module.second';self.data['addons/'+other+'/addon.xml']=meta(other,'1')
  registrar=self.registrar(fail=other)
  with self.assertRaises(self.m.UpdateError):self.m.apply(self.prepare(),registrar=registrar)
  self.assertFalse(self.flags.get(self.aid));self.assertFalse((self.home/'addons'/other).exists());self.assertEqual(self.saved(),self.before)
 def test_release34_provider_registration_repair_is_limited_to_known_modules(self):
  aid='script.module.tmdbhelper.sync.trakt';self.target['build_version']='1.1.35';self.marker['build_version']='1.1.34';(self.home/'userdata/blacklanturn-build.json').write_text(json.dumps(self.marker));self.seed(aid,'1.1.0');self.data['addons/'+aid+'/addon.xml']=meta(aid,'1.1.0')
  registrar=self.registrar();self.m.apply(self.prepare(),registrar=registrar);self.assertTrue(self.flags[aid]);self.assertFalse(self.flags['plugin.video.user'])
 def test_later_release_does_not_reenable_user_disabled_provider(self):
  aid='script.module.tmdbhelper.sync.trakt';self.marker['build_version']='1.1.35';self.target['build_version']='1.1.36';(self.home/'userdata/blacklanturn-build.json').write_text(json.dumps(self.marker));self.seed(aid,'1.1.0');self.data['addons/'+aid+'/addon.xml']=meta(aid,'1.1.0')
  registrar=self.registrar();self.m.apply(self.prepare(),registrar=registrar);self.assertNotIn(aid,self.flags)

 def test_cold_recovery_restores_owned_registration_intent(self):
  import shutil
  shutil.rmtree(self.home/'addons'/self.aid);registrar=self.registrar();plan=self.prepare();registrar.snapshot(plan)
  state=plan['state'];state['status']='applying';state['registration'][self.aid]['started']=True;self.m._journal(plan,state);self.flags[self.aid]=True;self.m.release(plan)
  with patch.dict('sys.modules',{'xbmc':self.registration_kodi}):self.assertTrue(self.m.recover(self.home))
  self.assertFalse(self.flags[self.aid]);self.assertFalse(self.flags['plugin.video.user']);self.assertEqual(self.saved(),self.before)

 def test_foreign_registration_journal_cannot_toggle_user_addon(self):
  registrar=self.registrar();plan=self.prepare();registrar.snapshot(plan);state=plan['state'];state['registration']['plugin.video.user']={'enabled_before':True,'existed_before':True,'started':True,'version':'7'}
  import importlib.util
  spec=importlib.util.spec_from_file_location('restore_contract',LIB/'addon_registration.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  with self.assertRaises(module.RegistrationError):module.restore(state,self.registration_kodi)
  self.assertEqual(self.calls,[]);self.assertFalse(self.flags['plugin.video.user']);state['registration']={};self.m.cancel(plan)

del Fixture
