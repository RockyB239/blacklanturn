"""An unavailable neighboring row must not block exact-title account actions."""
import sys,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
from test_window_lifecycle import extract,ROOT
from playback_core import trakt_command,choose_player_path
from search_ui import discovery_result
from browse_controls import can_choose_genre

class TitleActionFailures(unittest.TestCase):
    def run_action(self,target,item=None,focus=900):
        calls=[]
        if item is None:
            item={'file':'plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=tv&tmdb_id=712&season=1&episode=4','title':'Episode'}
        def menu(options):
            return options.index(target) if target in options else -1
        state=SimpleNamespace(row_states={0:'ready',1:'error'},getFocusId=lambda:focus,
            rows=[[item],[]],selected=item,getControl=lambda cid:SimpleNamespace(getSelectedPosition=lambda:0),stop_preview=lambda:None,
            config={'Saved':[]},rating_identity=lambda value:None,actions_open=False,
            refresh_watch_status=lambda **kw:calls.append(('refresh',kw)),
            retry_lists=lambda:calls.append(('retry',{})),settings=lambda:calls.append(('settings',{})))
        chosen=extract(ROOT/'live_review.py','chosen',{},'LiveReview')
        state.chosen=lambda cid:chosen(state,cid)
        ns={'xbmcgui':SimpleNamespace(Dialog=lambda:SimpleNamespace(contextmenu=menu)),
            'trakt_command':trakt_command,'choose_player_path':choose_player_path,'can_choose_genre':can_choose_genre,
            'discovery_result':discovery_result,'event':lambda *a,**kw:None}
        extract(ROOT/'live_review.py','title_actions',ns,'LiveReview')(state)
        return calls,state
    def test_valid_episode_can_refresh_when_neighboring_row_failed(self):
        calls,state=self.run_action('Refresh watched status')
        self.assertEqual(calls,[('refresh',{'sync':True})])
        self.assertFalse(state.actions_open)
    def test_valid_episode_keeps_retry_for_unavailable_neighbor(self):
        calls,_=self.run_action('Retry unavailable lists')
        self.assertEqual(calls,[('retry',{})])
    def test_empty_failed_row_still_offers_retry(self):
        calls,_=self.run_action('Retry unavailable lists',focus=901)
        self.assertEqual(calls,[('retry',{})])
    def test_empty_failed_row_does_not_act_on_a_stale_hero_selection(self):
        calls,_=self.run_action('Refresh watched status',focus=901)
        self.assertEqual(calls,[])

if __name__=='__main__':unittest.main()
