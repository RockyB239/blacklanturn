import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
import live_core as core
class EpisodeDetails(unittest.TestCase):
 def item(self):return {'file':'plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=tv&tmdb_id=248830&season=1&episode=2','filetype':'file','title':"Grossweiner's Law",'showtitle':'Stick','season':1,'episode':2,'resume':{'position':1310,'total':1800},'playcount':0,'plot':'Episode plot','runtime':1800}
 def test_identity_comes_from_play_route_and_accepts_specials(self):
  self.assertEqual(core.episode_identity(self.item()),{'tmdb_id':'248830','season':1,'episode':2})
  x=self.item();x['file']=x['file'].replace('season=1','season=0');self.assertEqual(core.episode_identity(x)['season'],0)
 def test_details_query_includes_season_and_episode(self):
  self.assertEqual(core.title_details_params(self.item()),{'tmdb_type':'tv','tmdb_id':'248830','season':1,'episode':2})
 def test_show_enrichment_cannot_replace_selected_episode_or_resume(self):
  x=self.item();merged=core.merge_title_details(x,{'title':'Stick','plot':'Show plot','runtime':3000,'season':-1,'episode':-1,'resume':{'position':0,'total':0},'playcount':0,'art':{'fanart':'image'}})
  for k in ('title','plot','runtime','season','episode','resume','playcount','file'):self.assertEqual(merged[k],x[k])
  self.assertEqual(merged['art'],{'fanart':'image'})
 def test_episode_has_clear_show_heading_and_episode_label(self):
  self.assertEqual(core.episode_heading(self.item()),('Stick',"S01 · E02 — Grossweiner's Law"))
 def test_season_folder_browses_even_when_it_has_a_year_and_plot(self):
  x={'file':'plugin://plugin.video.themoviedb.helper/?info=episodes&tmdb_type=tv&tmdb_id=248830&season=1','filetype':'directory','year':2025,'plot':'Season summary'}
  self.assertTrue(core.is_browse_folder(x));self.assertFalse(core.is_browse_folder(self.item()))
 def test_show_id_does_not_accept_a_movie(self):
  self.assertEqual(core.show_identity(self.item()),'248830');x=self.item();x['file']=x['file'].replace('tmdb_type=tv','tmdb_type=movie');self.assertIsNone(core.show_identity(x))
 def test_season_episode_count_is_not_an_episode_number(self):
  x={'file':'plugin://plugin.video.themoviedb.helper/?info=episodes&tmdb_type=tv&tmdb_id=288673&season=1','filetype':'directory','title':'Miniseries','showtitle':'Carrie','season':1,'episode':8}
  self.assertIsNone(core.episode_identity(x));self.assertEqual(core.episode_heading(x),('Carrie','Season 1 · Miniseries'))
