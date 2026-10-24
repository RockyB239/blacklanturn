import json,unittest
from pathlib import Path
import test_build_preferences as f
class ReleaseNoticeInstalls(unittest.TestCase):
 def env(self):
  x=f.BuildPreferences();x.setUp();self.addCleanup(x.doCleanups);return x,x.home/'userdata/addon_data/script.blacklanturn.preview/release-notices.json',f.IDS+['script.blacklanturn.preview']
 def state(self):return {'schema':2,'enabled':False,'installed':{'edition':'general','version':'1.1.19','revision':0},'available':None,'completed':None,'history':[],'seen':['available:old-release']}
 def test_standard_update_retains_release_preference_and_history(self):
  x,p,ids=self.env();p.parent.mkdir(parents=True,exist_ok=True);s=self.state();p.write_text(json.dumps(s));a=x.m.prepare(x.home,x.accounts(),ids,False);p.unlink();x.m.restore(x.home,a,ids);self.assertTrue(p.exists(),'Standard erased release notices');self.assertEqual(json.loads(p.read_text()),s)
 def test_first_upgrade_migrates_only_notice_preference_and_old_build_baseline(self):
  x,p,ids=self.env();p.parent.mkdir(parents=True,exist_ok=True);(p.parent/'update-notes.json').write_text(json.dumps({'schema':1,'enabled':False,'inventory':{},'history':[],'seen':0,'sequence':0}));(x.home/'userdata/blacklanturn-build.json').write_text(json.dumps({'edition':'general','build_version':'1.1.19'}));a=x.m.prepare(x.home,x.accounts(),ids,False);self.assertIn('release_notices',a['build_preferences']);s=a['build_preferences']['release_notices'];self.assertFalse(s['enabled']);self.assertEqual(s['installed'],{'edition':'general','version':'1.1.19','revision':0});self.assertEqual(s['history'],[])
 def test_clean_install_does_not_restore_prior_release_state(self):
  x,p,ids=self.env();p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(self.state()));a=x.m.prepare(x.home,x.accounts(),ids,True);p.unlink();x.m.restore(x.home,a,ids);self.assertFalse(p.exists())
 def test_completion_receipt_is_explicit_and_matches_installed_marker(self):
  x,p,ids=self.env();marker=x.home/'userdata/blacklanturn-build.json';marker.parent.mkdir(parents=True,exist_ok=True);marker.write_text(json.dumps({'edition':'general','build_version':'1.1.20','release_revision':0,'release_notices':'curated-releases-1','release_id':'blacklanturn-general-1.1.20-r0'}));self.assertTrue(callable(getattr(x.m,'complete_install',None)),'Installer lacks success receipt');receipt=x.home/'userdata/blacklanturn-install-complete.json';self.assertFalse(receipt.exists());x.m.complete_install(x.home);self.assertEqual(json.loads(receipt.read_text()),{'schema':1,'id':'blacklanturn-general-1.1.20-r0','edition':'general','version':'1.1.20','revision':0,'complete':True})

 def test_registry_protection_failure_does_not_leave_success_receipt(self):
  import test_umbrella_install_flow as fixture
  x=fixture.UmbrellaInstallFlow();x.setUp();self.addCleanup(x.tearDown)
  k,cfg,mods=x.environment();policy=dict(fixture.POLICY,build_version='1.1.20',release_notices='curated-releases-1',release_revision=0,release_id='blacklanturn-apple-1.1.20-r0');x.packaged(policy=policy)
  from resources.libs import managed_addons as module
  original=module.protect;calls=[]
  def protect(*a,**kw):
   calls.append(1)
   if len(calls)==2:raise module.ProtectionError('synthetic late registry failure')
   return original(*a,**kw)
  from unittest.mock import patch
  with patch.object(module,'protect',side_effect=protect):x.install(cfg,mods)
  self.assertEqual(len(calls),2);self.assertFalse((Path(cfg.HOME)/'userdata/blacklanturn-install-complete.json').exists(),'A late failed install was marked successful')
