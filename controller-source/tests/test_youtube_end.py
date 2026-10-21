"""Observable end-screen choices, ownership and autoplay cancellation contracts."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
import youtube_core

def item(key,title='Video'):
 return {'file':'plugin://plugin.video.youtube/play/?video_id='+key,'filetype':'file','title':title}

class EndScreen(unittest.TestCase):
 def state(self,autoplay=False):
  cls=getattr(youtube_core,'YouTubeEndState',None)
  self.assertTrue(callable(cls),'Missing YouTube end-screen state')
  return cls([item('bbbbbbbbbbb'),item('ccccccccccc')],autoplay,100)
 def test_first_back_dismisses_second_back_exits(self):
  s=self.state();self.assertEqual(s.back(),'dismiss');self.assertFalse(s.visible)
  self.assertEqual(s.back(),'exit')
 def test_dismiss_cancels_autoplay_even_after_deadline(self):
  s=self.state(True);self.assertEqual(s.back(),'dismiss');self.assertIsNone(s.tick(200))
 def test_autoplay_is_opt_in_and_waits_full_countdown(self):
  self.assertIsNone(self.state().tick(200));s=self.state(True)
  self.assertIsNone(s.tick(114.9));self.assertEqual(s.tick(115)['file'],'plugin://plugin.video.youtube/play/?video_id=bbbbbbbbbbb')
  self.assertIsNone(s.tick(116))
 def test_any_user_interaction_cancels_countdown_but_keeps_cards(self):
  s=self.state(True);s.interact();self.assertTrue(s.visible);self.assertIsNone(s.tick(200))
 def test_enabling_autoplay_while_dismissed_cannot_hide_playback(self):
  s=self.state();s.back();s.set_autoplay(True,110);self.assertIsNone(s.tick(200))
 def test_disabling_autoplay_cancels_pending_play(self):
  s=self.state(True);s.set_autoplay(False,110);self.assertIsNone(s.tick(200))
 def test_empty_candidates_never_start_autoplay(self):
  cls=getattr(youtube_core,'YouTubeEndState',None);self.assertTrue(callable(cls),'Missing YouTube end-screen state')
  s=cls([],True,100);self.assertIsNone(s.tick(200))
 def test_selecting_a_card_plays_that_card_only_once(self):
  s=self.state(True);self.assertEqual(s.choose(1)['file'],'plugin://plugin.video.youtube/play/?video_id=ccccccccccc')
  self.assertIsNone(s.tick(200));self.assertIsNone(s.choose(0))
 def test_suggestions_keep_provider_order_without_duplicates_or_current(self):
  f=getattr(youtube_core,'end_suggestions',None);self.assertTrue(callable(f),'Missing safe end-screen choices')
  inputs=[item('aaaaaaaaaaa'),item('bbbbbbbbbbb'),item('bbbbbbbbbbb'),{'file':'plugin://evil/play'},dict(item('ccccccccccc'),filetype='directory'),item('ddddddddddd'),item('eeeeeeeeeee'),item('fffffffffff')]
  self.assertEqual([youtube_core.video_id(x) for x in f(inputs,'aaaaaaaaaaa')],['bbbbbbbbbbb','ddddddddddd','eeeeeeeeeee'])
 def test_suggestions_require_explicit_natural_end_and_enabled_setting(self):
  f=getattr(youtube_core,'show_end_screen',None);self.assertTrue(callable(f),'Missing natural end guard')
  self.assertTrue(f('ended',{},True,True))
  for reason,config,owner,ready in [('stopped',{},True,True),('error',{},True,True),('ended',{'YouTubeEndSuggestions':False},True,True),('ended',{},False,True),('ended',{},True,False)]:
   with self.subTest(reason=reason,config=config,owner=owner,ready=ready):self.assertFalse(f(reason,config,owner,ready))
if __name__=='__main__':unittest.main()

class EndPreferences(unittest.TestCase):
 def test_switch_changes_only_selected_preference_and_preserves_other_values(self):
  import tempfile,json
  f=getattr(youtube_core,'save_end_preference',None);self.assertTrue(callable(f),'Missing isolated preference update')
  with tempfile.TemporaryDirectory() as temp:
   p=Path(temp)/'rows.json';p.write_text(json.dumps({'Saved':[{'file':'kept'}],'PreviewDelay':8,'PrivateExample':'preserve'}))
   result=f(p,'YouTubeEndAutoplay',True)
   self.assertEqual(result,{'Saved':[{'file':'kept'}],'PreviewDelay':8,'PrivateExample':'preserve','YouTubeEndAutoplay':True})
   self.assertEqual(json.loads(p.read_text()),result)
 def test_bad_preferences_never_replace_existing_config(self):
  import tempfile
  f=getattr(youtube_core,'save_end_preference',None);self.assertTrue(callable(f),'Missing isolated preference update')
  with tempfile.TemporaryDirectory() as temp:
   p=Path(temp)/'rows.json';p.write_text('{broken')
   with self.assertRaises(ValueError):f(p,'YouTubeEndAutoplay',True)
   self.assertEqual(p.read_text(),'{broken')

class CardGeometry(unittest.TestCase):
 def test_thumbnail_frame_tracks_physical_16_by_9_in_tv_and_mac_windows(self):
  f=getattr(youtube_core,'end_card_height',None);self.assertTrue(callable(f),'Missing end-card aspect correction')
  self.assertEqual(f(1920,1080),299);self.assertEqual(f(2084,1428),246)
