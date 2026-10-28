"""Execute real Helper classes against a deterministic Kodi clock/player boundary."""
import copy
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
import zipfile
from functools import cached_property

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'upstream/helper-6.19.2.zip'
CANDIDATE = ROOT / 'patched/plugin.video.themoviedb.helper/resources/tmdbhelper/lib/monitor'
PREFIX = 'plugin.video.themoviedb.helper/resources/tmdbhelper/lib/monitor/'


class NativePlayer:
    def __init__(self):
        self.position = 28.0
        self.duration = 6004.0
        self.playing = True
        self.time_error = False
        self.time_reads = []
        self.native_reads = 0

    def isPlayingVideo(self):
        self.native_reads += 1
        return self.playing

    def getTime(self):
        self.native_reads += 1
        self.time_reads.append(self.clock[0])
        if self.time_error:
            raise RuntimeError('Kodi has discarded player timing')
        return self.position

    def getTotalTime(self):
        self.native_reads += 1
        return self.duration


class CommonMonitor:
    def __init__(self):
        pass

    def clear_properties(self):
        pass

    def clear_property(self, *args):
        pass


class ProgressTests(unittest.TestCase):
    def setUp(self):
        self.clock = [100000.0]
        self.requests = []
        self.waits = []
        self.abort_at = None
        self.on_wait = lambda seconds: None
        modules = {}

        def module(name, **attrs):
            result = types.ModuleType(name)
            result.__dict__.update(attrs)
            modules[name] = result
            return result

        native_monitor = type('NativeMonitor', (), {
            'waitForAbort': lambda monitor, seconds: self.wait(seconds),
            'abortRequested': lambda monitor: False})
        module('xbmc', Player=NativePlayer, Monitor=native_monitor)
        module('jurialmunkey.ftools', cached_property=cached_property)
        module('jurialmunkey.window', get_property=lambda *a, **k: 1,
               wait_for_property=lambda *a, **k: None, WindowChecker=type('WindowChecker', (), {}))
        module('jurialmunkey.parser', try_int=int)
        module('tmdbhelper.lib.addon.plugin',
               get_setting=lambda name, *a, **k: name == 'trakt_scrobbling',
               get_condvisibility=lambda *a: False, get_infolabel=lambda *a: '')
        module('tmdbhelper.lib.addon.logger', kodi_log=lambda *a, **k: None)
        module('tmdbhelper.lib.addon.tmdate', set_timestamp=lambda offset=0: self.clock[0] + offset)
        module('tmdbhelper.lib.player.action.playerstring',
               read_playerstring=lambda: {'tmdb_type': 'movie', 'tmdb_id': '445571'})
        module('tmdbhelper.lib.monitor.images', ImageFunctions=object)
        module('tmdbhelper.lib.monitor.common', CommonMonitorFunctions=CommonMonitor)
        module('tmdbhelper.lib.monitor.listitemtools', ListItemMonitorFunctions=object)
        module('tmdbhelper.lib.monitor.cronjob', CronJobMonitor=object)
        module('tmdbhelper.lib.monitor.update', UpdateMonitor=object)
        module('tmdbhelper.lib.monitor.imgmon', ImagesMonitor=object)
        module('tmdbhelper.lib.addon.thread', SafeThread=object)
        module('tmdbhelper.lib.script.method.trakt', get_stats=lambda: None)
        module('tmdbhelper.lib.addon.consts', LASTACTIVITIES_DATA='activities')
        module('tmdbhelper.lib.monitor.playback_refresh', PlaybackRefreshFactory=lambda *a: types.SimpleNamespace(refresh=lambda *a, **k: None))
        module('tmdbhelper.lib.sync.invalidator', SyncInvalidator=lambda *a:
               types.SimpleNamespace(notification=True, run=lambda **k: None))
        self.module_patch = patch.dict(sys.modules, modules)
        self.module_patch.start()
        self.addCleanup(self.module_patch.stop)

        def load(name, filename, upstream=False):
            path = CANDIDATE / filename
            if upstream or not path.exists() or os.environ.get('HELPER_PROGRESS_UPSTREAM') == '1':
                with zipfile.ZipFile(BASE) as z:
                    source = z.read(PREFIX + filename)
            else:
                source = path.read_bytes()
            result = types.ModuleType(name)
            result.__file__ = str(path)
            sys.modules[name] = result
            self.addCleanup(sys.modules.pop, name, None)
            exec(compile(source, str(path), 'exec'), result.__dict__)
            return result

        self.scrobbler_module = load('tmdbhelper.lib.monitor.scrobbler', 'scrobbler.py')
        self.player_module = load('tmdbhelper.lib.monitor.player', 'player.py')
        load('tmdbhelper.lib.monitor.poller', 'poller.py', upstream=True)
        self.service_module = load('tmdbhelper.lib.monitor.service', 'service.py')
        self.service_module.monotonic = lambda: self.clock[0]
        self.player = self.player_module.PlayerMonitor()
        self.player.clock = self.clock
        self.player.__dict__['player_item'] = types.SimpleNamespace(tmdb_type='movie', tmdb_id='445571')

        def request(path, **kwargs):
            self.requests.append((path, copy.deepcopy(kwargs['postdata'])))
            return {'action': path.rsplit('/', 1)[-1]}

        self.request_success=True
        def make_request(scrobbler, provider):
            def send(method):
                request('https://api.trakt.tv/scrobble/'+method,postdata={'progress':scrobbler.progress})
                return types.SimpleNamespace(successful=self.request_success,history_changed=False)
            return types.SimpleNamespace(scrobble=send)
        self.provider=types.SimpleNamespace(is_authorized=lambda:self.scrobbler_module.get_setting('trakt_scrobbling'),scrobbler_class=make_request)
        self.syncdata=types.SimpleNamespace()
        self.scrobbler = self.scrobbler_module.PlayerScrobbler(6004, self.provider, self.syncdata)
        self.player.scrobbler = self.scrobbler
        self.player.scrobbler_start()
        self.player.time_reads.clear()
        self.player.native_reads = 0
        self.service = self.service_module.ServiceMonitor()
        self.service.player_monitor = self.player
        self.service.update_monitor = types.SimpleNamespace(waitForAbort=self.wait)

    def wait(self, seconds):
        self.waits.append(seconds)
        self.clock[0] += seconds
        self.on_wait(seconds)
        return self.abort_at is not None and self.clock[0] >= self.abort_at

    def test_missed_seek_is_sampled_in_idle_then_stop_uses_last_position(self):
        self.player.position = 602
        self.service._on_idle(1)
        self.clock[0] += 116
        self.player.position = 718
        self.service._on_idle(1)
        self.player.playing = False
        self.player.onPlayBackStopped()
        self.assertAlmostEqual(self.requests[-1][1]['progress'], 11.95869420386409)
        self.assertEqual(self.requests[-1][0], 'https://api.trakt.tv/scrobble/stop')

    def test_pause_and_api_delay_do_not_advance_position(self):
        self.player.position = 718
        self.player.scrobbler_pause()
        self.clock[0] += 600
        self.assertEqual(self.scrobbler.current_time, 718)
        self.assertAlmostEqual(self.scrobbler.progress, 11.95869420386409)

    def test_timing_race_retains_last_sample_without_escaping(self):
        self.player.time_error = True
        self.player.scrobbler_update()
        self.assertEqual(self.scrobbler.current_time, 28)
        self.player.playing = False
        self.clock[0] += 60
        self.player.scrobbler_stop()
        self.assertAlmostEqual(self.requests[-1][1]['progress'], 0.46635576282478347)

    def test_idle_sampling_is_capped_across_short_waits_without_network(self):
        for _ in range(20):
            self.service._on_idle(0.2)
        self.assertGreaterEqual(len(self.player.time_reads), 3)
        self.assertLessEqual(len(self.player.time_reads), 5)
        self.assertTrue(all(b - a >= 1 for a, b in zip(self.player.time_reads, self.player.time_reads[1:])))
        self.assertEqual(len(self.requests), 1)

    def test_live_wait_is_abort_responsive_with_one_second_maximum(self):
        self.abort_at = self.clock[0] + 1
        self.service._on_idle(30)
        self.assertEqual(self.waits, [1])
        self.assertEqual(self.clock[0], 100001)

    def test_browsing_without_live_scrobbler_preserves_exact_idle_wait(self):
        self.player.scrobbler = None
        self.service_module.monotonic = lambda: self.fail('Nonplayback browsing read the sampling clock')
        self.service._on_idle(5)
        self.assertEqual(self.waits, [5])
        self.assertEqual(self.player.native_reads, 0)
        self.assertEqual(len(self.requests), 1)

    def test_stopped_scrobbler_preserves_exact_idle_wait(self):
        self.scrobbler.stopped = True
        self.service._on_idle(5)
        self.assertEqual(self.waits, [5])
        self.assertEqual(self.player.native_reads, 0)

    def test_identity_gate_retains_previous_position(self):
        self.scrobbler.update_time('movie', 'wrong-id', 718)
        self.assertEqual(self.scrobbler.current_time, 28)

    def test_invalid_samples_do_not_replace_last_valid_position(self):
        for value in (-1, float('nan'), float('inf'), float('-inf'), None, '718', True, 6005):
            with self.subTest(value=value):
                self.scrobbler.update_time('movie', '445571', value)
                self.assertEqual(self.scrobbler.current_time, 28)

    def test_scrobbler_replacement_during_callback_keeps_original_session(self):
        def stopped_during_read():
            self.player.scrobbler = None
            return 718
        self.player.getTime = stopped_during_read
        for method in ('scrobbler_start', 'scrobbler_pause', 'scrobbler_stop'):
            with self.subTest(method=method):
                self.player.scrobbler = self.scrobbler
                getattr(self.player, method)()
                self.assertEqual(self.scrobbler.current_time, 718)
        self.assertTrue(self.scrobbler.stopped)
        self.assertAlmostEqual(self.requests[-1][1]['progress'], 11.95869420386409)

    def test_existing_eighty_percent_sync_threshold_and_single_send_are_retained(self):
        self.scrobbler.update_time('movie', '445571', 4803)
        self.scrobbler.sync('movie', '445571')
        self.assertEqual(len(self.requests), 1)
        self.scrobbler.update_time('movie', '445571', 4804)
        self.scrobbler.sync('movie', '445571')
        self.scrobbler.sync('movie', '445571')
        self.assertEqual(len(self.requests), 2)
        self.assertAlmostEqual(self.requests[-1][1]['progress'], 80.01332445036642)

    def test_disabled_trakt_authority_still_blocks_network(self):
        self.scrobbler_module.get_setting = lambda *a, **k: False
        self.scrobbler.update_time('movie', '445571', 718)
        self.scrobbler.scrobble('stop')
        self.assertEqual(len(self.requests), 1)

    def test_fullscreen_timing_race_keeps_service_alive(self):
        self.player.time_error = True
        self.player.on_fullscreen()
        self.assertEqual(self.scrobbler.current_time, 28)
        self.assertEqual(len(self.requests), 1)

    def test_idle_sampling_stops_when_session_disappears(self):
        self.on_wait = lambda seconds: setattr(self.player, 'scrobbler', None)
        self.service._on_idle(5)
        self.assertEqual(self.waits, [1, 4])
        self.assertEqual(len(self.player.time_reads), 1)

    def test_live_replacement_during_idle_keeps_sampling_at_global_deadline(self):
        replacement = self.scrobbler_module.PlayerScrobbler(6004, self.provider, self.syncdata)
        def replace_after_first_wait(seconds):
            if self.player.scrobbler is self.scrobbler:
                self.scrobbler.stopped = True
                self.player.scrobbler = replacement
                self.player.position = 718
        self.on_wait = replace_after_first_wait
        self.service._on_idle(5)
        self.assertEqual(replacement.current_time, 718)
        self.assertEqual(self.waits, [1, 1, 1, 1, 1])
        self.assertGreaterEqual(len(self.player.time_reads), 5)
        self.assertTrue(all(b - a >= 1 for a, b in zip(self.player.time_reads, self.player.time_reads[1:])))
        self.assertEqual(len(self.requests), 1)

    def test_fullscreen_session_replacement_does_not_lose_original_sync(self):
        self.scrobbler.update_time('movie', '445571', 5000)
        def replaced_during_read():
            self.player.scrobbler = None
            return 5000
        self.player.getTime = replaced_during_read
        self.player.on_fullscreen()
        self.assertTrue(self.scrobbler.syncing)
        self.assertAlmostEqual(self.requests[-1][1]['progress'], 83.2778147901399)

    def test_seek_then_stop_during_callback_wait_retains_callback_position(self):
        def stop_during_seek_wait(seconds):
            self.player.playing = False
            self.player.onPlayBackStopped()
        self.on_wait = stop_during_seek_wait
        self.player.onPlayBackSeek(600435, 521526)
        self.assertTrue(self.scrobbler.stopped)
        self.assertAlmostEqual(self.requests[-1][1]['progress'], 10.00058294470353)
        self.assertEqual(len(self.requests), 2)
        self.assertEqual(self.player.time_reads, [])

    def test_paused_then_stop_without_resume_does_not_include_pause_duration(self):
        self.player.position = 718
        self.player.onPlayBackPaused()
        self.clock[0] += 600
        self.player.playing = False
        self.player.onPlayBackStopped()
        self.assertAlmostEqual(self.requests[-1][1]['progress'], 11.95869420386409)

    def test_seek_wait_does_not_start_replacement_session(self):
        replacement = self.scrobbler_module.PlayerScrobbler(6004, self.provider, self.syncdata)
        self.on_wait = lambda seconds: setattr(self.player, 'scrobbler', replacement)
        self.player.onPlayBackSeek(600435, 521526)
        self.assertFalse(replacement.started)
        self.assertEqual(len(self.requests), 1)

    def legacy_factory(self, explicit='', disabled=False):
        values={'sync_provider_scrobbling':explicit,'trakt_scrobbling':True,'mdblist_scrobbling':not disabled,'trakt_token':'synthetic','mdblist_apikey':'synthetic'}
        calls=[]
        def provider(name):
            def make(player, owner):
                def send(method):calls.append((name,method,player.progress));return types.SimpleNamespace(successful=True,history_changed=False)
                return types.SimpleNamespace(scrobble=send)
            return types.SimpleNamespace(provider_id=name,capabilities=('scrobbling',),is_authorized=lambda:True,scrobbler_class=make)
        providers={name:provider(name) for name in ('trakt','mdblist')}
        registry=types.SimpleNamespace(providers=providers,get_selected_provider=lambda role:providers.get(explicit or 'trakt'))
        module=types.SimpleNamespace(SyncDataFactory=lambda:types.SimpleNamespace(registry=registry))
        with patch.dict(sys.modules,{'tmdbhelper.lib.sync.datasync':module}),patch.object(self.scrobbler_module,'get_setting',side_effect=lambda key,*a:values.get(key,'')):
            value=self.scrobbler_module.PlayerScrobblerFactory(6004)
        return value,calls

    def test_legacy_dual_authorizations_keep_both_progress_writes(self):
        value,calls=self.legacy_factory()
        value.start('movie','445571');value.update_time('movie','445571',718);value.pause('movie','445571');value.stop('movie','445571')
        self.assertEqual({name for name,method,progress in calls if method=='stop'},{'trakt','mdblist'})
        self.assertTrue(all(abs(progress-718/6004*100)<.001 for name,method,progress in calls if method=='stop'))
        self.assertTrue(value.stopped)

    def test_explicit_new_single_provider_does_not_enable_legacy_secondary(self):
        value,calls=self.legacy_factory(explicit='trakt');value.start('movie','445571');value.update_time('movie','445571',718);value.stop('movie','445571')
        self.assertEqual({name for name,method,progress in calls},{'trakt'})

    def test_disabled_legacy_secondary_stays_disabled(self):
        value,calls=self.legacy_factory(disabled=True);value.start('movie','445571');value.update_time('movie','445571',718);value.stop('movie','445571')
        self.assertEqual({name for name,method,progress in calls},{'trakt'})

    def test_new_provider_factory_retains_selected_provider(self):
        selected=[]
        registry=types.SimpleNamespace(get_selected_provider=lambda role:selected.append(role) or self.provider)
        module=types.ModuleType('tmdbhelper.lib.sync.datasync');module.SyncDataFactory=lambda:types.SimpleNamespace(registry=registry)
        with patch.dict(sys.modules,{'tmdbhelper.lib.sync.datasync':module}):
            value=self.scrobbler_module.PlayerScrobblerFactory(6004)
        self.assertIs(value.provider,self.provider)
        self.assertEqual(selected,['scrobbling'])

    def test_unsuccessful_completion_can_retry_under_new_provider_contract(self):
        self.request_success=False
        self.scrobbler.update_time('movie','445571',5000)
        self.scrobbler.sync('movie','445571')
        self.assertFalse(self.scrobbler.syncing)
        self.request_success=True
        self.scrobbler.sync('movie','445571')
        self.assertTrue(self.scrobbler.syncing)

if __name__ == '__main__':
    unittest.main()
