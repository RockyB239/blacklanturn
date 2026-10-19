"""The first episode action must play that episode, retaining its resume data."""
import copy
from types import SimpleNamespace
import unittest

from test_window_lifecycle import ROOT, extract
from playback_core import choose_player_path, resume_options, trakt_command
from search_ui import discovery_result
from browse_controls import can_choose_genre


class EpisodeOptions(unittest.TestCase):
    def run_menu(self, resume=None, cancel=False):
        item = {
            'file': 'plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=tv&tmdb_id=712&season=1&episode=4',
            'title': 'Selected episode', 'filetype': 'file',
            'art': {'thumb': 'selected-episode.jpg'}, 'playcount': 0,
        }
        if resume is not None:
            item['resume'] = resume
        original = copy.deepcopy(item)
        events = []
        menus = []
        state = SimpleNamespace(
            section='Shows', mode='home', nav=False, search_state=None,
            episode_browser_context=None, discovery_stack=[],
            getFocusId=lambda: 900, last_row=0, rows=[[item], []],
            histories=[SimpleNamespace(pages=[('original-row', 2)])],
            chosen=lambda cid: item, selected={'file': 'stale-hero'},
            row_states={}, config={'Saved': []}, rating_identity=lambda _: None,
            stop_preview=lambda: events.append('stop-preview'), actions_open=False,
            capture_browse=lambda: {'focus': 900, 'position': 2},
            finish=lambda: events.append('finish'),
            browse_source=lambda: events.append('genre'), setFocusId=lambda cid: None,
        )
        state.update = lambda chosen: setattr(state, 'selected', chosen)
        ns = {'resume_options': resume_options, 'discovery_result': discovery_result,
              'trakt_command': trakt_command, 'choose_player_path': choose_player_path,
              'can_choose_genre': can_choose_genre, 'event': lambda *a, **kw: None}
        click = extract(ROOT / 'live_review.py', 'onClick', ns, 'LiveReview')
        state.onClick = lambda cid: click(state, cid)

        def menu(labels):
            self.assertTrue(state.actions_open)
            menus.append(labels)
            return -1 if cancel else 0

        ns['xbmcgui'] = SimpleNamespace(Dialog=lambda: SimpleNamespace(contextmenu=menu))
        extract(ROOT / 'live_review.py', 'title_actions', ns, 'LiveReview')(state)
        self.assertFalse(state.actions_open)
        self.assertEqual(item, original, 'Opening episode options must not alter artwork or watched/progress data')
        return state, events, menus

    def test_first_action_plays_the_selected_episode_instead_of_the_stale_hero(self):
        state, events, _ = self.run_menu()
        self.assertEqual(getattr(state, 'playback_request', None),
                         'plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=tv&tmdb_id=712&season=1&episode=4')
        self.assertEqual(state.playback_options, {})
        self.assertEqual(state.playback_return, {'focus': 900, 'position': 2})
        self.assertIn('finish', events)

    def test_first_action_retains_the_selected_episodes_existing_resume_handoff(self):
        state, _, _ = self.run_menu({'position': 30, 'total': 100})
        self.assertEqual(getattr(state, 'playback_options', None), {'resume': True})
        self.assertEqual(state.selected['resume'], {'position': 30, 'total': 100})

    def test_cancel_does_not_play_save_sync_or_consume_row_history(self):
        state, events, _ = self.run_menu(cancel=True)
        self.assertFalse(hasattr(state, 'playback_request'))
        self.assertEqual(state.config['Saved'], [])
        self.assertEqual(state.histories[0].pages, [('original-row', 2)])
        self.assertEqual(events, ['stop-preview'])
