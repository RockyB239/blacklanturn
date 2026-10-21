import unittest
from types import SimpleNamespace,MethodType
import test_backend_preferences as backend

class EndSettings(unittest.TestCase):
 def test_hub_describes_current_suggestion_and_autoplay_switches(self):
  for config,one,two in [({},'On','Off'),({'YouTubeEndSuggestions':False,'YouTubeEndAutoplay':True},'Off','On')]:
   with self.subTest(config=config):
    _,rows=backend.BackendPreferences().hub(config)
    self.assertEqual(rows.items[4].label2,'Next-video suggestions: '+one)
    self.assertEqual(rows.items[5].label2,'Next-video autoplay: '+two+'  ·  Requires suggestions to be enabled')
 def test_toggling_end_preferences_preserves_other_playback_choices(self):
  original={'Saved':[{'file':'kept'}],'PreviewDelay':8,'YouTubePreviews':False};saved=[]
  w=SimpleNamespace(config=dict(original),save=lambda:saved.append(True))
  action=MethodType(backend.method('live_review.py','LiveReview','run_setting',{'event':lambda *a,**k:None}),w)
  action('youtube_end_suggestions');self.assertFalse(w.config['YouTubeEndSuggestions'])
  action('youtube_end_autoplay');self.assertTrue(w.config['YouTubeEndAutoplay'])
  for key,value in original.items():self.assertEqual(w.config[key],value)
  self.assertEqual(len(saved),2)
 def test_select_event_after_enabling_autoplay_does_not_cancel_the_new_countdown(self):
  import youtube_core
  state=youtube_core.YouTubeEndState([{'file':'plugin://plugin.video.youtube/play/?video_id=bbbbbbbbbbb'}],True,100)
  w=SimpleNamespace(state=state,update_status=lambda:None)
  action=MethodType(backend.method('youtube_end.py','YouTubeEndDialog','onAction',{}),w)
  action(SimpleNamespace(getId=lambda:7))
  self.assertEqual(state.deadline,115)
 def test_pointer_navigation_cancels_autoplay(self):
  import youtube_core
  for action_id in (106,107):
   with self.subTest(action_id=action_id):
    state=youtube_core.YouTubeEndState([{'file':'plugin://plugin.video.youtube/play/?video_id=bbbbbbbbbbb'}],True,100)
    w=SimpleNamespace(state=state,update_status=lambda:None)
    action=MethodType(backend.method('youtube_end.py','YouTubeEndDialog','onAction',{}),w)
    action(SimpleNamespace(getId=lambda:action_id))
    self.assertIsNone(state.tick(116))
    self.assertIsNone(state.deadline)
 def test_initial_focus_preserves_countdown_but_changed_focus_cancels_it(self):
  import youtube_core
  for target in (7001,7013):
   with self.subTest(target=target):
    state=youtube_core.YouTubeEndState([{'file':'plugin://plugin.video.youtube/play/?video_id=bbbbbbbbbbb'}],True,100)
    w=SimpleNamespace(state=state,selection=0,focused_control=7000,update_status=lambda:None)
    focus=MethodType(backend.method('youtube_end.py','YouTubeEndDialog','onFocus',{}),w)
    focus(7000);self.assertEqual(state.deadline,115)
    focus(target);self.assertIsNone(state.deadline)
    self.assertIsNone(state.tick(116))
