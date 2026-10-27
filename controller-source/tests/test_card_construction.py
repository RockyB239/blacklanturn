"""Unattached cards avoid GUI locking; current metadata must still hydrate."""
import unittest,tempfile
from native_list_fixture import media_functions

class CardConstruction(unittest.TestCase):
 def test_unattached_cards_keep_current_playback_and_display_metadata(self):
  build=media_functions()['media_item']
  data={'file':'plugin://plugin.video.youtube/play/?video_id=abcdefghijk','title':'A video','runtime':120,'playcount':1,'resume':{'position':23,'total':120},'studio':['Channel'],'art':{'thumb':'https://i.ytimg.com/vi/abcdefghijk/mqdefault.jpg'}}
  item=build(data,immutable=True)
  self.assertTrue(item.offscreen,'Cards must be built before container attachment without the GUI lock')
  self.assertEqual(item.getPath(),data['file']);self.assertEqual(item.info['playcount'],1)
  self.assertEqual(item.resume,(23,120));self.assertEqual(item.properties['episodeCaption'],'A video')
  self.assertEqual(item.art['thumb'],data['art']['thumb'])
  # A fresh row is rebuilt from new state rather than reusing a stale native item.
  data.update(playcount=0,resume={'position':0,'total':120});fresh=build(data,immutable=True)
  self.assertEqual(fresh.info['playcount'],0);self.assertEqual(fresh.resume,(0.,0.))
  self.assertIsNot(fresh,item)
 def test_mutable_cards_and_personal_extensions_keep_native_locking(self):
  build=media_functions()['media_item']
  for path in ('plugin://plugin.video.youtube/play/?video_id=abcdefghijk','plugin://slyguy.paramount.plus/?_=play','plugin://plugin.video.themoviedb.helper/?info=details&tmdb_type=tv&tmdb_id=1'):
   self.assertFalse(build({'file':path,'title':'Mutable card'}).offscreen)
 def test_only_youtube_browser_rows_opt_in_and_watch_refresh_replaces_cards(self):
  from test_snapshot_controller import SnapshotController
  path='plugin://plugin.video.youtube/special/recommendations'
  first={'file':'plugin://plugin.video.youtube/play/?video_id=abcdefghijk','title':'Video','playcount':0}
  with tempfile.TemporaryDirectory() as folder:
   state,calls,controls,queue=SnapshotController().state(folder,lambda p:[first])
   state.youtube_saved_guard=lambda current:current
   state.section='YouTube';state.set_rows([{'path':path,'label':'Recommended','local_items':[first]}]);queue.pop(0)()
   card=controls[900].items[0];self.assertTrue(card.offscreen)
   state.apply_row(0,[dict(first,playcount=1)],'Recommended')
   self.assertIsNot(controls[900].items[0],card);self.assertEqual(controls[900].items[0].info['playcount'],1)
   state.section='Fight Zone';state.apply_row(0,[first],'Personal clips')
   self.assertFalse(controls[900].items[0].offscreen)
