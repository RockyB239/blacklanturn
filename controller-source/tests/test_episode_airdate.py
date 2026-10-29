import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
from live_core import title_presentation,merge_title_details

def episode(**kw):
 return dict({'type':'episode','filetype':'file','season':1,'episode':2,'premiered':'2026-10-21','file':'plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=tv&tmdb_id=1&season=1&episode=2','runtime':2400},**kw)
class AirDateTests(unittest.TestCase):
 def test_episode_date_visible_with_runtime(self):
  text=title_presentation(episode())['technical'];self.assertIn('Aired Oct 21, 2026',text);self.assertIn('40 min',text)
 def test_invalid_or_unknown_dates_do_not_appear(self):
  for date in ('','0','0000-00-00','2026-02-30',None):self.assertNotIn('Aired',title_presentation(episode(premiered=date))['technical'])
 def test_movies_seasons_and_shows_do_not_get_episode_dates(self):
  for kind in ('movie','tvshow','season'):
   item=episode(type=kind,file='plugin://plugin.video.themoviedb.helper/?info=details&tmdb_type=movie&tmdb_id=1',filetype='directory',season=-1,episode=-1)
   self.assertNotIn('Aired',title_presentation(item)['technical'])
 def test_episode_details_keep_episode_date_instead_of_series_premiere(self):
  self.assertEqual(merge_title_details(episode(),{'premiered':'2001-01-01'})['premiered'],'2026-10-21')
