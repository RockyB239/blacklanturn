"""Account actions must target the exact item; playback must not cover providers."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
import importlib.util

class PlaybackContracts(unittest.TestCase):
    def core(self):
        path=Path(__file__).parents[1]/'addon/playback_core.py'
        self.assertTrue(path.exists(),'Playback return and action contracts are missing')
        spec=importlib.util.spec_from_file_location('playback_core',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
    def test_episode_trakt_action_uses_show_id_season_and_episode(self):
        core=self.core()
        item={'file':'plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=tv&tmdb_id=123&season=0&episode=2','uniqueid':{'tmdb':'999'}}
        self.assertEqual(core.trakt_command(item),'RunScript(plugin.video.themoviedb.helper,sync_trakt,tmdb_type=tv,tmdb_id=123,season=0,episode=2)')
    def test_actions_do_not_run_for_people_missing_or_injected_ids(self):
        core=self.core()
        for path in ['plugin://plugin.video.themoviedb.helper/?info=details&tmdb_type=person&tmdb_id=12','plugin://plugin.video.test/','plugin://plugin.video.themoviedb.helper/?tmdb_type=movie&tmdb_id=1%29%2CQuit']:
            self.assertIsNone(core.trakt_command({'file':path}))
    def test_choose_player_only_changes_helper_play_request(self):
        core=self.core()
        path='plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=tv&tmdb_id=123&season=1&episode=2'
        self.assertEqual(core.choose_player_path({'file':path,'filetype':'file'}),path+'&ignore_default=true')
        self.assertIsNone(core.choose_player_path({'file':'plugin://plugin.video.umbrella/?action=play','filetype':'file'}))
        self.assertIsNone(core.choose_player_path({'file':path,'filetype':'directory'}))
    def test_refresh_tracks_exact_episode_across_reordering(self):
        core=self.core()
        old={'file':'plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=tv&tmdb_id=12&season=1&episode=2'}
        different={'file':'plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=tv&tmdb_id=12&season=1&episode=3'}
        same={'file':old['file']+'&widget=true','resume':{'position':25,'total':100}}
        self.assertEqual(core.restored_position([different,same],old,0),1)
        self.assertEqual(core.restored_position([different],old,10),0)
        self.assertEqual(core.restored_position([],old,10),0)
    def test_missing_watch_metadata_does_not_turn_unknown_into_unwatched(self):
        core=self.core()
        old={'file':'exact-source','playcount':1,'resume':{'position':10,'total':100},'title':'Original'}
        self.assertEqual(core.refreshed_watch_item(old,{'title':'Other'}),old)
        updated=core.refreshed_watch_item(old,{'playcount':0,'resume':{'position':0,'total':100}})
        self.assertEqual(updated,{'file':'exact-source','playcount':0,'resume':{'position':0,'total':100},'title':'Original'})
    def test_resume_uses_exact_provider_progress_and_rejects_invalid_positions(self):
        core=self.core()
        self.assertEqual(core.resume_options({'resume':{'position':227,'total':1000}}),{'resume':True})
        for position,total in [(0,100),(100,100),(-2,100),(25,0),(float('nan'),100),(25,float('inf')),('bad',100)]:
            self.assertEqual(core.resume_options({'resume':{'position':position,'total':total}}),{})
        self.assertEqual(core.resume_options({}),{})
    def test_silent_sync_uses_empty_value_for_helpers_string_parameter_parser(self):
        command=self.core().watch_sync_command()
        args=command[len('RunScript('):-1].split(',')[1:]
        params=dict(arg.split('=',1) for arg in args)
        self.assertEqual(params['invalidate_sync'],'watched')
        self.assertFalse(params['notification'])
        self.assertFalse(params['sync'])
    def test_resume_fallback_only_targets_the_original_episode_once_ready(self):
        core=self.core();target={'title':'Beforeigners','season':1,'episode':2,'resume':{'position':9,'total':100}}
        guard=core.ResumeHandoff(target)
        current={'type':'episode','showtitle':'Beforeigners','season':1,'episode':2}
        self.assertIsNone(guard.tick(current,0,10))
        self.assertEqual(guard.tick(current,0,14),9)
        self.assertIsNone(guard.tick(current,0,20))
        guard=core.ResumeHandoff(target)
        guard.tick(current,9.2,10)
        self.assertIsNone(guard.tick(current,9.2,14))
        guard=core.ResumeHandoff(target)
        different={**current,'episode':3}
        guard.tick(different,0,10)
        self.assertIsNone(guard.tick(different,0,14))
        self.assertIsNone(guard.tick(current,0,20))
    def test_source_dialogs_and_episode_transitions_do_not_reopen_browsing(self):
        core=self.core();gate=core.PlaybackReturnGate(0)
        self.assertEqual(gate.tick(False,True,True,20),'wait')
        self.assertEqual(gate.tick(True,False,True,30),'wait')
        self.assertEqual(gate.tick(False,True,True,100),'wait')
        self.assertEqual(gate.tick(True,False,True,101),'wait')
        self.assertEqual(gate.tick(False,False,True,200),'wait')
        self.assertEqual(gate.tick(False,False,True,203),'return')
    def test_cancelled_or_failed_source_selection_returns_without_playback(self):
        core=self.core();gate=core.PlaybackReturnGate(0)
        self.assertEqual(gate.tick(False,True,True,5),'wait')
        self.assertEqual(gate.tick(False,False,True,8),'wait')
        self.assertEqual(gate.tick(False,False,True,11),'wait')
        self.assertEqual(gate.tick(False,False,True,16),'return')
        self.assertFalse(gate.played)
    def test_other_skin_and_external_windows_do_not_get_covered(self):
        core=self.core();gate=core.PlaybackReturnGate(0)
        self.assertEqual(gate.tick(False,False,False,15),'wait')
        self.assertEqual(gate.tick(False,False,True,16,owner=False),'abandon')

if __name__=='__main__':unittest.main()
