"""Native playlist callbacks must belong to the item this Player acquired."""
import importlib.util
import sys
from types import ModuleType, SimpleNamespace
from pathlib import Path
from unittest.mock import patch
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('lifecycle_progress_fixture', ROOT.parent/'umbrella-progress/tests/test_umbrella_progress.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)

class PlaylistLifecycle(unittest.TestCase):
    def player(self):
        with patch.object(base, 'source_bytes', lambda _: (ROOT/'candidate/resources/lib/modules/player.py').read_bytes()):
            p, outgoing, bookmarks, errors = base.fixture('fire')
        database = ModuleType('resources.lib.database')
        database.traktsync = SimpleNamespace(delete_bookmark=lambda _: None)
        modules = ModuleType('resources.lib.modules')
        modules.tools = SimpleNamespace(delete_all_subs=lambda: None)
        boundary = patch.dict(sys.modules, {'resources.lib.database': database, 'resources.lib.modules': modules})
        boundary.start()
        self.addCleanup(boundary.stop)
        p.libForPlayback = lambda: None
        p.onPlayBackEnded.__globals__['log_utils'].error = lambda: errors.append(repr(sys.exc_info()[1]))
        return p, outgoing, bookmarks, errors

    def test_previous_eof_before_new_item_av_started_cannot_close_new_tracking(self):
        p, outgoing, bookmarks, errors = self.player()
        p._playback_path = None
        p.current_time = 0
        p.timing_lost = True
        p.onPlayBackEnded()
        self.assertFalse(p.scrobble_sent, 'Previous item EOF retired the next item before AVStarted')
        self.assertEqual(bookmarks, [])
        self.assertEqual(outgoing, [])
        self.assertEqual(errors, [])

    def test_new_item_starts_remote_progress_after_ignoring_outgoing_eof(self):
        p, outgoing, bookmarks, errors = self.player()
        p._playback_path = None
        p.timing_lost = True
        p.onPlayBackEnded()
        p.timing_lost = False
        p.onAVStarted()
        self.assertFalse(p.scrobble_sent)
        self.assertEqual(p._playback_path, p.native_path)
        self.assertEqual(len(p._starts), 1)
        self.assertEqual(outgoing, [])
        self.assertEqual(bookmarks, [])
        self.assertEqual(errors, [])

    def test_explicit_stop_of_acquired_next_item_clears_override_and_saves_progress(self):
        p, outgoing, bookmarks, errors = self.player()
        window = p.onPlayBackStopped.__globals__['playerWindow']
        keys = ['BlackLanturn.SourceSession.v1', 'umbrella.preResolved_sourceSession', 'umbrella.preResolved_nextUrl']
        for key in keys: window.setProperty(key, 'test')
        p.av_started_ran = True
        p.current_time = 70
        p.media_length = 438
        p.timing_lost = True
        p.onPlayBackStopped()
        self.assertTrue(p.scrobble_sent)
        self.assertTrue(p.onPlayBackStopped_ran)
        self.assertTrue(all(not window.getProperty(key) for key in keys))
        self.assertEqual(len(outgoing), 1)
        self.assertAlmostEqual(outgoing[0], 70 / 438 * 100)
        self.assertEqual(errors, [])

    def test_previous_eof_after_new_item_av_started_keeps_current_tracking_open(self):
        p, outgoing, bookmarks, errors = self.player()
        p.av_started_ran = True
        p.onPlayBackEnded()
        self.assertFalse(p.scrobble_sent)
        self.assertEqual(bookmarks, [])
        self.assertEqual(outgoing, [])
        self.assertEqual(errors, [])

    def test_real_failed_start_stop_still_retires_an_unacquired_configured_player(self):
        p, outgoing, bookmarks, errors = self.player()
        p._playback_path = None
        p.current_time = 0
        p.media_length = 0
        p.timing_lost = True
        window = p.onPlayBackStopped.__globals__['playerWindow']
        window.setProperty('BlackLanturn.SourceSession.v1', 'cancelled-choice')
        p.onPlayBackStopped()
        self.assertTrue(p.scrobble_sent)
        self.assertTrue(p.onPlayBackStopped_ran)
        self.assertEqual(window.getProperty('BlackLanturn.SourceSession.v1'), '')
        self.assertEqual(outgoing, [0.])
        self.assertEqual(errors, [])

    def test_retired_player_stop_cannot_clear_new_items_runtime_choice(self):
        p, outgoing, bookmarks, errors = self.player()
        p.scrobble_sent = True
        p.onPlayBackStopped_ran = True
        p.native_path = 'fixture://next-episode'
        window = p.onPlayBackStopped.__globals__['playerWindow']
        keys = ['BlackLanturn.SourceSession.v1', 'umbrella.preResolved_sourceSession', 'umbrella.preResolved_nextUrl']
        for key in keys: window.setProperty(key, 'next-item-choice')
        p.onPlayBackStopped()
        self.assertTrue(all(window.getProperty(key) == 'next-item-choice' for key in keys))
        self.assertEqual(outgoing, [])
        self.assertEqual(bookmarks, [])
        self.assertEqual(errors, [])

    def test_delayed_outgoing_stop_saves_its_cached_progress_without_clearing_next_choice(self):
        p, outgoing, bookmarks, errors = self.player()
        p.current_time = 750
        p.native_time = 12
        p.native_path = 'fixture://next-episode'
        window = p.onPlayBackStopped.__globals__['playerWindow']
        window.setProperty('BlackLanturn.SourceSession.v1', 'next-item-choice')
        p.onPlayBackStopped()
        p.onPlayBackStopped()
        self.assertEqual(len(outgoing), 1)
        self.assertAlmostEqual(outgoing[0], 750 / 6004 * 100)
        self.assertEqual(p.current_time, 750)
        self.assertTrue(p.scrobble_sent)
        self.assertEqual(window.getProperty('BlackLanturn.SourceSession.v1'), 'next-item-choice')
        self.assertEqual(errors, [])

    def test_eof_after_playlist_cursor_advanced_preserves_queued_next_policy(self):
        p, outgoing, bookmarks, errors = self.player()
        p._playback_playlist_position = 0
        p._control.playlist.getposition = lambda: 1
        p._control.playlist.size = lambda: 2
        p.current_time = p.media_length
        p.timing_lost = True
        window = p.onPlayBackEnded.__globals__['playerWindow']
        window.setProperty('BlackLanturn.SourceSession.v1', 'queued-next-policy')
        p.onPlayBackEnded()
        self.assertEqual(window.getProperty('BlackLanturn.SourceSession.v1'), 'queued-next-policy')
        self.assertEqual(outgoing, [100.])
        self.assertEqual(errors, [])

    def test_fallback_stop_after_cursor_advanced_does_not_erase_queued_next_policy(self):
        p, outgoing, bookmarks, errors = self.player()
        p._playback_playlist_position = 0
        p._control.playlist.getposition = lambda: 1
        p._control.playlist.size = lambda: 2
        p.current_time = p.media_length
        p.timing_lost = True
        window = p.onPlayBackStopped.__globals__['playerWindow']
        window.setProperty('BlackLanturn.SourceSession.v1', 'queued-next-policy')
        p.onPlayBackStopped()
        self.assertEqual(window.getProperty('BlackLanturn.SourceSession.v1'), 'queued-next-policy')
        self.assertTrue(p.scrobble_sent)
        self.assertEqual(errors, [])

    def test_explicit_stop_at_own_cursor_still_clears_policy_with_future_item_queued(self):
        p, outgoing, bookmarks, errors = self.player()
        p._playback_playlist_position = 0
        p._control.playlist.getposition = lambda: 0
        p._control.playlist.size = lambda: 2
        p.timing_lost = True
        window = p.onPlayBackStopped.__globals__['playerWindow']
        window.setProperty('BlackLanturn.SourceSession.v1', 'stop-this-viewing-session')
        p.onPlayBackStopped()
        self.assertEqual(window.getProperty('BlackLanturn.SourceSession.v1'), '')
        self.assertTrue(p.scrobble_sent)
        self.assertEqual(errors, [])

    def test_last_item_eof_clears_policy_after_native_cursor_becomes_unavailable(self):
        p, outgoing, bookmarks, errors = self.player()
        p._playback_playlist_position = 1
        p._control.playlist.getposition = lambda: -1
        p._control.playlist.size = lambda: 2
        p.timing_lost = True
        p.current_time = p.media_length
        window = p.onPlayBackEnded.__globals__['playerWindow']
        window.setProperty('BlackLanturn.SourceSession.v1', 'finished-session')
        p.onPlayBackEnded()
        self.assertEqual(window.getProperty('BlackLanturn.SourceSession.v1'), '')
        self.assertTrue(p.scrobble_sent)
        self.assertEqual(errors, [])

    def test_current_item_eof_still_closes_tracking_once_video_has_ended(self):
        p, outgoing, bookmarks, errors = self.player()
        p.current_time = p.media_length
        p.timing_lost = True
        p.onPlayBackEnded()
        self.assertTrue(p.scrobble_sent)
        self.assertEqual(len(bookmarks), 1)
        self.assertEqual(outgoing, [100.])
        self.assertEqual(errors, [])

if __name__ == '__main__': unittest.main()
