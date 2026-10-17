import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
import live_core

class WatchState(unittest.TestCase):
 def state(self,item):
  self.assertTrue(hasattr(live_core,'watch_state'),'Provider watch/resume metadata needs to reach custom cards')
  return live_core.watch_state(item)
 def test_missing_data_is_unknown_instead_of_claimed_unwatched(self):
  self.assertEqual(self.state({'title':'A title'}),{'state':'unknown','label':'','percent':0})
 def test_provider_watched_and_unwatched_flags_are_distinct(self):
  self.assertEqual(self.state({'playcount':2})['state'],'watched')
  self.assertEqual(self.state({'playcount':0})['state'],'unwatched')
 def test_partial_resume_wins_even_for_a_previously_watched_title(self):
  self.assertEqual(self.state({'playcount':1,'resume':{'position':1200,'total':4800}}),{'state':'progress','label':'In progress · 25%','percent':25})
 def test_invalid_resume_is_not_a_progress_bar(self):
  self.assertEqual(self.state({'resume':{'position':float('nan'),'total':0}})['state'],'unknown')
 def test_partial_show_cannot_be_labelled_unwatched_from_completion_flag(self):
  self.assertEqual(self.state({'playcount':0,'filetype':'directory','file':'plugin://plugin.video.themoviedb.helper/?tmdb_type=tv'})['state'],'unknown')
