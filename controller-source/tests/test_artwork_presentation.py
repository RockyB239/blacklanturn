import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
import live_core

class ArtworkPresentation(unittest.TestCase):
 def test_caption_fit_follows_art_in_tall_windows_without_changing_tv_layout(self):
  self.assertEqual(live_core.caption_fit_step(1920,1080),0)
  self.assertEqual(live_core.caption_fit_step(2084,1428),4)
  self.assertEqual(live_core.caption_fit_step(1920,1200),2)
  self.assertEqual(live_core.caption_fit_step(2560,1080),0)
  self.assertEqual(live_core.caption_fit_step('',0),0)
 def art(self,item):
  self.assertTrue(hasattr(live_core,'card_artwork'),'Artwork needs type-aware fallback rules')
  return live_core.card_artwork(item)
 def info(self,item,logos=True):
  self.assertTrue(hasattr(live_core,'title_presentation'),'Watch status must survive long genre metadata')
  return live_core.title_presentation(item,logos)
 def test_episode_uses_episode_thumb_before_generic_show_landscape(self):
  item={'file':'plugin://plugin.video.themoviedb.helper/?tmdb_type=tv&tmdb_id=1&season=1&episode=2','art':{'thumb':'episode.jpg','landscape':'show.jpg'}}
  self.assertEqual(self.art(item),{'image':'episode.jpg','kind':'landscape'})
 def season(self,art,number=1):
  # Real TMDbHelper seasons carry episode count, not episode identity.
  return {'file':f'plugin://plugin.video.themoviedb.helper/?info=episodes&tmdb_type=tv&tmdb_id=1399&season={number}','filetype':'directory','season':number,'episode':10,'art':art}
 def test_season_poster_wins_over_shared_show_landscape_and_episode_count(self):
  self.assertEqual(self.art(self.season({'poster':'season1.jpg','tvshow.poster':'show.jpg','landscape':'show-wide.jpg'})),{'image':'season1.jpg','kind':'portrait'})
 def test_explicit_season_poster_wins_over_generic_poster(self):
  self.assertEqual(self.art(self.season({'season.poster':'season.jpg','poster':'show.jpg','tvshow.poster':'show.jpg','landscape':'show-wide.jpg'})),{'image':'season.jpg','kind':'portrait'})
 def test_specials_season_zero_uses_its_poster(self):
  self.assertEqual(self.art(self.season({'poster':'specials.jpg','landscape':'show-wide.jpg'},0)),{'image':'specials.jpg','kind':'portrait'})
 def test_missing_season_poster_falls_back_to_show_landscape(self):
  self.assertEqual(self.art(self.season({'tvshow.landscape':'show-wide.jpg','tvshow.poster':'show.jpg'})),{'image':'show-wide.jpg','kind':'landscape'})
 def test_shared_show_poster_does_not_override_wide_fallback(self):
  self.assertEqual(self.art(self.season({'poster':'show.jpg','tvshow.poster':'show.jpg','landscape':'show-wide.jpg'})),{'image':'show-wide.jpg','kind':'landscape'})
 def test_season_without_wide_art_can_use_show_poster(self):
  self.assertEqual(self.art(self.season({'tvshow.poster':'show.jpg'})),{'image':'show.jpg','kind':'portrait'})
 def test_real_episode_keeps_its_thumb_despite_season_poster(self):
  item=self.season({'season.poster':'season.jpg','poster':'season.jpg','thumb':'episode.jpg','landscape':'show-wide.jpg'})
  item.update(file='plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=tv&tmdb_id=1399&season=1&episode=2',filetype='file',episode=2)
  self.assertEqual(self.art(item),{'image':'episode.jpg','kind':'landscape'})
 def test_movie_prefers_landscape_to_backdrop_and_poster(self):
  self.assertEqual(self.art({'art':{'landscape':'title.jpg','fanart':'backdrop.jpg','poster':'poster.jpg'}}),{'image':'title.jpg','kind':'landscape'})
 def test_backdrop_fills_missing_landscape_without_using_portrait(self):
  self.assertEqual(self.art({'art':{'fanart':'backdrop.jpg','poster':'poster.jpg'}}),{'image':'backdrop.jpg','kind':'landscape'})
 def test_poster_is_identified_as_portrait_and_missing_art_as_text(self):
  self.assertEqual(self.art({'art':{'poster':'poster.jpg'}}),{'image':'poster.jpg','kind':'portrait'})
  self.assertEqual(self.art({'art':{}}),{'image':'','kind':'text'})
 def test_show_landscape_alias_is_used_before_poster(self):
  self.assertEqual(self.art({'art':{'tvshow.landscape':'series.jpg','poster':'poster.jpg'}})['image'],'series.jpg')
 def test_long_genres_do_not_consume_watch_state_or_runtime(self):
  item={'year':2026,'genre':['Mystery','Drama','Science Fiction & Fantasy'],'runtime':3180,'mpaa':'TV-MA','resume':{'position':636,'total':3180}}
  info=self.info(item)
  self.assertEqual(info['meta'],'2026  ·  Mystery / Drama / Science Fiction & Fantasy')
  self.assertEqual(info['technical'],'53 min  ·  TV-MA')
  self.assertEqual(info['watch'],'In progress · 20%')
 def test_logos_are_optional_and_missing_values_leave_clean_metadata(self):
  item={'art':{'clearlogo':'logo.png'}}
  self.assertEqual(self.info(item)['logo'],'logo.png')
  self.assertEqual(self.info(item,False)['logo'],'')
  self.assertEqual(self.info({}),{'meta':'','technical':'','watch':'','watch_state':'unknown','logo':''})
 def test_thumbnail_that_is_known_poster_never_becomes_wide_art(self):
  item={'thumbnail':'poster.jpg','art':{'poster':'poster.jpg'}}
  self.assertEqual(self.art(item),{'image':'poster.jpg','kind':'portrait'})

if __name__=='__main__':unittest.main()
