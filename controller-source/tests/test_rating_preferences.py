import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
import live_core
class RatingPreferences(unittest.TestCase):
 def test_source_selection_preserves_custom_order(self):
  self.assertEqual(live_core.update_rating_sources(['imdb','rottentomatoes','metacritic'],['rottentomatoes','imdb','popcorn']),['imdb','rottentomatoes','popcorn'])
 def test_source_selection_can_disable_all(self):
  self.assertEqual(live_core.update_rating_sources(['imdb'],[]),[])
 def test_disabled_ratings_stay_hidden(self):
  self.assertEqual(live_core.select_rating_badges({'rating':8},[{'icon':'imdb','value':'8/10'}],[]),[])
 def test_requested_order_and_missing_scores(self):
  badges=[{'icon':'imdb','value':'8/10'},{'icon':'metacritic','value':'72/100'}]
  self.assertEqual(live_core.select_rating_badges({},badges,['metacritic','rottentomatoes','imdb']),[badges[1],badges[0]])
 def test_tmdb_only_when_selected_and_present(self):
  item={'rating':7.8,'_rating_source':'TMDb'}
  self.assertEqual(live_core.select_rating_badges(item,[],['imdb']),[])
  self.assertEqual(live_core.select_rating_badges(item,[],['themoviedatabase']),[{'icon':'themoviedatabase','value':'7.8/10','kind':'audience'}])
  self.assertEqual(live_core.select_rating_badges({},[],['themoviedatabase']),[])
