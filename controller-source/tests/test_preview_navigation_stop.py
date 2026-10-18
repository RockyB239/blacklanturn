"""Navigating away must never wait on Kodi's synchronous player-stop message."""
import threading,unittest
from types import SimpleNamespace
from test_window_lifecycle import extract,ROOT

class PreviewNavigationStop(unittest.TestCase):
 def state(self,owned=True,playing=True):
  calls=[];release=threading.Event();entered=threading.Event()
  def synchronous_stop():entered.set();release.wait(2);calls.append('synchronous_stop')
  props={}
  w=SimpleNamespace(preview_dispatch_lock=threading.RLock(),preview_dispatched=False,preview_generation=2,preview_attempts=SimpleNamespace(cancel=lambda:calls.append('cancel')),owned_preview=owned,
   player=SimpleNamespace(isPlaying=lambda:playing,stop=synchronous_stop),cancel_preview_bar_scan=lambda:calls.append('scan_closed'),
   restore_preview_viewmode=lambda:calls.append('view_restored'),restore_preview_renderer=lambda:calls.append('renderer_restored'),
   setProperty=props.__setitem__,preview_key='old')
  def builtin(command,wait=False):calls.append((command,wait))
  method=extract(ROOT/'live_review.py','stop_preview',{'xbmc':SimpleNamespace(executebuiltin=builtin),'rpc':lambda *a:calls.append(('barrier',a)) or {'result':{}}},'LiveReview')
  return w,method,calls,release,entered,props
 def test_navigation_returns_while_native_player_stop_is_blocked(self):
  w,stop,calls,release,entered,props=self.state();finished=threading.Event()
  def run():
   try:stop(w)
   finally:finished.set()
  thread=threading.Thread(target=run);thread.start()
  try:self.assertTrue(finished.wait(.25),'Preview cancellation blocked the navigation callback on Player.stop')
  finally:release.set();thread.join(2)
  self.assertFalse(entered.is_set());self.assertIn(('PlayerControl(Stop)',False),calls)
  self.assertLess(calls.index(('PlayerControl(Stop)',False)),next(i for i,c in enumerate(calls) if isinstance(c,tuple) and c[0]=='barrier'))
  self.assertLess(next(i for i,c in enumerate(calls) if isinstance(c,tuple) and c[0]=='barrier'),calls.index('view_restored'))
  self.assertFalse(w.owned_preview);self.assertIsNone(w.preview_attempts);self.assertEqual(props['preview'],'idle')
 def test_navigation_does_not_stop_unowned_playback(self):
  w,stop,calls,release,entered,props=self.state(owned=False);stop(w)
  self.assertFalse(entered.is_set());self.assertNotIn(('PlayerControl(Stop)',False),calls)
 def test_repeated_cancel_does_not_stop_a_later_unowned_video(self):
  w,stop,calls,release,entered,props=self.state();release.set();stop(w);stop(w)
  self.assertEqual(calls.count(('PlayerControl(Stop)',False)),1)

 def test_cancel_dispatched_request_even_before_kodi_reports_playing(self):
  w,stop,calls,release,entered,props=self.state(playing=False);w.preview_dispatched=True;stop(w)
  self.assertIn(('PlayerControl(Stop)',False),calls);self.assertFalse(w.preview_dispatched)
 def candidate(self,when_acquire=None):
  w,stop,calls,release,entered,props=self.state(playing=False);w.alive=True;w.preview_attempts=SimpleNamespace(index=0,cancel=lambda:calls.append('cancel'))
  w.player.failed=False;w.player.play=lambda url,listitem=None,windowed=False:calls.append(('play',url))
  def acquire():
   if when_acquire:when_acquire(w,stop)
   return True
  w.preview_renderer=SimpleNamespace(acquire=acquire)
  from urllib.parse import parse_qs,urlsplit
  import time
  class InlineThread:
   def __init__(self,target,**kwargs):self.target=target
   def start(self):self.target()
  candidate=extract(ROOT/'live_review.py','play_preview_candidate',{'threading':SimpleNamespace(Thread=InlineThread),'resolve_preview':lambda url,current:SimpleNamespace(path='https://fixture.invalid/preview.mpd',listitem=object(),publish=lambda:True),'rpc':lambda *a:{'result':{}},'time':time,'parse_qs':parse_qs,'urlsplit':urlsplit,'event':lambda *a,**k:None,'xbmc':SimpleNamespace(executebuiltin=lambda *a:calls.append(('stop',)))},'LiveReview')
  return w,candidate,calls,props

 def test_slow_resolution_does_not_block_navigation_or_change_decoder_settings(self):
  w,candidate,calls,props=self.candidate();entered=threading.Event();release=threading.Event();finished=threading.Event()
  def resolve(url,current):entered.set();release.wait(2);return None
  # Exercise the real controller method and real worker; only the native stream
  # resolver is blocked at its external dependency boundary.
  from urllib.parse import parse_qs,urlsplit
  method=extract(ROOT/'live_review.py','play_preview_candidate',{'rpc':lambda *a:{'result':{}},'parse_qs':parse_qs,'urlsplit':urlsplit,'event':lambda *a,**k:None,'threading':threading,'resolve_preview':resolve,'xbmc':SimpleNamespace(executebuiltin=lambda *a:None)},'LiveReview')
  w.preview_renderer.acquire=lambda:self.fail('Cancelled resolution must not change decoder settings')
  w.restore_preview_viewmode=lambda:None
  driver=threading.Thread(target=lambda:(method(w,'plugin://plugin.video.youtube/play/?video_id=Abc_123-Xyz'),finished.set()));driver.start()
  try:
   self.assertTrue(entered.wait(1),'Player was given a plug-in URL instead of resolving it first')
   self.assertTrue(finished.wait(.2),'Network resolution blocked navigation')
   w.preview_generation+=1;w.owned_preview=False
  finally:release.set();driver.join(2)
  self.assertFalse(any(isinstance(c,tuple) and c[0]=='play' for c in calls))
 def test_cancel_during_renderer_preparation_does_not_start_an_orphan(self):
  w,candidate,calls,props=self.candidate(lambda w,stop:stop(w))
  candidate(w,'plugin://plugin.video.youtube/play/?video_id=test')
  self.assertFalse(any(isinstance(c,tuple) and c[0]=='play' for c in calls));self.assertFalse(w.owned_preview)
  self.assertEqual(props['preview'],'idle');self.assertEqual(calls.count('renderer_restored'),2)
 def test_renderer_acquisition_is_serialized_with_navigation_cleanup(self):
  w,candidate,calls,props=self.candidate();entered=threading.Event();release=threading.Event();cancelled=threading.Event()
  stop=extract(ROOT/'live_review.py','stop_preview',{'xbmc':SimpleNamespace(executebuiltin=lambda *a:None),'rpc':lambda *a:{'result':{}}},'LiveReview')
  def acquire():entered.set();release.wait(2);return True
  w.preview_renderer.acquire=acquire
  dispatch=threading.Thread(target=lambda:candidate(w,'plugin://plugin.video.youtube/play/?video_id=test'));dispatch.start()
  self.assertTrue(entered.wait(1))
  cancel=threading.Thread(target=lambda:(stop(w),cancelled.set()));cancel.start()
  try:self.assertFalse(cancelled.wait(.1),'Renderer restoration overtook in-progress acquisition')
  finally:release.set();dispatch.join(2);cancel.join(2)
  self.assertTrue(cancelled.is_set());self.assertFalse(w.owned_preview)
  self.assertEqual(props['preview'],'idle');self.assertEqual(calls[-1],'renderer_restored')
 def test_cancelled_fallback_cannot_touch_a_later_preview(self):
  w,candidate,calls,props=self.candidate();old_generation=w.preview_generation;old_attempts=w.preview_attempts
  w.preview_generation+=1;w.preview_attempts=SimpleNamespace(index=0)
  candidate(w,'plugin://plugin.video.youtube/play/?video_id=old',old_generation,old_attempts)
  self.assertEqual(calls,[])
 def test_current_candidate_dispatches_once_and_remains_owned(self):
  w,candidate,calls,props=self.candidate()
  candidate(w,'plugin://plugin.video.youtube/play/?video_id=test')
  self.assertEqual([c for c in calls if isinstance(c,tuple)],[('play','https://fixture.invalid/preview.mpd')]);self.assertTrue(w.owned_preview);self.assertTrue(w.preview_dispatched)

 def test_fallback_stops_old_player_before_replacing_it(self):
  w,candidate,calls,props=self.candidate();w.preview_dispatched=True
  candidate(w,'plugin://plugin.video.youtube/play/?video_id=new')
  relevant=[c[0] for c in calls if isinstance(c,tuple)]
  self.assertEqual(relevant,['stop','play'])

 def test_new_dispatch_waits_for_prior_renderer_cleanup(self):
  w,candidate,calls,props=self.candidate();stop=extract(ROOT/'live_review.py','stop_preview',{'xbmc':SimpleNamespace(executebuiltin=lambda *a:None),'rpc':lambda *a:{'result':{}}},'LiveReview')
  entered=threading.Event();release=threading.Event();finished=threading.Event()
  def restore():entered.set();release.wait(2);calls.append('old_cleanup_complete')
  w.restore_preview_viewmode=restore
  old=threading.Thread(target=lambda:stop(w));old.start();self.assertTrue(entered.wait(1))
  def newer():
   with w.preview_dispatch_lock:
    w.owned_preview=True;w.preview_attempts=SimpleNamespace(index=0,cancel=lambda:None)
   w.restore_preview_viewmode=lambda:None
   candidate(w,'plugin://plugin.video.youtube/play/?video_id=new');finished.set()
  new=threading.Thread(target=newer);new.start()
  try:self.assertFalse(finished.wait(.1),'New preview overtook prior renderer cleanup')
  finally:release.set();old.join(2);new.join(2)
  self.assertTrue(finished.is_set());self.assertEqual(props['preview'],'loading')
  self.assertLess(calls.index('old_cleanup_complete'),calls.index(('play','https://fixture.invalid/preview.mpd')))


 def test_preview_does_not_retake_ownership_after_sidebar_cancellation(self):
  import time
  old={'file':'plugin://plugin.video.youtube/play/?video_id=old'}
  w=SimpleNamespace(previews_ready=True,selected=old,nav=False,alive=True,owned_preview=False,preview_generation=3,
    player=SimpleNamespace(isPlaying=lambda:False),dwell=0,config={},preview_dispatch_lock=threading.RLock(),setProperty=lambda *a:self.fail('Cancelled intent must not update the preview'))
  def cancel():w.preview_generation+=1;w.nav=True;w.selected={'file':'new'}
  w.stop_preview=cancel
  preview=extract(ROOT/'live_review.py','preview',{'time':time,'event':lambda *a,**k:None,'threading':threading},'LiveReview')
  preview(w);self.assertFalse(w.owned_preview)

if __name__=='__main__':unittest.main()
