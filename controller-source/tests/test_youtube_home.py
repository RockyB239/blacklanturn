"""Adaptive Home comes from provider shelves, never hard-coded topic searches."""
import copy,unittest
from urllib.parse import parse_qs,urlsplit
import youtube_home as home
from youtube_artwork import fit_cards

def shelf(label,ids):
 return {'shelfRenderer':{'headerRenderer':{'shelfHeaderRenderer':{'avatarLockup':{'avatarLockupRenderer':{'title':{'runs':[{'text':label}]}}}}},'content':{'horizontalListRenderer':{'items':[{'tileRenderer':{'onSelectCommand':{'watchEndpoint':{'videoId':i}},'metadata':{'tileMetadataRenderer':{'title':{'simpleText':'A video'}}},'header':{'tileHeaderRenderer':{'thumbnail':{'thumbnails':[{'url':'https://i.ytimg.com/vi/'+i+'/hq720.jpg','width':640,'height':360}]}}}}} for i in ids]}}}}
def response(*rows):return {'contents':{'tvBrowseRenderer':{'content':{'tvSurfaceContentRenderer':{'content':{'sectionListRenderer':{'contents':list(rows),'continuations':[{'nextContinuationData':{'continuation':'page-token','clickTrackingParams':'tracking'}}]}}}}}}}

class AdaptiveHome(unittest.TestCase):
 def test_real_shelf_labels_and_order_follow_each_response(self):
  a=response(shelf('Recommended',['Abc_123-Xyz']),shelf('Science and more',['Def_123-Xyz']))
  b=response(shelf('Recommended',['Abc_123-Xyz']),shelf('A different interest',['Ghi_123-Xyz']))
  self.assertEqual([x['label'] for x in home.parse_shelves(a)],['Recommended','Science and more'])
  self.assertEqual(home.parse_shelves(b)[1]['label'],'A different interest')
 def test_unsupported_and_empty_tiles_do_not_create_fake_rows(self):
  self.assertEqual(home.parse_shelves({'unrelated':{}}),[])
  self.assertEqual(home.parse_shelves(response(shelf('Channels',[]),shelf('Invalid',['not-video']))),[])
 def test_section_continuation_does_not_take_a_video_row_token(self):
  a=response(shelf('Recommended',['Abc_123-Xyz']))
  a['contents']['tvBrowseRenderer']['content']['tvSurfaceContentRenderer']['content']['sectionListRenderer']['contents'][0]['shelfRenderer']['content']['horizontalListRenderer']['continuations']=[{'nextContinuationData':{'continuation':'wrong-row'}}]
  self.assertEqual(home.section_continuation(a)['continuation'],'page-token')
 def test_cards_use_highest_verified_wide_thumbnail_and_keep_normal_playback(self):
  item={'file':'plugin://plugin.video.youtube/play/?video_id=Abc_123-Xyz&resume=true','filetype':'file','art':{'thumb':'padded.jpg'},'resume':{'position':20,'total':600},'playcount':1};before=copy.deepcopy(item)
  metadata={'Abc_123-Xyz':{'snippet':{'thumbnails':{'high':{'url':'padded.jpg','width':480,'height':360},'medium':{'url':'medium.jpg','width':320,'height':180},'maxres':{'url':'wide.jpg','width':1280,'height':720}}}}}
  result=fit_cards([item],metadata)[0]
  self.assertEqual(result['art']['thumb'],'wide.jpg');self.assertEqual(result['file'],before['file']);self.assertEqual(result['resume'],before['resume']);self.assertEqual(result['playcount'],1);self.assertEqual(item,before)
 def test_rows_preserve_provider_full_play_urls_without_preview_flags(self):
  payload=response(shelf('Your interest',['Abc_123-Xyz']))
  items={'Abc_123-Xyz':{'file':'plugin://plugin.video.youtube/play/?video_id=Abc_123-Xyz','filetype':'file','title':'A video'}}
  rows=home.local_rows(home.parse_shelves(payload),items)
  self.assertEqual(rows[0]['label'],'Your interest');self.assertEqual(rows[0]['local_items'],list(items.values()))
  self.assertNotIn('incognito',parse_qs(urlsplit(rows[0]['local_items'][0]['file']).query))
