"""Navigation invalidates automatic preview intent before yielding to Kodi."""
import threading,time,unittest
from types import SimpleNamespace,MethodType
from test_window_lifecycle import extract,ROOT

class PreviewInputEpoch(unittest.TestCase):
 def state(self):
  calls=[]
  w=SimpleNamespace(actions_open=False,mode='home',nav=False,last_row=0,histories=[SimpleNamespace(pop=lambda:None)],episode_browser_context=None,person_context=None,discovery_stack=[],search_state=None,active_page=None,return_focus=900,
   setProperty=lambda *a:calls.append(('property',a)),setFocusId=lambda cid:calls.append(('focus',cid)),input_generation=0,dwell=time.monotonic()-30,
   selected={'file':'old'},preview_generation=0,preview_dispatch_lock=threading.RLock(),owned_preview=False,previews_ready=True,alive=True,config={'PreviewDelay':5},player=SimpleNamespace(isPlaying=lambda:False))
  def set_nav(value,**kw):w.nav=value
  def stop():w.preview_generation+=1
  w.set_nav=set_nav;w.stop_preview=stop
  ns={'time':time,'event':lambda *a,**k:None,'threading':SimpleNamespace(Thread=lambda **k:SimpleNamespace(start=lambda:calls.append('worker')))}
  for name in ['onAction','preview']:setattr(w,name,MethodType(extract(ROOT/'live_review.py',name,ns,'LiveReview'),w))
  return w,calls
 def test_back_invalidates_auto_intent_before_stop_yields(self):
  w,calls=self.state();seen=[]
  def stop():
   w.preview_generation+=1;seen.append(w.input_generation)
   w.preview(automatic=True)
  w.stop_preview=stop
  w.onAction(SimpleNamespace(getId=lambda:92))
  self.assertEqual(seen,[1]);self.assertTrue(w.nav);self.assertNotIn('worker',calls);self.assertFalse(w.owned_preview)
 def test_fast_back_right_does_not_reuse_the_old_dwell(self):
  w,calls=self.state();before=time.monotonic()
  w.onAction(SimpleNamespace(getId=lambda:92));w.onAction(SimpleNamespace(getId=lambda:2));w.preview(automatic=True)
  self.assertFalse(w.nav);self.assertGreaterEqual(w.dwell,before);self.assertEqual(w.input_generation,2);self.assertNotIn('worker',calls)
 def test_explicit_preview_does_not_wait_for_automatic_dwell(self):
  w,calls=self.state();w.dwell=time.monotonic();w.preview()
  self.assertTrue(w.owned_preview);self.assertIn('worker',calls)
 def test_navigation_during_preparation_rejects_dispatch(self):
  from test_preview_navigation_stop import PreviewNavigationStop
  w,candidate,calls,props=PreviewNavigationStop().candidate(lambda w,stop:setattr(w,'input_generation',2))
  w.input_generation=1;w.preview_input_generation=1
  candidate(w,'plugin://plugin.video.youtube/play/?video_id=test')
  self.assertFalse(any(isinstance(c,tuple) and c[0]=='play' for c in calls))

if __name__=='__main__':unittest.main()
