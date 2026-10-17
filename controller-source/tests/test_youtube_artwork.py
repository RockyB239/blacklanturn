"""Use provider-verified wide thumbnails without changing playback intent."""
import copy,unittest
from youtube_artwork import fit_cards,cached_fit_cards
class YouTubeArtwork(unittest.TestCase):
 def test_highest_verified_wide_thumbnail_keeps_playback_watch_and_resume(self):
  item={'file':'plugin://plugin.video.youtube/play/?video_id=Abc_123-Xyz&resume=true','filetype':'file','art':{'thumb':'padded.jpg'},'resume':{'position':20,'total':600},'playcount':1};before=copy.deepcopy(item)
  metadata={'Abc_123-Xyz':{'snippet':{'thumbnails':{'high':{'url':'padded.jpg','width':480,'height':360},'medium':{'url':'medium.jpg','width':320,'height':180},'maxres':{'url':'wide.jpg','width':1280,'height':720}}}}}
  result=fit_cards([item],metadata)[0]
  self.assertEqual(result['art']['thumb'],'wide.jpg');self.assertEqual(result['file'],before['file']);self.assertEqual(result['resume'],before['resume']);self.assertEqual(result['playcount'],1);self.assertEqual(item,before)
  self.assertEqual(result['art']['youtubefallback'],'https://i.ytimg.com/vi/Abc_123-Xyz/mqdefault.jpg')
  metadata['Abc_123-Xyz']['snippet']['thumbnails']['invented']={'url':'404.jpg','width':3840,'height':2160,'unverified':True}
  self.assertEqual(fit_cards([item],metadata)[0]['art']['thumb'],'wide.jpg')
 def test_missing_metadata_falls_back_to_known_unpadded_video_variant_only(self):
  video={'file':'plugin://plugin.video.youtube/play/?video_id=Abc_123-Xyz','filetype':'file','art':{'thumb':'padded.jpg'}}
  folder={'file':'plugin://plugin.video.youtube/channel/example/','filetype':'directory','art':{'thumb':'channel.jpg'}}
  result=fit_cards([video,folder],{})
  self.assertEqual(result[0]['art']['thumb'],'https://i.ytimg.com/vi/Abc_123-Xyz/mqdefault.jpg');self.assertEqual(result[1],folder)

 def test_directory_cards_do_not_create_provider_context_or_read_account_cache(self):
  from unittest.mock import patch
  import builtins
  original=builtins.__import__
  def guarded(name,*args,**kwargs):
   if name.startswith(('xbmc','youtube_plugin')):raise AssertionError('Artwork must not create provider resources')
   return original(name,*args,**kwargs)
  item={'file':'plugin://plugin.video.youtube/play/?video_id=Abc_123-Xyz','filetype':'file','playcount':1,'resume':{'position':31},'art':{'thumb':'https://i.ytimg.com/vi/Abc_123-Xyz/fhddefault.jpg'}}
  with patch('builtins.__import__',guarded):result=cached_fit_cards([item])[0]
  self.assertEqual(result['art']['thumb'],'https://i.ytimg.com/vi/Abc_123-Xyz/maxresdefault.jpg')
  self.assertEqual(result['art']['youtubefallback'],'https://i.ytimg.com/vi/Abc_123-Xyz/mqdefault.jpg')
  self.assertEqual(result['playcount'],1);self.assertEqual(result['resume'],{'position':31})
