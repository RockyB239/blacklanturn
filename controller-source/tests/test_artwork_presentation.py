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
 def test_season_folder_prefers_wide_show_art_over_portrait_and_episode_count(self):
  self.assertEqual(self.art(self.season({'poster':'season1.jpg','tvshow.poster':'show.jpg','landscape':'show-wide.jpg'})),{'image':'show-wide.jpg','kind':'landscape'})
 def test_season_poster_does_not_override_available_wide_art(self):
  self.assertEqual(self.art(self.season({'season.poster':'season.jpg','poster':'show.jpg','tvshow.poster':'show.jpg','landscape':'show-wide.jpg'})),{'image':'show-wide.jpg','kind':'landscape'})
 def test_specials_season_zero_uses_wide_art(self):
  self.assertEqual(self.art(self.season({'poster':'specials.jpg','landscape':'show-wide.jpg'},0)),{'image':'show-wide.jpg','kind':'landscape'})
 def test_missing_season_poster_falls_back_to_show_landscape(self):
  self.assertEqual(self.art(self.season({'tvshow.landscape':'show-wide.jpg','tvshow.poster':'show.jpg'})),{'image':'show-wide.jpg','kind':'landscape'})
 def test_shared_show_poster_does_not_override_wide_fallback(self):
  self.assertEqual(self.art(self.season({'poster':'show.jpg','tvshow.poster':'show.jpg','landscape':'show-wide.jpg'})),{'image':'show-wide.jpg','kind':'landscape'})
 def test_season_without_wide_art_keeps_landscape_frame_for_poster_fallback(self):
  self.assertEqual(self.art(self.season({'tvshow.poster':'show.jpg'})),{'image':'show.jpg','kind':'landscape'})
 def test_real_episode_keeps_its_thumb_despite_season_poster(self):
  item=self.season({'season.poster':'season.jpg','poster':'season.jpg','thumb':'episode.jpg','landscape':'show-wide.jpg'})
  item.update(file='plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=tv&tmdb_id=1399&season=1&episode=2',filetype='file',episode=2)
  self.assertEqual(self.art(item),{'image':'episode.jpg','kind':'landscape'})
 def test_movie_prefers_landscape_to_backdrop_and_poster(self):
  self.assertEqual(self.art({'art':{'landscape':'title.jpg','fanart':'backdrop.jpg','poster':'poster.jpg'}}),{'image':'title.jpg','kind':'landscape'})
 def test_backdrop_fills_missing_landscape_without_using_portrait(self):
  self.assertEqual(self.art({'art':{'fanart':'backdrop.jpg','poster':'poster.jpg'}}),{'image':'backdrop.jpg','kind':'landscape'})
 def test_poster_fallback_keeps_landscape_kind_and_missing_art_as_text(self):
  self.assertEqual(self.art({'art':{'poster':'poster.jpg'}}),{'image':'poster.jpg','kind':'landscape'})
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
  self.assertEqual(self.art(item),{'image':'poster.jpg','kind':'landscape'})

if __name__=='__main__':unittest.main()

class LandscapeContracts(unittest.TestCase):
 def test_specific_season_landscape_wins_without_falling_back_to_its_poster(self):
  item={'file':'plugin://plugin.video.themoviedb.helper/?info=episodes&tmdb_type=tv&tmdb_id=1413&season=2','filetype':'directory','episode':13,'art':{'season.landscape':'asylum-wide.jpg','landscape':'generic-wide.jpg','season.poster':'asylum-poster.jpg'}}
  self.assertEqual(live_core.card_artwork(item),{'image':'asylum-wide.jpg','kind':'landscape'})
 def test_wide_alias_that_is_the_known_poster_is_framed_as_a_poster_fallback(self):
  item={'art':{'landscape':'poster.jpg','poster':'poster.jpg','tvshow.fanart':'real-wide.jpg'}}
  self.assertEqual(live_core.card_artwork(item),{'image':'real-wide.jpg','kind':'landscape'})
 def test_next_page_media_with_only_a_poster_keeps_the_same_kind_as_first_page(self):
  wide={'art':{'landscape':'one-wide.jpg','poster':'one-poster.jpg'}};poster={'art':{'poster':'two-poster.jpg'}}
  self.assertEqual([live_core.card_artwork(x)['kind'] for x in (wide,poster)],['landscape','landscape'])
 def test_cast_portrait_identity_remains_separate_from_media_shelves(self):
  person={'file':'plugin://plugin.video.themoviedb.helper/?info=details&tmdb_type=person&tmdb_id=1','type':'person','art':{'poster':'actor.jpg'}}
  self.assertEqual(live_core.card_artwork(person),{'image':'actor.jpg','kind':'portrait'})
 def test_native_card_marks_poster_only_for_the_fixed_wide_fallback_frame(self):
  from test_window_lifecycle import extract
  from native_list_fixture import NativeItem
  from types import SimpleNamespace
  from watch_metadata import hydrate_watch_metadata
  from live_core import episode_heading
  from episode_ui import episode_card
  p=Path(__file__).parents[1]/'addon/live_review.py'
  ns={'xbmcgui':SimpleNamespace(ListItem=NativeItem),'episode_heading':episode_heading,'card_artwork':live_core.card_artwork,'is_youtube':lambda _:False,'episode_card':episode_card,'hydrate_watch_metadata':hydrate_watch_metadata}
  media=extract(p,'media_item',ns)
  x=media({'label':'Missing wide art','art':{'poster':'poster.jpg'},'resume':{'position':10,'total':100}})
  self.assertEqual(x.properties.get('cardArtKind'),'landscape');self.assertEqual(x.properties.get('cardPosterFallback'),'true');self.assertEqual(x.resume,(10.,100.))
  y=media({'label':'Wide art','art':{'poster':'poster.jpg','landscape':'wide.jpg'}})
  self.assertEqual(y.properties.get('cardPosterFallback'),'false')
 def test_native_media_shelf_layouts_fill_wide_viewports_and_frame_poster_fallbacks(self):
  import xml.etree.ElementTree as E
  root=E.parse(Path(__file__).parents[1]/'addon/resources/skins/Default/1080i/LiveReview.xml')
  for cid in ('900','901','3100'):
   row=next(c for c in root.iter('control') if c.get('id')==cid)
   layouts=[c for c in row if c.tag in ('itemlayout','focusedlayout') and c.get('condition','') != 'String.IsEqual(Window.Property(youtubeBrowser),true)' and 'String.IsEqual(Window.Property(addonBrowser),true)'!=c.get('condition','')]
   for layout in layouts:
    with self.subTest(cid=cid,layout=layout.tag,condition=layout.get('condition')):
     normal=[c for c in layout.findall('control') if c.findtext('texture')=='$INFO[ListItem.Art(landscape)]']
     self.assertTrue(normal)
     self.assertTrue(all(c.findtext('aspectratio')=='scale' for c in normal),'Media must fill its fixed wide viewport')
     framed=[g for g in layout.findall('control') if g.get('type')=='group' and 'cardPosterFallback' in (g.findtext('visible') or '')]
     self.assertEqual(len(framed),1,'Poster fallback needs one fixed landscape group')
     images=framed[0].findall('control');back=images[0]
     self.assertGreater(int(back.findtext('width'))/int(back.findtext('height')),1.7)
     self.assertTrue(any(c.findtext('aspectratio')=='keep' for c in images),'A portrait-only fallback must not be stretched or cropped')
 def test_personal_episode_still_beats_shared_show_art_without_tmdb_route(self):
  item={'file':'plugin://slyguy.paramount.plus/?_=play&id=episode1','filetype':'file','season':34,'episode':1,'art':{'thumb':'episode-wide.jpg','landscape':'show-wide.jpg','poster':'show-poster.jpg'}}
  self.assertEqual(live_core.card_artwork(item),{'image':'episode-wide.jpg','kind':'landscape'})

class LandscapeCaptionContracts(unittest.TestCase):
 def test_compact_episode_and_season_cards_retain_visible_identity(self):
  import xml.etree.ElementTree as E
  root=E.parse(Path(__file__).parents[1]/'addon/resources/skins/Default/1080i/LiveReview.xml')
  for cid in ('900','901'):
   row=next(c for c in root.iter('control') if c.get('id')==cid)
   layouts=[c for c in row if c.tag in ('itemlayout','focusedlayout') and c.get('height')=='276']
   self.assertEqual(len(layouts),2)
   for layout in layouts:
    groups=[g for g in layout.findall('control') if g.get('type')=='group' and 'cardEpisodeLabel' in g.findtext('visible','')]
    self.assertEqual(len(groups),1)
    self.assertTrue(any(c.findtext('label')=='$INFO[ListItem.Label]' for c in groups[0]))
 def test_captioned_layouts_are_explicitly_covered(self):
  import xml.etree.ElementTree as E
  root=E.parse(Path(__file__).parents[1]/'addon/resources/skins/Default/1080i/LiveReview.xml')
  layouts=[l for cid in ('900','901') for row in root.iter('control') if row.get('id')==cid for l in row if l.tag in ('itemlayout','focusedlayout') and l.get('width')=='496' and l.get('height')=='344']
  self.assertEqual(len(layouts),4)
  for layout in layouts:
   self.assertTrue(any('cardPosterFallback' in g.findtext('visible','') for g in layout.findall('control')))

class LandscapeReadableCaptions(unittest.TestCase):
 def test_every_standard_caption_layout_keeps_a_readable_media_name(self):
  import xml.etree.ElementTree as E
  root=E.parse(Path(__file__).parents[1]/'addon/resources/skins/Default/1080i/LiveReview.xml')
  for row in root.iter('control'):
   if row.get('id') not in ('900','901'):continue
   for layout in row:
    if layout.tag not in ('itemlayout','focusedlayout') or layout.get('width')!='496' or layout.get('height')!='344':continue
    captions=[c for c in layout.findall('control') if c.findtext('label')=='$INFO[ListItem.Label]' and int(c.findtext('top','0'))>=264]
    self.assertEqual(len(captions),1)
    self.assertGreaterEqual(int(captions[0].findtext('width')),460)
