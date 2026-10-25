import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
from update_notes import notice_allowed
class NoticeGateTests(unittest.TestCase):
 def test_safe_idle_home_only(self):
  good=dict(home=True,loading=False,playing=False,dialog=False,settings=False,idle=8)
  self.assertTrue(notice_allowed(**good))
  for key in ('home','loading','playing','dialog','settings'):
   altered=dict(good);altered[key]=not altered[key];self.assertFalse(notice_allowed(**altered),key)
  self.assertFalse(notice_allowed(**dict(good,idle=7)))
 def test_notice_layout_in_safe_margins(self):
  from xml.etree import ElementTree as E
  root=Path(__file__).resolve().parents[1]/'addon/resources/skins/Default/1080i'
  for name in ('UpdateNotice.xml','UpdateNotes.xml'):
   tree=E.parse(root/name)
   for node in tree.findall('.//control'):
    values=[node.findtext(k) for k in ('left','top','width','height')]
    if all(v is not None and v.isdigit() for v in values):
     x,y,w,h=map(int,values)
     if node.findtext('colordiffuse')=='99000000' and (x,y,w,h)==(0,0,1920,1080):continue # full-screen dimming behind notes only
     self.assertLessEqual(x+w,1870,name);self.assertLessEqual(y+h,1030,name)

class HomeUpdatesRuntimeTests(unittest.TestCase):
 def setUp(self):
  import importlib.util,tempfile,types,json
  from unittest.mock import patch
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.calls=[]
  class Window:
   def __init__(self,*args):self.props={};self.closed=False
   def setProperty(self,k,v):self.props[k]=v
   def getProperty(self,k):return self.props.get(k,'')
   def setFocusId(self,cid):self.focus=cid
   def close(self):self.closed=True
  fake=types.SimpleNamespace(Player=lambda:types.SimpleNamespace(isPlaying=lambda:self.playing),getGlobalIdleTime=lambda:10,LOGWARNING=2,log=lambda *a:self.calls.append('error'),Monitor=lambda:types.SimpleNamespace(waitForAbort=lambda t:False))
  self.playing=False
  self.session=Window()
  modules={'xbmc':fake,'xbmcgui':types.SimpleNamespace(WindowXMLDialog=Window,Window=lambda wid:self.session,getCurrentWindowDialogId=lambda:0),'xbmcaddon':types.SimpleNamespace(),'xbmcvfs':types.SimpleNamespace()}
  with patch.dict(sys.modules,modules):
   spec=importlib.util.spec_from_file_location('update_ui_test',Path(__file__).resolve().parents[1]/'addon/update_notes_ui.py');self.ui=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.ui)
  self.path=Path(self.temp.name)/'state.json';self.ui.state_path=lambda:self.path
  from release_updates import refresh,write_state
  import hashlib
  f=Path(self.temp.name)/'addons/example/main.py';f.parent.mkdir(parents=True);f.write_text('release')
  release={'id':'release2','edition':'apple','version':'1.1.20','revision':0,'title':'BlackLanturn 1.1.20','summary':'Our tested changes.','sections':[{'heading':'Playback','bullets':['Our playback changes.']}],'files':{'addons/example/main.py':hashlib.sha256(b'release').hexdigest()}}
  self.state=refresh({}, {'edition':'apple','build_version':'1.1.19'}, {'schema':1,'releases':[release]},1,Path(self.temp.name));write_state(self.path,self.state)
  self.ui.legacy_path=lambda:Path(self.temp.name)/'old.json'
  self.owner=types.SimpleNamespace(alive=True,window_lifetime=object(),mode='home',nav=False,settings_open=False,actions_open=False,getProperty=lambda k:'false')
  self.runtime=self.ui.HomeUpdates(self.owner,lambda *a:{})
  self.runtime.state=self.state;self.runtime.due=float('inf')
  calls=self.calls
  class Notice(Window):
   def doModal(self):calls.append('notice');self.view=False;self.update=False;self.never=False
  self.nativeNotice=self.ui.UpdateNotice
  self.ui.UpdateNotice=Notice
 def test_later_repeats_on_next_kodi_launch_but_not_home_reentry(self):
  from release_updates import pending,read_state
  self.runtime.tick();self.assertEqual(self.calls,['notice']);self.assertTrue(pending(read_state(self.path)))
  self.runtime.tick();other=self.ui.HomeUpdates(self.owner,lambda *a:{});other.state=self.state;other.due=float('inf');other.tick();self.assertEqual(self.calls,['notice'])
  self.session.props.clear();other.tick();self.assertEqual(self.calls,['notice','notice'])
 def test_old_later_ack_does_not_hide_new_startup_reminder(self):
  from release_updates import write_state
  self.state['seen']=['available:release2'];write_state(self.path,self.state);self.runtime.state=self.state
  self.runtime.tick();self.assertEqual(self.calls,['notice']);self.assertTrue(self.ui.notice_pending(self.ui.releases.read_state(self.path)))
 def test_do_not_show_again_applies_only_to_this_release(self):
  from release_updates import pending,read_state
  import copy
  class Never(self.ui.UpdateNotice):
   def doModal(n):self.calls.append('notice');n.view=False;n.update=False;n.never=True
  self.ui.UpdateNotice=Never;self.runtime.tick();state=read_state(self.path);self.assertIsNone(pending(state));self.assertTrue(state['enabled'])
  newer=copy.deepcopy(state['available']);newer['id']='release3';newer['version']='1.1.21';state['available']=newer;self.assertEqual(pending(state)['release']['id'],'release3')
 def test_explicit_optout_survives_full_legacy_seen_history(self):
  from release_updates import read_state,write_state
  self.state['seen']=['available:release2']+['completed:old'+str(i) for i in range(79)];write_state(self.path,self.state)
  event={'kind':'available','release':self.state['available']};self.ui.mark_seen(event)
  self.assertIsNone(self.ui.notice_pending(read_state(self.path)))
 def test_real_dont_show_button_suppresses_available_release_only(self):
  from unittest.mock import patch,MagicMock
  for kind in ('available','completed'):
   dialog=self.nativeNotice();dialog.event={'kind':kind,'release':self.state['available']}
   with patch.object(self.ui.threading,'Thread',return_value=MagicMock()):dialog.onInit()
   dialog.onClick(104);self.assertEqual(dialog.never,kind=='available');self.assertTrue(dialog.closed)
 def test_completed_confirmation_remains_one_time(self):
  from release_updates import pending,read_state,write_state
  self.state['completed']=self.state['available'];self.state['available']=None;write_state(self.path,self.state);self.runtime.state=self.state
  self.runtime.tick();self.session.props.clear();self.assertIsNone(pending(read_state(self.path)))
 def test_corrupt_read_cannot_kill_home_monitor(self):
  self.path.write_text('{bad');self.runtime.tick();self.assertEqual(self.calls,['error']);self.assertTrue(self.owner.alive)
 def test_failed_ack_does_not_escape_or_redisplay_in_tight_loop(self):
  from unittest.mock import patch
  with patch.object(self.ui,'mark_seen',side_effect=OSError('disk full')):
   class Never(self.ui.UpdateNotice):
    def doModal(n):self.calls.append('notice');n.view=False;n.update=False;n.never=True
   self.ui.UpdateNotice=Never;self.runtime.tick();self.runtime.tick()
  self.assertEqual(self.calls,['notice','error']);self.assertFalse(self.owner.actions_open)
 def test_playback_and_old_lifetime_do_not_open_notice(self):
  self.playing=True;self.runtime.tick();self.assertEqual(self.calls,[])
  self.playing=False;self.owner.window_lifetime=object();self.runtime.tick();self.assertEqual(self.calls,[])
 def test_manual_toggle_uses_durable_store_and_history_stays(self):
  from release_updates import pending,read_state
  self.ui.save_preference(False);state=read_state(self.path);self.assertFalse(pending(state));self.assertEqual(state['available']['id'],'release2')
  self.ui.save_preference(True);self.assertTrue(pending(read_state(self.path)))
 def test_timeout_closes_before_any_new_playback_is_interrupted(self):
  import time
  notice=self.ui.UpdateNotice # use actual class from fresh source below
  import ast,types
  source=Path(__file__).resolve().parents[1]/'addon/update_notes_ui.py'
  node=next(n for n in ast.parse(source.read_text()).body if isinstance(n,ast.ClassDef) and n.name=='UpdateNotice')
  method=next(n for n in node.body if isinstance(n,ast.FunctionDef) and n.name=='timeout')
  ns={'xbmc':self.ui.xbmc,'time':time};exec(compile(ast.Module(body=[method],type_ignores=[]),str(source),'exec'),ns)
  obj=types.SimpleNamespace(finished=False,opened=time.monotonic()-20,close=lambda:self.calls.append('closed'))
  ns['timeout'](obj);self.assertTrue(obj.finished);self.assertEqual(self.calls,['closed'])
 def test_update_uses_only_fixed_installer_catalog_and_not_during_playback(self):
  self.ui.xbmc.executebuiltin=lambda cmd:self.calls.append(cmd)
  self.assertTrue(self.ui.request_update());self.assertEqual(self.calls,['RunPlugin(plugin://plugin.program.blacklanturninstaller/?mode=updates)'])
  self.playing=True;self.assertFalse(self.ui.request_update());self.assertEqual(len(self.calls),1)
 def test_catalog_is_cached_and_no_inventory_rpc_is_used(self):
  from unittest.mock import patch
  import json
  root=Path(self.temp.name);home=root/'home';(home/'userdata').mkdir(parents=True)
  (home/'userdata/blacklanturn-build.json').write_text(json.dumps({'edition':'apple','build_version':'1.1.19'}))
  self.ui.profile_path=lambda:root;self.ui.home_path=lambda:home
  catalog={'schema':1,'releases':[self.state['available']]}
  with patch.object(self.ui.releases,'fetch_catalog',return_value=catalog) as fetch:
   self.ui.sample(lambda *a:self.fail('No add-on inventory RPC allowed'));self.ui.sample()
   self.assertEqual(fetch.call_count,1)
 def test_offline_catalog_backs_off_and_retains_cached_release(self):
  from unittest.mock import patch
  import json
  root=Path(self.temp.name);home=root/'home';(home/'userdata').mkdir(parents=True)
  (home/'userdata/blacklanturn-build.json').write_text(json.dumps({'edition':'apple','build_version':'1.1.19'}))
  self.ui.profile_path=lambda:root;self.ui.home_path=lambda:home
  catalog={'schema':1,'releases':[self.state['available']]}
  (root/'release-catalog-cache.json').write_text(json.dumps({'source':self.ui.catalog_source(),'fetched':0,'catalog':catalog}))
  with patch.object(self.ui.releases,'fetch_catalog',side_effect=OSError('offline')) as fetch:
   state=self.ui.sample();self.ui.sample();self.assertEqual(fetch.call_count,1)
  self.assertEqual(state['available']['id'],'release2')

 def test_new_bundled_release_completes_with_recent_empty_network_cache(self):
  import json,time,copy
  from unittest.mock import patch
  root=Path(self.temp.name);home=root/'testhome';profile=root/'profile';(home/'userdata').mkdir(parents=True);profile.mkdir()
  entry=copy.deepcopy(self.state['available']);file=home/'addons/example/main.py';file.parent.mkdir(parents=True);file.write_text('release')
  (home/'userdata/blacklanturn-build.json').write_text(json.dumps({'edition':'apple','build_version':'1.1.20'}))
  (home/'userdata/blacklanturn-releases.json').write_text(json.dumps({'schema':1,'releases':[entry]}))
  (home/'userdata/blacklanturn-install-complete.json').write_text(json.dumps(dict(schema=1,id='release2',edition='apple',version='1.1.20',revision=0,complete=True)))
  self.ui.home_path=lambda:home;self.ui.profile_path=lambda:profile;source=self.ui.catalog_source()
  (profile/'release-catalog-cache.json').write_text(json.dumps({'source':source,'fetched':time.time(),'catalog':{'schema':1,'releases':[]}}))
  with patch.object(self.ui.releases,'fetch_catalog',side_effect=AssertionError('Recent cache must not fetch')):
   state=self.ui.sample()
  self.assertIsNotNone(state['completed'],'Old cache hid the newly installed bundled release');self.assertEqual(state['completed']['id'],'release2')
