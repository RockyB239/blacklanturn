import unittest
from native_list_fixture import media_functions
from watch_metadata import hydrate_watch_metadata

class MetadataBatch(unittest.TestCase):
 def test_fresh_card_skips_only_native_defaults_not_needed_until_displayed(self):
  item=media_functions()['media_item']({'file':'video','title':'Title'})
  self.assertFalse(item.offscreen);self.assertEqual(item.resume,(0.,0.));self.assertEqual(item.resume_calls,0)
  for key in ('pageControl','watchLabel','episodeMeta'):self.assertEqual(item.getProperty(key),'');self.assertNotIn(key,item.properties)
  self.assertEqual(item.getProperty('watchPercent'),'0');self.assertEqual(item.getProperty('watchState'),'unknown')
 def test_displayed_refresh_still_explicitly_clears_empty_properties_and_resume(self):
  item=media_functions()['media_item']({'file':'video','title':'Title','resume':{'position':23,'total':120}})
  self.assertEqual(item.resume_calls,1)
  hydrate_watch_metadata(item,{'file':'video'})
  self.assertEqual(item.resume_calls,2);self.assertEqual(item.resume,(0.,0.))
  self.assertIn('watchLabel',item.properties);self.assertEqual(item.properties['watchLabel'],'')
 def test_fresh_locked_card_batches_metadata_without_losing_caption_art_or_progress(self):
  data={'file':'plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=tv&tmdb_id=1&season=1&episode=1','title':'Episode','showtitle':'Show','season':1,'episode':1,'runtime':120,'playcount':1,'resume':{'position':23,'total':120},'art':{'thumb':'image.jpg'}}
  item=media_functions()['media_item'](data)
  self.assertFalse(item.offscreen);self.assertEqual(item.info_calls,1);self.assertEqual(item.property_batches,1)
  self.assertEqual(item.resume,(23,120));self.assertEqual(item.art['thumb'],'image.jpg')
  self.assertEqual(item.properties['watchState'],'progress');self.assertTrue(item.properties['episodeCaption'])
  self.assertEqual(item.info['duration'],120);self.assertEqual(item.info['playcount'],1)
 def test_displayed_watch_refresh_clears_resume_and_keeps_existing_art_caption_and_metadata(self):
  item=media_functions()['media_item']({'file':'video','title':'Title','year':2026,'playcount':0,'resume':{'position':23,'total':120},'art':{'thumb':'image.jpg'}})
  art=dict(item.art);caption=item.properties['episodeCaption']
  hydrate_watch_metadata(item,{'playcount':1,'resume':{}})
  self.assertEqual(item.resume,(0.,0.));self.assertEqual(item.info['playcount'],1);self.assertEqual(item.info['year'],2026)
  self.assertEqual(item.properties['watchState'],'watched');self.assertEqual(item.properties['episodeCaption'],caption);self.assertEqual(item.art,art)
