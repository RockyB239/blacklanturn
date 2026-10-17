import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
import live_core

class StalePreview(unittest.TestCase):
 def check(self,item,elapsed):
  self.assertTrue(hasattr(live_core,'clear_stale_preview'))
  calls=[]
  def rpc(method,params=None):
   calls.append(method)
   if method=='Player.GetActivePlayers':return {'result':[{'playerid':1,'type':'video'}]}
   if method=='Player.GetItem':return {'result':{'item':item}}
   if method=='Player.GetProperties':return {'result':{'time':{'minutes':elapsed},'totaltime':{'minutes':2,'seconds':5}}}
   return {'result':'OK'}
  return live_core.clear_stale_preview(rpc),calls
 def test_expired_youtube_trailer_is_released(self):
  cleared,calls=self.check({'file':'plugin://plugin.video.youtube/play/?video_id=ABC','title':'Carrie Official Trailer'},22)
  self.assertTrue(cleared);self.assertIn('Player.Stop',calls)
 def test_a_current_trailer_is_not_stopped(self):
  cleared,calls=self.check({'file':'plugin://plugin.video.youtube/play/?video_id=ABC','title':'Carrie Official Trailer'},1)
  self.assertFalse(cleared);self.assertNotIn('Player.Stop',calls)
 def test_full_playback_is_never_treated_as_a_stale_preview(self):
  for path,title in [('plugin://plugin.video.umbrella/?action=play','A movie'),('plugin://plugin.video.youtube/play/?video_id=ABC','A full movie')]:
   cleared,calls=self.check({'file':path,'title':title},22)
   self.assertFalse(cleared);self.assertNotIn('Player.Stop',calls)
