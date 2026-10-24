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
     x,y,w,h=map(int,values);self.assertLessEqual(x+w,1870,name);self.assertLessEqual(y+h,1030,name)

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
  modules={'xbmc':fake,'xbmcgui':types.SimpleNamespace(WindowXMLDialog=Window,getCurrentWindowDialogId=lambda:0),'xbmcaddon':types.SimpleNamespace(),'xbmcvfs':types.SimpleNamespace()}
  with patch.dict(sys.modules,modules):
   spec=importlib.util.spec_from_file_location('update_ui_test',Path(__file__).resolve().parents[1]/'addon/update_notes_ui.py');self.ui=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.ui)
  self.path=Path(self.temp.name)/'state.json';self.ui.state_path=lambda:self.path
  from update_notes import observe,write_state
  old=[{'addonid':'plugin.video.example','name':'Example','version':'1'}];new=[dict(old[0],version='2')]
  self.state=observe(observe({},old,1),new,2);write_state(self.path,self.state)
  self.owner=types.SimpleNamespace(alive=True,window_lifetime=object(),mode='home',nav=False,settings_open=False,actions_open=False,getProperty=lambda k:'false')
  self.runtime=self.ui.HomeUpdates(self.owner,lambda *a:{})
  self.runtime.state=self.state;self.runtime.due=float('inf')
  calls=self.calls
  class Notice(Window):
   def doModal(self):calls.append('notice');self.view=False
  self.ui.UpdateNotice=Notice
 def test_real_ack_path_persists_and_does_not_redisplay(self):
  from update_notes import pending,read_state
  self.runtime.tick();self.assertEqual(self.calls,['notice']);self.assertFalse(pending(read_state(self.path)))
  self.runtime.tick();self.assertEqual(self.calls,['notice']);self.assertFalse(self.owner.actions_open)
 def test_corrupt_read_cannot_kill_home_monitor(self):
  self.path.write_text('{bad');self.runtime.tick();self.assertEqual(self.calls,['error']);self.assertTrue(self.owner.alive)
 def test_failed_ack_does_not_escape_or_redisplay_in_tight_loop(self):
  from unittest.mock import patch
  with patch.object(self.ui,'mark_seen',side_effect=OSError('disk full')):
   self.runtime.tick();self.runtime.tick()
  self.assertEqual(self.calls,['notice','error']);self.assertFalse(self.owner.actions_open)
 def test_playback_and_old_lifetime_do_not_open_notice(self):
  self.playing=True;self.runtime.tick();self.assertEqual(self.calls,[])
  self.playing=False;self.owner.window_lifetime=object();self.runtime.tick();self.assertEqual(self.calls,[])
 def test_manual_toggle_uses_durable_store_and_history_stays(self):
  from update_notes import pending,read_state
  self.ui.save_preference(False);state=read_state(self.path);self.assertFalse(pending(state));self.assertEqual(len(state['history']),1)
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
