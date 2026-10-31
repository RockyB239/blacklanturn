import json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace,MethodType
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
import test_experiment_lifecycle as fixture
from youtube_browser import YouTubeBrowser
import youtube_browser
class SidebarStartupEfficiency(unittest.TestCase):
 def test_actual_init_builds_sidebar_once_for_every_connection_outcome(self):
  cases=[({'result':{'addon':{'enabled':True}}},{'access_manager':{'current_user':'0','users':{'0':{'refresh_token':'one|two|three|'}}}}),({'result':{'addon':{'enabled':False}}},{}),({'error':{'message':'Unavailable'}},{})]
  for response,store in cases:
   with self.subTest(response=response),tempfile.TemporaryDirectory() as folder:
    window,queued,effects=fixture.ExperimentLifecycle().state(folder);window.refresh_youtube_connection=MethodType(YouTubeBrowser.refresh_youtube_connection,window);window.apply_youtube_home_rows=lambda:None;window.invalidate_row_results=lambda:None
    with patch.dict(sys.modules,{'xbmc':SimpleNamespace(executeJSONRPC=lambda *a:json.dumps(response))}),patch.object(youtube_browser,'read_account_store',return_value=store):window.onInit()
    self.assertEqual(effects.count('recreate_navigation'),1)
 def test_normal_account_transition_still_redraws_sidebar(self):
  effects=[];window=SimpleNamespace(alive=True,window_lifetime=object(),section='Home',youtube_connection=SimpleNamespace(connected=True,identity='old-account'),apply_youtube_home_rows=lambda:None,invalidate_row_results=lambda:None,setProperty=lambda *a:None,refresh_navigation=lambda:effects.append('redraw'));store={'access_manager':{'current_user':'0','users':{'0':{'refresh_token':'one|two|three|'}}}}
  with patch.dict(sys.modules,{'xbmc':SimpleNamespace(executeJSONRPC=lambda *a:json.dumps({'result':{'addon':{'enabled':True}}}))}),patch.object(youtube_browser,'read_account_store',return_value=store):YouTubeBrowser.refresh_youtube_connection(window,force=True)
  self.assertEqual(effects,['redraw'])
