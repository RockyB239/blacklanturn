"""Actual play_source and callback-after-teardown duration-gap regression."""
import importlib.util
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parents[1]/'compatibility/umbrella-progress'
SPEC=importlib.util.spec_from_file_location('duration_zero_contract',HERE/'tests/test_zero_resume.py')
ZERO=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(ZERO)

def source(version):
    number='6.7.90' if version=='apple' else '6.7.92'
    directory='zero-candidate' if os.environ.get('UMBRELLA_DURATION_UPSTREAM')=='1' else 'duration-candidate'
    path=HERE/directory/number/'player.py'
    if not path.exists():path=HERE/'zero-candidate'/number/'player.py'
    return path.read_bytes()

def fixture(version,metadata=None,on_resolve=None):
    with patch.object(ZERO,'source',source):p,outgoing,env=ZERO.fixture(version)
    p.current_time=p.media_length=0.;p.debuglog=False;p.enable_playnext=False
    p._playback_path=None;p._resolved=[];p._cancelled=[]
    p.keepAlive=lambda:None;p.checkPlaylist=lambda item:False
    env['fetch_metacache']=lambda items,*a:items
    env['jsdumps']=json.dumps;env['jsloads']=json.loads
    control=env['control'];control.apiLanguage=lambda:{'tvdb':'en'}
    control.infoLabel=lambda key:'';control.addonThumb=lambda:'fixture-thumb'
    control.jsonrpc=lambda raw:json.dumps({'result':{'movies':[{'uniqueid':{'imdb':'tt1234567'},'movieid':1}]}})
    control.item=lambda **kw:SimpleNamespace(setArt=lambda *a:None,setProperty=lambda *a:None)
    control.set_info=lambda *a,**kw:None;control.cancelPlayback=lambda:p._cancelled.append(True)
    def resolve(*args):
        p._resolved.append({'media_length':p.media_length,'fallback':getattr(p,'_progress_length_fallback',False)})
        if on_resolve:on_resolve(p)
    control.resolve=resolve
    writer=env['Bookmarks']();writer.get=lambda **kw:'0';writer.custom_rewatch=False
    return p,outgoing,env

def play(p,metadata):
    # Run unchanged production play_source/getMeta; only Kodi, persistence and
    # network boundaries are substituted. The resolve boundary sees seed state.
    with patch.object(sys,'argv',['plugin://fixture','1','']):
        p.play_source('Fixture','2018',None,None,'tt1234567','1','',
                      'fixture://resolved-movie',metadata)

class DurationGapTests(unittest.TestCase):
    def test_actual_play_source_seeds_seconds_before_delayed_seek_and_stop_callbacks(self):
        for version in ('apple','fire'):
            with self.subTest(version=version):
                def late_callbacks(p):
                    p.timing_lost=True
                    p.onPlayBackSeek(750000,750000)
                    p.onPlayBackStopped()
                p,outgoing,_=fixture(version,on_resolve=late_callbacks)
                play(p,{'title':'Fixture','duration':6000})
                self.assertEqual(len(p._resolved),1,p._cancelled)
                self.assertEqual(p._resolved[0],{'media_length':6000.,'fallback':True})
                self.assertAlmostEqual(outgoing[-1],12.5)
                self.assertEqual(p.current_time,750.)
                self.assertFalse(p.av_started_ran)

    def test_invalid_missing_and_boolean_metadata_never_invent_duration(self):
        for version in ('apple','fire'):
            for value in (None,'bad',0,-1,float('nan'),float('inf'),True,False):
                with self.subTest(version=version,value=value):
                    p,_,_=fixture(version);play(p,{'title':'Fixture','duration':value})
                    self.assertEqual(len(p._resolved),1,p._cancelled)
                    self.assertEqual(p._resolved[0]['media_length'],0.)
            p,_,_=fixture(version);play(p,{'title':'Fixture','runtime':100})
            self.assertEqual(p._resolved[0]['media_length'],0.)

    def test_duration_units_are_seconds_without_minute_guessing(self):
        for version in ('apple','fire'):
            with self.subTest(version=version):
                p,_,_=fixture(version);play(p,{'title':'Fixture','duration':'100'})
                self.assertEqual(p._resolved[0]['media_length'],100.)

    def test_first_native_duration_replaces_fallback_in_both_directions(self):
        for version in ('apple','fire'):
            for native in (5900.,6003.648):
                with self.subTest(version=version,native=native):
                    p,_,_=fixture(version);play(p,{'title':'Fixture','duration':6000})
                    p.native_total=native;p.native_time=750.;p.getWatchedPercent()
                    self.assertEqual(p.media_length,native)
                    self.assertFalse(getattr(p,'_progress_length_fallback',True))

    def test_seek_callback_native_duration_also_replaces_larger_metadata_fallback(self):
        for version in ('apple','fire'):
            with self.subTest(version=version):
                p,_,_=fixture(version);play(p,{'title':'Fixture','duration':7000})
                p.native_total=6003.648;p.onPlayBackSeek(750000,722000)
                self.assertEqual(p.media_length,6003.648)
                self.assertFalse(getattr(p,'_progress_length_fallback',True))

    def test_invalid_native_duration_keeps_current_item_fallback(self):
        for version in ('apple','fire'):
            for native in (0.,-1.,float('nan'),float('inf')):
                with self.subTest(version=version,native=native):
                    p,_,_=fixture(version);play(p,{'title':'Fixture','duration':6000})
                    p.native_total=native;p.getWatchedPercent()
                    self.assertEqual(p.media_length,6000.)
                    self.assertTrue(getattr(p,'_progress_length_fallback',False))

    def test_subsequent_native_duration_retains_existing_maximum_policy(self):
        for version in ('apple','fire'):
            with self.subTest(version=version):
                p,_,_=fixture(version);play(p,{'title':'Fixture','duration':7000})
                p.native_total=6003.648;p.getWatchedPercent()
                p.native_total=5900.;p.getWatchedPercent()
                self.assertEqual(p.media_length,6003.648)

    def test_other_item_or_closed_callback_cannot_replace_fallback_duration(self):
        for version in ('apple','fire'):
            for mode in ('other_item','closed'):
                with self.subTest(version=version,mode=mode):
                    p,_,_=fixture(version);play(p,{'title':'Fixture','duration':6000})
                    p._playback_path='fixture://resolved-movie';p.native_total=7000.
                    if mode=='other_item':p.native_path='fixture://next-movie'
                    else:p.scrobble_sent=True
                    p.onPlayBackSeek(750000,722000);p.getWatchedPercent()
                    self.assertEqual(p.media_length,6000.)
                    self.assertTrue(getattr(p,'_progress_length_fallback',False))

    def test_metadata_fallback_allows_delayed_explicit_zero_to_clear_old_resume(self):
        for version in ('apple','fire'):
            with self.subTest(version=version):
                def late_zero(p):
                    p.timing_lost=True;p.onPlayBackSeek(0,-750000);p.onPlayBackStopped()
                p,outgoing,_=fixture(version,on_resolve=late_zero)
                play(p,{'title':'Fixture','duration':6000})
                self.assertEqual(outgoing,[])
                self.assertEqual([x[0]for x in p._events],['sync','reset'])

class ContradictedFallbackTests(unittest.TestCase):
    def prepared(self,version,zero_first=False):
        p,outgoing,env=fixture(version);play(p,{'title':'Fixture','duration':6000})
        p.timing_lost=True
        if zero_first:p.onPlayBackSeek(0,-750000)
        p.onPlayBackSeek(6002000,6002000)
        return p,outgoing,env

    def test_positive_over_approximate_fallback_revokes_zero_without_inventing_duration(self):
        for version in ('apple','fire'):
            for zero_first in (False,True):
                with self.subTest(version=version,zero_first=zero_first):
                    p,outgoing,env=self.prepared(version,zero_first)
                    self.assertEqual(p.current_time,6002.)
                    self.assertEqual(p._progress_seek_target,6002.)
                    self.assertEqual(p.media_length,0.)
                    self.assertEqual(p.getWatchedPercent(),0.)
                    p.onPlayBackStopped();p.onPlayBackStopped()
                    self.assertEqual(p._events,[])
                    self.assertEqual(outgoing,[])
                    self.assertEqual(p._reset_options,[])
                    self.assertFalse(p.watched_during_playback)
                    self.assertTrue(p.scrobble_sent)

    def test_all_provider_terminal_writes_are_withheld_for_contradicted_denominator(self):
        for version in ('apple','fire'):
            for name,credential,provider_id in (('trakt','trakt','1'),('simkl','simkl','2'),('mdblist','mdblist','3'),('customtrakt','custom','4'),('floppy','floppy','5'),('scrob','scrob','6'),('punchplay','punchplay','7')):
                with self.subTest(version=version,provider=name):
                    p,outgoing,env=self.prepared(version,True)
                    p.traktCredentials=False;setattr(p,credential+'Credentials',True)
                    p._settings['scrobble.source']=provider_id;written=[]
                    def record(*a,**kw):written.append((a,kw))
                    env[name]=SimpleNamespace(isReadOnly=lambda:False,scrobbleMovie=record,
                        scrobbleStopMovie=record,scrobbleReset=record,sync_playbackProgress=record)
                    p.onPlayBackStopped()
                    self.assertEqual(written,[])
                    self.assertEqual(p._reset_options,[])
                    self.assertFalse(p.watched_during_playback)

    def test_unknown_fallback_suppresses_start_pause_resume_end_and_error_writes(self):
        for version in ('apple','fire'):
            for callback in ('onAVStarted','onPlayBackPaused','onPlayBackResumed','onPlayBackEnded','onPlayBackError'):
                with self.subTest(version=version,callback=callback):
                    p,outgoing,env=self.prepared(version,True)
                    # Enable every service so no alternate start/reset route is hidden.
                    calls=[]
                    for name,credential in (('trakt','trakt'),('simkl','simkl'),('mdblist','mdblist'),('customtrakt','custom'),('floppy','floppy'),('scrob','scrob'),('punchplay','punchplay')):
                        setattr(p,credential+'Credentials',True)
                        p._settings[credential+'.markwatched']='true'
                        def record(*a,**kw):calls.append((a,kw))
                        env[name]=SimpleNamespace(isReadOnly=lambda:False,scrobbleMovie=record,
                            scrobbleStopMovie=record,scrobbleStart=record,scrobbleReset=record,
                            sync_playbackProgress=record)
                    # The file can be active while native duration is still unknown.
                    p.timing_lost=False;p.native_total=0.;p.native_time=6002.
                    if callback=='onPlayBackEnded':p.timing_lost=True
                    getattr(p,callback)()
                    self.assertEqual(outgoing,[])
                    self.assertEqual(p._events,[])
                    self.assertEqual(p._starts,[])
                    self.assertEqual(calls,[])
                    self.assertEqual(p._reset_options,[])
                    self.assertFalse(p.watched_during_playback)

    def test_existing_keepalive_cycle_withholds_seconds_heartbeats_until_native_duration(self):
        for version in ('apple','fire'):
            for recover in (False,True):
                with self.subTest(version=version,recover=recover):
                    p,_,env=self.prepared(version)
                    p.timing_lost=False;p.native_total=7000. if recover else 0.;p.native_time=6002.
                    p.scrobCredentials=p.punchplayCredentials=True
                    p._settings['scrob.markwatched']=p._settings['punchplay.markwatched']='true'
                    p._scrob_heartbeat_at=p._punchplay_heartbeat_at=0.
                    p._maybe_show_skip_intro=p._maybe_show_skip_recap=lambda *a:None
                    p._control.hide=p._control.closeAll=lambda:None
                    p._control.addonInfo=lambda key:'fixture'
                    cycles=iter((False,True));p._control.monitor=SimpleNamespace(abortRequested=lambda:next(cycles))
                    env['xbmc'].sleep=lambda *a:None
                    calls=[]
                    class CaptureThread:
                        def __init__(self,target=None,args=(),kwargs=None):self.kwargs=kwargs
                        def start(self):
                            if self.kwargs is not None:calls.append(self.kwargs)
                    env['Thread']=CaptureThread
                    env['scrob'].scrobbleProgress=env['punchplay'].scrobbleProgress=lambda **kw:None
                    # Don't run terminal cleanup after the one real keepAlive iteration.
                    p.onPlayBackStopped=lambda:None
                    type(p).keepAlive(p)
                    self.assertEqual(len(calls),2 if recover else 0)
                    if recover:
                        self.assertEqual(calls[0]['total_time'],7000.)
                        self.assertAlmostEqual(calls[0]['watched_percent'],85.74)
                    self.assertEqual(p.media_length,7000. if recover else 0.)

    def test_first_valid_native_duration_restores_correct_nonzero_write(self):
        for version in ('apple','fire'):
            with self.subTest(version=version):
                p,outgoing,env=self.prepared(version,True)
                p.timing_lost=False;p.native_total=7000.;p.native_time=6002.
                self.assertAlmostEqual(p.getWatchedPercent(),6002./7000.*100)
                p.timing_lost=True;p.onPlayBackStopped()
                self.assertAlmostEqual(outgoing[-1],6002./7000.*100)
                self.assertEqual(p._events,[])
                self.assertFalse(p._reset_options[-1]['clear_zero'])

    def test_native_correction_below_target_uses_valid_clock_not_impossible_pending_seek(self):
        for version in ('apple','fire'):
            with self.subTest(version=version):
                p,outgoing,env=self.prepared(version,True)
                p.timing_lost=False;p.native_total=5900.;p.native_time=750.
                self.assertAlmostEqual(p.getWatchedPercent(),750./5900.*100)
                self.assertEqual(p.current_time,750.)
                self.assertEqual(p._progress_seek_target,6002.)
                self.assertIsNone(p._progress_pending_seek)
                p.timing_lost=True;p.onPlayBackStopped()
                self.assertAlmostEqual(outgoing[-1],750./5900.*100)
                self.assertFalse(p.watched_during_playback)

    def test_shorter_native_duration_without_valid_clock_keeps_writes_withheld(self):
        for version in ('apple','fire'):
            for native_position in (None,6002.,float('nan')):
                with self.subTest(version=version,native_position=native_position):
                    p,outgoing,env=self.prepared(version,True)
                    p.timing_lost=False;p.native_total=5900.
                    if native_position is None:
                        def unavailable():raise RuntimeError('native clock not ready')
                        p.getTime=unavailable
                    else:p.native_time=native_position
                    self.assertEqual(p.getWatchedPercent(),0.)
                    p.onPlayBackPaused();p.onPlayBackResumed()
                    p.onPlayBackStopped()
                    self.assertEqual(outgoing,[])
                    self.assertEqual(p._starts,[])
                    self.assertEqual(p._events,[])
                    self.assertEqual(p._reset_options,[])
                    self.assertFalse(p.watched_during_playback)

    def test_native_length_alone_cannot_acknowledge_still_valid_pending_target(self):
        for version in ('apple','fire'):
            for native_position in (None,float('nan'),750.):
                with self.subTest(version=version,native_position=native_position):
                    p,outgoing,env=self.prepared(version,True)
                    p.timing_lost=False;p.native_total=7000.
                    if native_position is None:
                        def unavailable():raise RuntimeError('native clock not ready')
                        p.getTime=unavailable
                    else:p.native_time=native_position
                    self.assertEqual(p.getWatchedPercent(),0.)
                    self.assertEqual(p.current_time,6002.)
                    self.assertIsNotNone(p._progress_pending_seek)
                    p.onPlayBackPaused();p.onPlayBackResumed()
                    self.assertEqual(outgoing,[]);self.assertEqual(p._starts,[])
                    # The existing acknowledgment interval remains in force.
                    p.getTime=lambda:6002.
                    self.assertAlmostEqual(p.getWatchedPercent(),6002./7000.*100)
                    self.assertIsNone(p._progress_pending_seek)

    def test_new_in_range_absolute_callback_recovers_consistent_native_snapshot(self):
        for version in ('apple','fire'):
            with self.subTest(version=version):
                p,outgoing,env=self.prepared(version,True)
                p.timing_lost=False;p.native_total=5900.;p.native_time=0.
                p.onPlayBackSeek(750000,-5252000)
                p.timing_lost=True;p.onPlayBackStopped()
                self.assertAlmostEqual(outgoing[-1],750./5900.*100)
                self.assertEqual(p._events,[])

    def test_first_native_duration_can_disprove_previously_in_range_fallback_seek(self):
        for version in ('apple','fire'):
            for native_position in (None,5000.,float('nan'),750.):
                with self.subTest(version=version,native_position=native_position):
                    p,outgoing,env=fixture(version);play(p,{'title':'Fixture','duration':6000})
                    p.timing_lost=True;p.onPlayBackSeek(5000000,5000000)
                    p.timing_lost=False;p.native_total=4800.
                    if native_position is None:
                        def unavailable():raise RuntimeError('native clock not ready')
                        p.getTime=unavailable
                    else:p.native_time=native_position
                    expected=750./4800.*100 if native_position==750. else 0.
                    self.assertAlmostEqual(p.getWatchedPercent(),expected)
                    if native_position!=750.:
                        p.onPlayBackPaused();p.onPlayBackResumed()
                        self.assertEqual(outgoing,[]);self.assertEqual(p._starts,[])
                        p.getTime=lambda:750.
                        self.assertAlmostEqual(p.getWatchedPercent(),750./4800.*100)
                    self.assertEqual(p.current_time,750.)
                    self.assertEqual(p._progress_seek_target,5000.)
                    self.assertIsNone(p._progress_pending_seek)
                    p.timing_lost=True;p.onPlayBackStopped()
                    self.assertAlmostEqual(outgoing[-1],750./4800.*100)
                    self.assertFalse(p.watched_during_playback)

    def test_valid_pending_target_survives_first_native_refinement_and_stale_clock(self):
        for version in ('apple','fire'):
            with self.subTest(version=version):
                p,outgoing,env=fixture(version);play(p,{'title':'Fixture','duration':6000})
                p.timing_lost=True;p.onPlayBackSeek(750000,750000)
                p.timing_lost=False;p.native_total=5900.;p.native_time=10.
                self.assertAlmostEqual(p.getWatchedPercent(),750./5900.*100)
                self.assertEqual(p.current_time,750.)
                self.assertIsNotNone(p._progress_pending_seek)
                p.timing_lost=True;p.onPlayBackStopped()
                self.assertAlmostEqual(outgoing[-1],750./5900.*100)

    def test_contradicted_metadata_cannot_reseed_denominator(self):
        for version in ('apple','fire'):
            with self.subTest(version=version):
                p,_,_=self.prepared(version)
                p._seed_progress_length({'duration':6000})
                self.assertEqual(p.media_length,0.)
                p.onPlayBackSeek(750000,-5252000)
                self.assertEqual(p.current_time,750.)
                self.assertEqual(p.media_length,0.)

    def test_native_authoritative_overlength_still_rejects_callback(self):
        for version in ('apple','fire'):
            with self.subTest(version=version):
                p,_,_=fixture(version);play(p,{'title':'Fixture','duration':6000})
                p.native_total=6001.;p.onPlayBackSeek(750000,750000)
                p.timing_lost=True;p.onPlayBackSeek(6002000,5252000)
                self.assertEqual(p._progress_seek_target,750.)
                self.assertEqual(p.media_length,6001.)

    def test_missing_duration_failed_start_cleanup_is_unchanged(self):
        for version in ('apple','fire'):
            with self.subTest(version=version):
                p,outgoing,_=fixture(version);play(p,{'title':'Fixture'})
                p.timing_lost=True;p.onPlayBackStopped()
                self.assertEqual(outgoing,[0.])
                self.assertEqual(len(p._reset_options),1)
                self.assertEqual(p._events,[])

class DurationPositiveRegressions(ZERO.ZeroPositiveRegressions):
    def setUp(self):
        replacement=patch.object(ZERO,'source',source);replacement.start();self.addCleanup(replacement.stop)
        super().setUp()

class DurationZeroRouteRegressions(ZERO.ZeroRouteTests):
    def setUp(self):
        replacement=patch.object(ZERO,'source',source);replacement.start();self.addCleanup(replacement.stop)

class DurationLocalBookmarkRegressions(ZERO.LocalBookmarkZeroTests):
    def setUp(self):
        replacement=patch.object(ZERO,'source',source);replacement.start();self.addCleanup(replacement.stop)

if __name__=='__main__':unittest.main(verbosity=2)
