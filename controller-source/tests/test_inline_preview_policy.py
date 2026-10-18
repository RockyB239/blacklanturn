"""Preview timing and quality must remain separate from fullscreen preferences."""
import importlib.util,unittest
from types import SimpleNamespace
from urllib.parse import parse_qs,urlsplit
from youtube_provider import _PreviewSettings
from youtube_core import preview_path

class InlinePreviewPolicy(unittest.TestCase):
 def test_preview_does_not_delegate_timed_stop_to_native_youtube_service(self):
  query=parse_qs(urlsplit(preview_path({'file':'plugin://plugin.video.youtube/play/?video_id=Abc_123-Xyz'})).query)
  self.assertEqual(query.get('end',['0']),['0']);self.assertEqual(query['incognito'],['true'])
 def test_preview_quality_caps_fullscreen_4k_without_writing_the_saved_setting(self):
  base=SimpleNamespace(mpd_video_qualities=lambda:[{'nom_height':2160},{'nom_height':1080},{'nom_height':720},{'nom_height':480}],fixed_video_quality=lambda:1080,max_video_height=lambda:2160)
  preview=_PreviewSettings(base)
  self.assertEqual([x['nom_height'] for x in preview.mpd_video_qualities()],[720,480]);self.assertEqual(preview.max_video_height(),720);self.assertEqual(preview.fixed_video_quality(),720)
  self.assertEqual(base.max_video_height(),2160)
 def clock(self):
  spec=importlib.util.find_spec('inline_preview');self.assertIsNotNone(spec,'Controller-owned inline timing missing')
  return __import__('inline_preview').InlinePreviewClock()
 def test_preview_plays_longer_then_fades_before_requesting_stop(self):
  clock=self.clock();self.assertEqual(clock.tick(100,0,True),'playing');self.assertEqual(clock.tick(130,30,True),'playing')
  self.assertEqual(clock.tick(144,44,True),'fading');self.assertEqual(clock.tick(144.5,44.5,True),'fading');self.assertEqual(clock.tick(145,45,True),'stop')
 def test_stalled_preview_fades_instead_of_freezing_for_ten_seconds(self):
  clock=self.clock();clock.tick(0,0,True);clock.tick(1,1,True)
  self.assertEqual(clock.tick(3.9,1,True),'playing');self.assertEqual(clock.tick(4,1,True),'fading');self.assertEqual(clock.tick(5,1,True),'stop')

class InlinePresentation(unittest.TestCase):
 def test_owned_stop_reveals_artwork_before_waiting_for_decoder_shutdown(self):
  import threading
  from test_window_lifecycle import extract,ROOT
  props={'preview':'playing'};observed=[]
  w=SimpleNamespace(preview_dispatch_lock=threading.RLock(),preview_generation=1,preview_attempts=None,owned_preview=True,preview_dispatched=True,preview_key='same',
   player=SimpleNamespace(isPlaying=lambda:True),cancel_preview_bar_scan=lambda:None,restore_preview_viewmode=lambda:None,restore_preview_renderer=lambda:None,setProperty=props.__setitem__)
  method=extract(ROOT/'live_review.py','stop_preview',{'xbmc':SimpleNamespace(executebuiltin=lambda *a:None),'rpc':lambda *a:observed.append(props['preview']) or {}},'LiveReview')
  method(w);self.assertEqual(observed,['idle'])
 def test_finished_preview_retains_hover_key_so_auto_preview_does_not_restart(self):
  import ast,threading
  from test_window_lifecycle import extract,ROOT
  tree=ast.parse((ROOT/'live_review.py').read_text());method=next((n for c in tree.body if isinstance(c,ast.ClassDef) and c.name=='LiveReview' for n in c.body if isinstance(n,ast.FunctionDef) and n.name=='finish_inline_preview'),None)
  self.assertIsNotNone(method,'Natural preview completion handler missing')
  props={};w=SimpleNamespace(preview_dispatch_lock=threading.RLock(),preview_key='selected-video',selected={'file':'selected-video'},setProperty=props.__setitem__)
  w.stop_preview=lambda:setattr(w,'preview_key',None)
  extract(ROOT/'live_review.py','finish_inline_preview',{},'LiveReview')(w)
  self.assertEqual(w.preview_key,'selected-video')
 def test_stale_clock_cannot_stop_a_new_preview_installed_during_native_time_read(self):
  import threading
  from test_window_lifecycle import extract,ROOT
  old=SimpleNamespace(tick=lambda *a:'stop');new=object();stopped=[];props={}
  w=SimpleNamespace(preview_dispatch_lock=threading.RLock(),alive=True,window_lifetime=object(),preview_generation=1,preview_attempts=object(),input_generation=3,inline_preview_clock=old,owned_preview=True,preview_playing=True,setProperty=props.__setitem__,finish_inline_preview=lambda:stopped.append('new owner stopped'))
  def position():w.preview_generation=2;w.inline_preview_clock=new;return 45
  w.player=SimpleNamespace(getTime=position)
  method=extract(ROOT/'live_review.py','advance_inline_preview',{'time':SimpleNamespace(monotonic=lambda:45)},'LiveReview')
  method(w,True);self.assertEqual(stopped,[]);self.assertEqual(props,{})

class BufferedPreview(unittest.TestCase):
 def test_initial_buffering_does_not_use_the_short_midstream_stall_deadline(self):
  clock=__import__('inline_preview').InlinePreviewClock();clock.tick(0,0,True)
  self.assertEqual(clock.tick(5,0,True),'playing');self.assertEqual(clock.tick(11,0,True),'playing')
 def test_native_startup_timestamp_jump_does_not_end_preview_early(self):
  clock=__import__('inline_preview').InlinePreviewClock();clock.tick(100,0,True)
  self.assertEqual(clock.tick(101,294397.907,True),'playing')
  self.assertEqual(clock.tick(101.2,-.133,True),'playing')
  self.assertEqual(clock.tick(102,.5,True),'playing')
  self.assertEqual(clock.tick(130,28.5,True),'playing')
  self.assertEqual(clock.tick(144,43,True),'playing')
  self.assertEqual(clock.tick(145,44,True),'fading')
 def test_invalid_initial_position_does_not_poison_progress_tracking(self):
  for position in (float('nan'),float('inf'),-1,294397.907):
   with self.subTest(position=position):
    clock=__import__('inline_preview').InlinePreviewClock()
    self.assertEqual(clock.tick(100,position,True),'playing')
    self.assertEqual(clock.tick(101,0,True),'playing')
    self.assertEqual(clock.tick(102,1,True),'playing')
    self.assertEqual(clock.tick(104.9,1,True),'playing')
    self.assertEqual(clock.tick(105,1,True),'fading')

class PreviewCodecPolicy(unittest.TestCase):
 def test_fullscreen_vp9_preference_does_not_change_the_preview_avc_preference(self):
  full=['avc1','vp9','mp4a','vtt','filter','alt_sort']
  base=SimpleNamespace(stream_features=lambda value=None,raw_values=False:list(full) if raw_values else frozenset(full))
  preview=_PreviewSettings(base)
  self.assertEqual(preview.stream_features(),frozenset(['avc1','mp4a','vtt','filter','alt_sort']))
  self.assertIn('vp9',base.stream_features())
