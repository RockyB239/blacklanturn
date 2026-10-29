"""Preview workers must not overtake Options, even after the monitor's guard."""
import time,unittest
import test_episode_options as menu_fixtures
import test_preview_input_epoch as epoch_fixtures
import test_preview_navigation_stop as candidate_fixtures
from test_window_lifecycle import ROOT,extract

class PreviewOptionsFocus(unittest.TestCase):
    def test_options_claims_modal_ownership_before_focus_lookup(self):
        def lookup(w):
            self.assertTrue(w.actions_open,'Options must block preview before native focus reads')
            self.assertGreater(w.input_generation,0,'Old preview work must be invalidated before yielding')
            return 900
        menu_fixtures.EpisodeOptions.run_menu(self,cancel=True,on_focus=lookup)
    def test_options_blocks_preview_before_stop_can_yield(self):
        def stop(w):self.assertTrue(w.actions_open,'Stop cleanup can yield to the preview monitor')
        menu_fixtures.EpisodeOptions.run_menu(self,cancel=True,on_stop=stop)
    def test_cancel_starts_a_fresh_normal_preview_delay(self):
        before=time.monotonic();w,_,_=menu_fixtures.EpisodeOptions.run_menu(self,cancel=True)
        self.assertGreaterEqual(w.dwell,before)
    def test_lookup_cannot_start_under_options_or_settings(self):
        for modal in ('actions_open','settings_open'):
            with self.subTest(modal=modal):
                w,calls=epoch_fixtures.PreviewInputEpoch().state();setattr(w,modal,True)
                w.preview(automatic=True)
                self.assertNotIn('worker',calls);self.assertFalse(w.owned_preview)
    def test_long_genre_cancel_restarts_delay_before_focus_returns(self):
        w,calls=epoch_fixtures.PreviewInputEpoch().state();w.section='Shows';w.browse_sources=[];w.active_page=None
        def choose(*args):w.dwell=time.monotonic()-30;return None
        extract(ROOT/'live_review.py','browse_source',{'choose_genre':choose},'LiveReview')(w)
        w.preview(automatic=True)
        self.assertNotIn('worker',calls)
    def test_long_trakt_dialog_keeps_modal_through_focus_restore(self):
        from types import SimpleNamespace
        from playback_core import choose_player_path,trakt_command,resume_options
        from search_ui import discovery_result
        from browse_controls import can_choose_genre
        w,_,_=menu_fixtures.EpisodeOptions.run_menu(self,cancel=True)
        w.alive=True;restored=[]
        w.set_browse_enabled=lambda enabled:None
        w.setFocusId=lambda focus:restored.append((w.actions_open,time.monotonic()-w.dwell))
        w.refresh_watch_status=lambda:None
        class Inline:
            def __init__(self,target,**kw):self.target=target
            def start(self):self.target()
        def wait(current):w.dwell=time.monotonic()-30;return True
        ns={'resume_options':resume_options,'discovery_result':discovery_result,'trakt_command':trakt_command,'choose_player_path':choose_player_path,'can_choose_genre':can_choose_genre,'event':lambda *a,**k:None,
            'wait_for_helper':wait,'threading':SimpleNamespace(Thread=Inline),'xbmc':SimpleNamespace(executebuiltin=lambda *a:None),'xbmcgui':SimpleNamespace(Dialog=lambda:SimpleNamespace(contextmenu=lambda labels:labels.index('Trakt: Watched, progress & lists')))}
        extract(ROOT/'live_review.py','title_actions',ns,'LiveReview')(w)
        self.assertTrue(restored[0][0],'Returning focus must still be protected')
        self.assertLess(time.monotonic()-w.dwell,1)
    def test_long_discovery_cancel_restarts_delay(self):
        from types import SimpleNamespace
        w,calls=epoch_fixtures.PreviewInputEpoch().state()
        def select(*args):w.dwell=time.monotonic()-30;return -1
        ns={'event':lambda *a,**k:None,'xbmcgui':SimpleNamespace(Dialog=lambda:SimpleNamespace(select=select))}
        extract(ROOT/'live_review.py','discover_more',ns,'LiveReview')(w,{})
        w.preview(automatic=True);self.assertNotIn('worker',calls)
    def test_title_feedback_claims_modal_before_preview_cleanup(self):
        from types import SimpleNamespace
        w,_=epoch_fixtures.PreviewInputEpoch().state()
        def stop():self.assertTrue(w.actions_open)
        def unavailable(item):raise ValueError('fixture unavailable')
        w.stop_preview=stop;w.title_preferences=SimpleNamespace(state=unavailable)
        ns={'xbmcgui':SimpleNamespace(Dialog=lambda:SimpleNamespace(ok=lambda *a:None))}
        extract(ROOT/'title_feedback_ui.py','change_title_feedback',ns,'TitleFeedback')(w,{},'title_hide')
    def test_long_feedback_error_dialog_restarts_delay(self):
        from types import SimpleNamespace
        w,calls=epoch_fixtures.PreviewInputEpoch().state()
        def unavailable(item):raise ValueError('fixture unavailable')
        def dialog(*args):w.dwell=time.monotonic()-30
        w.title_preferences=SimpleNamespace(state=unavailable)
        ns={'xbmcgui':SimpleNamespace(Dialog=lambda:SimpleNamespace(ok=dialog))}
        extract(ROOT/'title_feedback_ui.py','change_title_feedback',ns,'TitleFeedback')(w,{},'title_hide')
        w.preview(automatic=True);self.assertNotIn('worker',calls)
    def test_resolved_candidate_cannot_dispatch_under_options(self):
        w,method,calls,_=candidate_fixtures.PreviewNavigationStop().candidate();w.actions_open=True
        method(w,'plugin://plugin.video.youtube/play/?video_id=test')
        self.assertFalse(any(isinstance(c,tuple) and c[0]=='play' for c in calls))
    def test_menu_opening_during_renderer_preparation_cancels_dispatch(self):
        w,method,calls,_=candidate_fixtures.PreviewNavigationStop().candidate(lambda w,stop:setattr(w,'actions_open',True))
        method(w,'plugin://plugin.video.youtube/play/?video_id=test')
        self.assertFalse(any(isinstance(c,tuple) and c[0]=='play' for c in calls))
