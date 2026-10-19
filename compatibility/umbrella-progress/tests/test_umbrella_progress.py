"""Run original Player/Bookmarks AST unchanged at a deterministic Kodi/API boundary.

No Kodi installation, network request, real title history or profile is touched.
Set UMBRELLA_PLAYER to execute a candidate source using this same harness.
"""
import ast
import hashlib
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
import zipfile

HERE = Path(__file__).resolve().parents[1]

class Window:
    def __init__(self): self.values = {}
    def getProperty(self, key): return self.values.get(key, '')
    def setProperty(self, key, value): self.values[key] = value
    def clearProperty(self, key): self.values.pop(key, None)


class NativePlayer:
    def getTime(self):
        if self.timing_lost: raise RuntimeError('Kodi discarded timing after Stop')
        return self.native_time
    def getTotalTime(self):
        if self.timing_lost: raise RuntimeError('Kodi discarded timing after Stop')
        return self.native_total
    def isPlaying(self): return not self.timing_lost
    def isPlayingVideo(self): return not self.timing_lost
    def getPlayingFile(self): return self.native_path
    def seekTime(self, position): self.native_seeks.append(float(position)); self.native_time = float(position)


class NoThread:
    def __init__(self, *args, **kwargs): pass
    def start(self): pass


def source_bytes(version):
    candidate = os.environ.get('UMBRELLA_PLAYER')
    if candidate: return Path(candidate).read_bytes()
    version_number = '6.7.90' if version == 'apple' else '6.7.92'
    directory = 'upstream' if os.environ.get('UMBRELLA_PROGRESS_UPSTREAM') == '1' else 'candidate'
    return (HERE / directory / version_number / 'player.py').read_bytes()


def fixture(version):
    requests, bookmarks, errors, starts = [], [], [], []
    clock = [100.]
    noop = lambda *a, **k: None
    settings = {'scrobble.source': '1', 'markwatched.percent': '85'}
    control = SimpleNamespace(playlist=SimpleNamespace(getposition=lambda: -1, size=lambda: 0, clear=noop), sleep=noop)
    env = {'xbmc': SimpleNamespace(Player=NativePlayer), 'getSetting': lambda key: settings.get(key, 'false'),
           'playerWindow': Window(), 'homeWindow': Window(), 'control': control,
           'clear_local_bookmarks': noop, 'Thread': NoThread,
           'time': SimpleNamespace(time_ns=lambda: 1, monotonic=lambda: clock[0]), '_refresh_after_player_closes': noop,
           'log_utils': SimpleNamespace(log=noop, error=lambda: errors.append('error'), LOGDEBUG=0),
           'fetch_bookmarks': lambda *a: 300. / 6004. * 100,
           'trakt': SimpleNamespace(scrobbleReset=noop, scrobbleStart=lambda **k: starts.append(k), scrobbleMovie=lambda imdb, tmdb, pct: requests.append(pct),
                                    scrobbleEpisode=lambda *args: requests.append(args[-1]))}
    for provider in ('floppy', 'scrob', 'punchplay'):
        env[provider] = SimpleNamespace(scrobbleReset=noop, isReadOnly=lambda: False,
            scrobbleStart=lambda **kwargs: starts.append(kwargs))
    tree = ast.parse(source_bytes(version))
    nodes = [node for node in tree.body if
             isinstance(node, ast.ClassDef) and node.name == 'Player' or
             isinstance(node, ast.FunctionDef) and (node.name == '_remote_playback_enabled' or node.name.startswith('_progress_'))]
    bookmark_class = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'Bookmarks')
    setter = next(node for node in bookmark_class.body if isinstance(node, ast.FunctionDef) and node.name == 'set_scrobble')
    exec(compile(ast.Module(body=nodes + [setter], type_ignores=[]), version, 'exec'), env)
    writer = SimpleNamespace()
    writer.reset = lambda *args, **kwargs: bookmarks.append(args)
    writer.set_scrobble = lambda *a, **k: env['set_scrobble'](writer, *a, **k)
    env['Bookmarks'] = lambda: writer
    player = env['Player'].__new__(env['Player'])
    player.__dict__.update(native_time=28., native_total=6004., timing_lost=False,
        current_time=28., media_length=6004., media_type='movie', title='Deterministic fixture',
        name='Deterministic fixture', year='2020', imdb='tt1234567', tmdb='1', tvdb='', season='', episode='',
        traktCredentials=True, simklCredentials=False, mdblistCredentials=False, customCredentials=False,
        floppyCredentials=False, scrobCredentials=False, punchplayCredentials=False,
        watched_during_playback=False, markwatched_percentage=85, watched_update_thread=None,
        onPlayBackStopped_ran=False, playbackStopped_triggered=False, scrobble_sent=False,
        av_started_ran=False, _playback_path='fixture://resolved-movie',
        native_path='fixture://resolved-movie', native_seeks=[], offset='0', playback_resumed=False,
        custom_rewatch=False, _clock=clock, _starts=starts, _settings=settings, _control=control)
    return player, requests, bookmarks, errors


class OriginalProgressContract(unittest.TestCase):
    def each_version(self): return ('apple', 'fire')

    def test_absolute_seek_then_immediate_stop_closes_at_seek_destination(self):
        for version in self.each_version():
            with self.subTest(version=version):
                p, outgoing, local, errors = fixture(version)
                p.native_time = 750.
                p.onPlayBackSeek(750000, 722000)
                p.timing_lost = True
                p.onPlayBackStopped()
                self.assertEqual(len(outgoing), 1, errors)
                self.assertAlmostEqual(outgoing[-1], 750. / 6004. * 100)
                self.assertEqual(local[-1][0], 750.)

    def test_seek_to_zero_then_stop_does_not_restore_prior_position(self):
        for version in self.each_version():
            with self.subTest(version=version):
                p, outgoing, _, errors = fixture(version)
                p.current_time = 750.
                p.native_time = 0.
                p.onPlayBackSeek(0, -750000)
                p.timing_lost = True
                p.onPlayBackStopped()
                self.assertEqual(len(outgoing), 1, errors)
                self.assertEqual(outgoing[-1], 0.)

    def test_terminal_writer_samples_before_sending_when_timing_still_exists(self):
        for version in self.each_version():
            with self.subTest(version=version):
                p, outgoing, _, errors = fixture(version)
                p.native_time = 750.
                p.onPlayBackStopped()
                self.assertEqual(len(outgoing), 1, errors)
                self.assertAlmostEqual(outgoing[-1], 750. / 6004. * 100)

    def test_percentage_accepts_valid_zero_native_position(self):
        for version in self.each_version():
            with self.subTest(version=version):
                p, _, _, _ = fixture(version)
                p.current_time = 750.
                p.native_time = 0.
                self.assertEqual(p.getWatchedPercent(), 0.)


    def test_callback_position_is_absolute_not_relative_seek_offset(self):
        for version in self.each_version():
            with self.subTest(version=version):
                p, outgoing, _, _ = fixture(version)
                p.onPlayBackSeek(500000, -250000)
                p.timing_lost = True
                p.onPlayBackStopped()
                self.assertAlmostEqual(outgoing[-1], 500. / 6004. * 100)

    def test_seekback_before_native_clock_catches_up_keeps_destination(self):
        for version in self.each_version():
            with self.subTest(version=version):
                p, outgoing, _, _ = fixture(version)
                p.current_time = p.native_time = 750.
                p.onPlayBackSeek(500000, -250000)
                p.getWatchedPercent()
                p.timing_lost = True
                p.onPlayBackStopped()
                self.assertAlmostEqual(outgoing[-1], 500. / 6004. * 100)

    def test_stop_before_av_ready_cannot_reopen_remote_session(self):
        for version in self.each_version():
            with self.subTest(version=version):
                p, outgoing, _, _ = fixture(version)
                p.timing_lost = True
                p.onPlayBackStopped()
                p.timing_lost = False
                p.onAVStarted()
                self.assertTrue(p.scrobble_sent)
                self.assertEqual(p._starts, [])
                self.assertEqual(len(outgoing), 1)

    def test_explicit_seek_before_av_ready_overrides_saved_resume_offset(self):
        for version in self.each_version():
            with self.subTest(version=version):
                p, _, _, _ = fixture(version)
                p.offset = '300'
                p.native_time = 750.
                p.onPlayBackSeek(750000, 722000)
                p.onAVStarted()
                self.assertEqual(p.native_seeks, [])
                self.assertAlmostEqual(p.current_time, 750.)
                self.assertAlmostEqual(p._starts[-1]['watched_percent'], 750. / 6004. * 100, places=2)

    def test_late_seek_callback_cannot_mutate_closed_item(self):
        for version in self.each_version():
            with self.subTest(version=version):
                p, _, _, _ = fixture(version)
                p.timing_lost = True
                p.onPlayBackStopped()
                before = p.current_time
                p.onPlayBackSeek(999000, 971000)
                self.assertEqual(p.current_time, before)

    def test_other_item_seek_callback_does_not_mutate_previous_player(self):
        for version in self.each_version():
            with self.subTest(version=version):
                p, _, _, _ = fixture(version)
                p.native_path = 'fixture://next-movie'
                p.onPlayBackSeek(999000, 971000)
                self.assertEqual(p.current_time, 28.)

    def test_invalid_callback_milliseconds_cannot_poison_cached_progress(self):
        for version in self.each_version():
            for invalid in (float('nan'), float('inf'), -1000, None, 'bad', 999999999999):
                with self.subTest(version=version, invalid=invalid):
                    p, outgoing, _, _ = fixture(version)
                    p.onPlayBackSeek(invalid, 1)
                    p.timing_lost = True
                    p.onPlayBackStopped()
                    self.assertAlmostEqual(outgoing[-1], 28. / 6004. * 100)

    def test_invalid_native_duration_preserves_known_valid_duration(self):
        for version in self.each_version():
            for invalid in (0, float('nan'), float('inf'), -1):
                with self.subTest(version=version, invalid=invalid):
                    p, outgoing, _, _ = fixture(version)
                    p.native_total = invalid
                    p.native_time = 750.
                    p.onPlayBackSeek(750000, 722000)
                    p.timing_lost = True
                    p.onPlayBackStopped()
                    self.assertAlmostEqual(outgoing[-1], 750. / 6004. * 100)


    def test_pending_seek_acknowledges_normal_advance_then_tracks_native_again(self):
        for version in self.each_version():
            with self.subTest(version=version):
                p, _, _, _ = fixture(version)
                p.onPlayBackSeek(750000, 722000)
                self.assertAlmostEqual(p.getWatchedPercent(), 750. / 6004. * 100)
                p._clock[0] += 2.
                p.native_time = 752.
                self.assertAlmostEqual(p.getWatchedPercent(), 752. / 6004. * 100)
                p.native_time = 800.
                self.assertAlmostEqual(p.getWatchedPercent(), 800. / 6004. * 100)

    def test_pause_caches_position_for_stop_after_timing_disappears(self):
        for version in self.each_version():
            with self.subTest(version=version):
                p, outgoing, _, _ = fixture(version)
                p.native_time = 750.
                p.onPlayBackPaused()
                p.timing_lost = True
                p.onPlayBackStopped()
                self.assertAlmostEqual(outgoing[-1], 750. / 6004. * 100)

    def test_resume_at_zero_sends_zero_not_prior_cached_position(self):
        for version in self.each_version():
            with self.subTest(version=version):
                p, _, _, _ = fixture(version)
                p.current_time = 750.
                p.native_time = 0.
                p.onPlayBackResumed()
                self.assertEqual(p._starts[-1]['watched_percent'], 0.)


    def test_seek_during_av_initialization_delay_cannot_be_overwritten_by_saved_offset(self):
        for version in self.each_version():
            with self.subTest(version=version):
                p, _, _, _ = fixture(version)
                p.offset = '300'
                called = []
                def user_seek(milliseconds):
                    if called: return
                    called.append(True)
                    p.native_time = 750.
                    p.onPlayBackSeek(750000, 722000)
                p._control.sleep = user_seek
                p.onAVStarted()
                self.assertEqual(p.native_seeks, [])
                self.assertAlmostEqual(p.current_time, 750.)
                self.assertAlmostEqual(p._starts[-1]['watched_percent'], 750. / 6004. * 100, places=2)

    def test_early_seek_stop_initializes_both_position_and_duration_without_av_callback(self):
        for version in self.each_version():
            with self.subTest(version=version):
                p, outgoing, _, _ = fixture(version)
                p.current_time = p.media_length = 0.
                p.native_time = 750.
                p.onPlayBackSeek(750000, 722000)
                p.timing_lost = True
                p.onPlayBackStopped()
                self.assertAlmostEqual(outgoing[-1], 750. / 6004. * 100)

    def test_paused_pending_seek_does_not_add_paused_wall_clock_to_progress(self):
        for version in self.each_version():
            with self.subTest(version=version):
                p, outgoing, _, _ = fixture(version)
                p.onPlayBackSeek(750000, 722000)
                p.native_time = 750.
                p.onPlayBackPaused()
                p._clock[0] += 600.
                p.timing_lost = True
                p.onPlayBackStopped()
                self.assertAlmostEqual(outgoing[-1], 750. / 6004. * 100)

    def test_invalid_cached_clocks_cannot_reach_remote_payload(self):
        for version in self.each_version():
            for invalid in (float('nan'), float('inf'), -10):
                with self.subTest(version=version, invalid=invalid):
                    p, outgoing, _, _ = fixture(version)
                    p.current_time = p.media_length = invalid
                    p.timing_lost = True
                    p.onPlayBackStopped()
                    self.assertEqual(outgoing, [0.])


    def test_normal_saved_resume_keeps_offset_while_native_seek_ack_is_delayed(self):
        for version in self.each_version():
            with self.subTest(version=version):
                p, _, _, _ = fixture(version)
                p.offset = '300'
                p.seekTime = lambda position: p.native_seeks.append(float(position))
                p.onAVStarted()
                self.assertEqual(p.native_seeks, [300.])
                self.assertAlmostEqual(p._starts[-1]['watched_percent'], 300. / 6004. * 100, places=2)


    def test_seconds_based_providers_start_from_same_explicit_seek_snapshot(self):
        for version in self.each_version():
            for provider, source in (('floppy', '5'), ('scrob', '6'), ('punchplay', '7')):
                for position in (750., 0.):
                    with self.subTest(version=version, provider=provider, position=position):
                        p, _, _, _ = fixture(version)
                        p.traktCredentials = False
                        setattr(p, provider + 'Credentials', True)
                        p._settings['scrobble.source'] = source
                        p.current_time = p.native_time = 28.
                        p.onPlayBackSeek(position * 1000, (position - 28.) * 1000)
                        p.onAVStarted()
                        payload = p._starts[-1]
                        self.assertEqual(payload['current_time'], position)
                        self.assertEqual(payload['total_time'], p.media_length)
                        self.assertAlmostEqual(payload['watched_percent'], position / p.media_length * 100, places=2)

    def test_seconds_based_providers_normal_resume_uses_validated_seconds_snapshot(self):
        for version in self.each_version():
            for provider, source in (('floppy', '5'), ('scrob', '6'), ('punchplay', '7')):
                with self.subTest(version=version, provider=provider):
                    p, _, _, _ = fixture(version)
                    p.traktCredentials = False
                    setattr(p, provider + 'Credentials', True)
                    p._settings['scrobble.source'] = source
                    p.offset = '300'
                    p.onAVStarted()
                    payload = p._starts[-1]
                    self.assertEqual(payload['current_time'], 300.)
                    self.assertEqual(payload['total_time'], p.media_length)
                    self.assertAlmostEqual(payload['watched_percent'], 300. / p.media_length * 100, places=2)

    def test_duplicate_stop_does_not_write_twice(self):
        for version in self.each_version():
            with self.subTest(version=version):
                p, outgoing, _, _ = fixture(version)
                p.timing_lost = True
                p.onPlayBackStopped()
                p.onPlayBackStopped()
                self.assertEqual(len(outgoing), 1)


if __name__ == '__main__':
    for version in ('apple', 'fire'):
        print(version, hashlib.sha256(source_bytes(version)).hexdigest(), flush=True)
    unittest.main(verbosity=2)
