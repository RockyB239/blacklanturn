"""Sidebar geometry has one writer; callbacks only queue explicit focus intent."""
import threading,unittest
from types import SimpleNamespace,MethodType
from test_window_lifecycle import extract,ROOT

class SidebarPreviewStop(unittest.TestCase):
 def state(self,width_handler=None):
  calls=[];props={'nav':'closed'};focus=[]
  w=SimpleNamespace(nav=False,preview_dispatch_lock=threading.RLock(),nav_state_lock=threading.RLock(),nav_revision=0,nav_focus_intent=None,nav_width_requested=82,nav_width_applied=82,
   stop_preview=lambda:calls.append('stop'),setProperty=props.__setitem__,setFocusId=focus.append,
   getControl=lambda cid:SimpleNamespace(setWidth=lambda width:(width_handler(cid,width) if width_handler else None,calls.append((cid,width)))))
  for name in ['set_nav','apply_nav_width','sync_nav_focus']:
   setattr(w,name,MethodType(extract(ROOT/'live_review.py',name,{},'LiveReview'),w))
  return w,calls,props,focus
 def test_callback_queues_navigation_without_resizing_controls(self):
  calls=[];w=SimpleNamespace(nav=False,nav_state_lock=threading.RLock(),nav_revision=0,stop_preview=lambda:calls.append('stop'),setProperty=lambda *a:None,
   getControl=lambda cid:self.fail('Callbacks must not resize native sidebar controls'))
  extract(ROOT/'live_review.py','set_nav',{},'LiveReview')(w,True)
  self.assertEqual(calls,['stop']);self.assertEqual(w.nav_width_requested,350)
 def test_delayed_open_focus_does_not_reverse_the_explicit_remote_request(self):
  w,calls,props,focus=self.state();w.set_nav(True,pending_focus=True);w.sync_nav_focus(900)
  self.assertTrue(w.nav);self.assertEqual(props['nav'],'open');self.assertEqual(w.nav_width_applied,350)
  w.sync_nav_focus(50);self.assertIsNone(w.nav_focus_intent)
 def test_delayed_close_focus_does_not_reopen_the_sidebar(self):
  w,calls,props,focus=self.state();w.set_nav(True,pending_focus=True);w.sync_nav_focus(50)
  w.set_nav(False,pending_focus=True);w.sync_nav_focus(50)
  self.assertFalse(w.nav);self.assertEqual(props['nav'],'closed');self.assertEqual(w.nav_width_applied,82)
  w.sync_nav_focus(600);self.assertIsNone(w.nav_focus_intent)
 def test_newer_close_supersedes_unacknowledged_open(self):
  w,calls,props,focus=self.state();w.set_nav(True,pending_focus=True);w.set_nav(False,pending_focus=True);w.sync_nav_focus(900)
  self.assertFalse(w.nav);self.assertEqual(w.nav_width_applied,82);self.assertEqual(props['nav'],'closed')
 def test_latest_intent_during_resize_is_applied_on_next_drain(self):
  fired=[]
  def change(cid,width):
   if not fired:fired.append(True);w.set_nav(False,pending_focus=True)
  w,calls,props,focus=self.state(change);w.set_nav(True,pending_focus=True);w.apply_nav_width();w.apply_nav_width()
  self.assertEqual(calls[-3:],[(10,82),(50,82),(15,82)]);self.assertEqual(props['nav'],'closed')
 def test_callback_stays_responsive_while_geometry_writer_waits(self):
  entered=threading.Event();release=threading.Event();finished=threading.Event()
  def slow(cid,width):entered.set();release.wait(2)
  w,calls,props,focus=self.state(slow);w.set_nav(True,pending_focus=True)
  worker=threading.Thread(target=w.apply_nav_width);worker.start();self.assertTrue(entered.wait(1))
  callback=threading.Thread(target=lambda:(w.set_nav(False,pending_focus=True),finished.set()));callback.start()
  try:self.assertTrue(finished.wait(.2),'Remote navigation waited on the native geometry writer')
  finally:release.set();worker.join(2);callback.join(2)
  w.apply_nav_width();self.assertEqual(w.nav_width_applied,82)
 def test_geometry_waits_until_preview_shutdown_has_drained(self):
  w,calls,props,focus=self.state();w.nav_width_requested=350
  started=threading.Event();finished=threading.Event()
  def geometry():started.set();w.apply_nav_width();finished.set()
  with w.preview_dispatch_lock:
   worker=threading.Thread(target=geometry);worker.start();self.assertTrue(started.wait(1))
   self.assertFalse(finished.wait(.1),'Native geometry overlapped preview shutdown')
   self.assertEqual(calls,[])
  worker.join(2);self.assertTrue(finished.is_set());self.assertEqual(w.nav_width_applied,350)

 def test_background_row_navigation_waits_for_preview_shutdown(self):
  from test_discovery_controller import DiscoveryController
  w,_,controls=DiscoveryController().state();w.selected=None;w.startup_idle=False
  mutations=[];entered=threading.Event();done=threading.Event()
  for control in controls.values():
   for method in ('controlUp','controlDown','controlLeft','controlRight'):
    setattr(control,method,lambda other:mutations.append(other))
  def apply():entered.set();w.row_navigation();done.set()
  with w.preview_dispatch_lock:
   thread=threading.Thread(target=apply);thread.start();self.assertTrue(entered.wait(1))
   self.assertFalse(done.wait(.1));self.assertEqual(mutations,[])
  thread.join(2);self.assertTrue(done.is_set());self.assertGreater(len(mutations),0)

 def test_mouse_focus_still_opens_and_closes_sidebar(self):
  w,calls,props,focus=self.state();w.sync_nav_focus(50);self.assertTrue(w.nav);self.assertEqual(w.nav_width_applied,350)
  w.sync_nav_focus(900);self.assertFalse(w.nav);self.assertEqual(w.nav_width_applied,82)

 def test_queued_sidebar_open_drains_while_a_provider_page_is_loading(self):
  w,calls,props,focus=self.state();w.alive=True;w.owner_skin='test';w.settings_open=False;w.actions_open=False;w.loading_paths={0:'pending'}
  w.getProperty=lambda key:'false';w.set_nav(True,pending_focus=True)
  ns={'xbmc':SimpleNamespace(getSkinDir=lambda:'test',Monitor=lambda:SimpleNamespace(abortRequested=lambda:False)),
      'time':SimpleNamespace(sleep=lambda _:setattr(w,'alive',False))}
  extract(ROOT/'live_review.py','monitor',ns,'LiveReview')(w)
  self.assertEqual(w.nav_width_applied,350);self.assertEqual(props['nav'],'open')
 def test_sidebar_destination_retains_explicit_close_until_content_focus_arrives(self):
  from test_navigation_controller import NavigationController
  w,calls=NavigationController().controller();requests=[];w.set_nav=lambda opened,**kw:requests.append((opened,kw))
  w.activate_navigation({'id':'home','destination':{'kind':'section','section':'Home'}})
  self.assertEqual(requests,[(False,{'pending_focus':True})]);self.assertIn(('focus',900),calls)

if __name__=='__main__':unittest.main()
