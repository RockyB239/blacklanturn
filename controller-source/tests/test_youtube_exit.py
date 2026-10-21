"""Back may stop only the exact fullscreen YouTube playback this handoff owns."""
import importlib.util,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
import playback_core

class YouTubeExitContracts(unittest.TestCase):
 def guard(self,enabled=True):
  cls=getattr(playback_core,'YouTubeExitGuard',None)
  self.assertTrue(callable(cls),'Missing owned YouTube fullscreen exit guard')
  return cls(enabled)
 def test_initial_player_loading_does_not_treat_home_as_back(self):
  g=self.guard();g.observe(True,False,'https://stream-a',True)
  self.assertFalse(g.armed);self.assertFalse(g.consume_back(True,True,'https://stream-a',True))
 def test_back_after_fullscreen_stops_the_exact_owned_source_once(self):
  g=self.guard();g.observe(True,True,'https://stream-a',True)
  self.assertTrue(g.armed);self.assertTrue(g.consume_back(True,True,'https://stream-a',True))
  self.assertFalse(g.consume_back(True,True,'https://stream-a',True))
 def test_ordinary_playback_and_osd_dismissal_do_not_stop_video(self):
  g=self.guard();g.observe(True,True,'https://stream-a',True)
  self.assertFalse(g.consume_back(False,True,'https://stream-a',True));self.assertTrue(g.armed)
 def test_movie_handoff_and_other_skin_cannot_be_stopped(self):
  for enabled,owner,path in [(False,True,'https://stream-a'),(True,False,'https://stream-a'),(True,True,'https://different-source')]:
   with self.subTest(enabled=enabled,owner=owner,path=path):
    g=self.guard(enabled);g.observe(True,True,'https://stream-a',True)
    self.assertFalse(g.consume_back(True,True,path,owner))
 def test_natural_end_never_calls_stop_and_does_not_arm_a_replacement(self):
  g=self.guard();g.observe(True,True,'https://stream-a',True);g.observe(False,False,'',True)
  self.assertFalse(g.consume_back(True,False,'',True));self.assertFalse(g.armed)
  g.observe(True,True,'https://another-source',True);self.assertFalse(g.armed)
 def test_changed_source_disarms_the_original_session(self):
  g=self.guard();g.observe(True,True,'https://stream-a',True);g.observe(True,True,'https://another-source',True)
  self.assertFalse(g.armed);self.assertFalse(g.consume_back(True,True,'https://another-source',True))
if __name__=='__main__':unittest.main()
