from types import SimpleNamespace, MethodType
import unittest
from test_window_lifecycle import ROOT,extract
from live_core import episode_identity,is_browse_folder
from search_ui import discovery_result
from playback_core import resume_options

class EpisodeClick(unittest.TestCase):
 def test_episode_select_returns_play_request_and_preserves_resume_and_browse_state(self):
  item={'file':'plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=tv&tmdb_id=123&season=1&episode=4','filetype':'file','title':'Episode','showtitle':'Show','season':1,'episode':4,'resume':{'position':20,'total':100}}
  calls=[];context={'section':'Shows','position':4}
  state=SimpleNamespace(actions_open=False,chosen=lambda cid:item,stop_preview=lambda:calls.append('stop'),finish=lambda:calls.append('finish'),capture_browse=lambda:context,details=lambda x:calls.append('details'))
  def update(x):state.selected=x
  state.update=update
  ns={'episode_identity':episode_identity,'is_browse_folder':is_browse_folder,'discovery_result':discovery_result,'resume_options':resume_options}
  state.onClick=MethodType(extract(ROOT/'live_review.py','onClick',ns,'LiveReview'),state)
  state.onClick(900)
  self.assertEqual(calls,['stop','finish']);self.assertEqual(state.playback_request,item['file']);self.assertEqual(state.playback_return,context);self.assertEqual(state.playback_options,{'resume':True})
if __name__=='__main__':unittest.main()
