"""Supported directory and media actions must retain the exact selected item."""
import unittest
from types import SimpleNamespace
from test_window_lifecycle import ROOT,extract
from playback_core import choose_player_path,resume_options,trakt_command
from search_ui import discovery_result
from browse_controls import can_choose_genre
class OptionsTypes(unittest.TestCase):
 def test_directory_first_action_opens_selected_folder_without_stale_hero(self):
  chosen={'title':'Show','file':'plugin://plugin.video.themoviedb.helper/?info=seasons&tmdb_type=tv&tmdb_id=2316','filetype':'directory'}
  state=SimpleNamespace(getFocusId=lambda:900,rows=[[chosen],[]],chosen=lambda cid:chosen,row_states={},config={'Saved':[]},rating_identity=lambda i:None,selected={'file':'wrong'},stop_preview=lambda:None,actions_open=False)
  calls=[]
  state.update=lambda item:setattr(state,'selected',item);state.onClick=lambda cid:calls.append(state.selected['file'])
  ns={'resume_options':resume_options,'choose_player_path':choose_player_path,'trakt_command':trakt_command,'discovery_result':discovery_result,'can_choose_genre':can_choose_genre,'event':lambda *a,**k:None,'xbmcgui':SimpleNamespace(Dialog=lambda:SimpleNamespace(contextmenu=lambda options:0))}
  state.details=lambda item:self.fail('First folder action opened Details instead of its episodes')
  extract(ROOT/'live_review.py','title_actions',ns,'LiveReview')(state)
  self.assertEqual(calls,[chosen['file']])
