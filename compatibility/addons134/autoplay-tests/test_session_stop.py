"""Use the real Player callback with a live item's tracking state."""
import unittest
import test_player_lifecycle as lifecycle

class SessionStop(unittest.TestCase):
 def stop(self,transition):
  fixture=lifecycle.PlaylistLifecycle()
  self.addCleanup(fixture.doCleanups)
  player,_,_,errors=fixture.player()
  window=player.onPlayBackStopped.__globals__['playerWindow']
  window.setProperty('BlackLanturn.SourceSession.v1','chosen')
  window.setProperty('umbrella.playnext.transition','true' if transition else 'false')
  player.timing_lost=True
  player.onPlayBackStopped()
  self.assertTrue(player.onPlayBackStopped_ran)
  self.assertTrue(player.scrobble_sent)
  self.assertEqual(errors,[])
  return window.getProperty('BlackLanturn.SourceSession.v1')
 def test_explicit_stop_retires_the_viewing_session(self):self.assertEqual(self.stop(False),'')
 def test_real_next_episode_transition_retains_the_viewing_session(self):self.assertEqual(self.stop(True),'chosen')
