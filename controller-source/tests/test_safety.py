"""Catches production-profile leakage and autoplay cancellation regressions."""
import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
class ProbeSafety(unittest.TestCase):
    def test_rejects_regular_profile_and_sibling_prefix(self):
        from probe_core import isolated_paths
        self.assertFalse(isolated_paths('/tmp/test/portable_data','/Users/chris/Library/Application Support/Kodi','/tmp/test/portable_data/temp'))
        self.assertFalse(isolated_paths('/tmp/test/portable_data','/tmp/test/portable_data-old/userdata','/tmp/test/portable_data/temp'))
        self.assertTrue(isolated_paths('/tmp/test/portable_data','/tmp/test/portable_data/userdata','/tmp/test/portable_data/temp'))
    def test_cancel_keeps_current_episode_and_blocks_transition(self):
        from probe_core import EpisodeTransition
        t=EpisodeTransition()
        self.assertEqual(t.tick(9,1),'show')
        t.cancel()
        self.assertEqual(t.tick(0,1),'continue')
        self.assertEqual(t.episode,1)
    def test_episode_transition_occurs_once_and_never_after_last(self):
        from probe_core import EpisodeTransition
        t=EpisodeTransition()
        self.assertEqual(t.tick(0,1),'next')
        self.assertEqual(t.episode,2)
        self.assertEqual(t.tick(0,1),'continue')
        self.assertEqual(t.tick(0,2),'continue')
if __name__=='__main__': unittest.main()
