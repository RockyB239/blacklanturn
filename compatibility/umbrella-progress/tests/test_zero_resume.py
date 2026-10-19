"""Explicit zero clears this item's resume using the existing configured route."""
import ast
import hashlib
import importlib.util
import inspect
import os
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('zero_base_contract',HERE/'tests/test_umbrella_progress.py')
BASE=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(BASE)

def source(version):
    number='6.7.90' if version=='apple' else '6.7.92'
    directory='candidate' if os.environ.get('UMBRELLA_ZERO_UPSTREAM')=='1' else 'zero-candidate'
    path=HERE/directory/number/'player.py'
    if not path.exists():path=HERE/'candidate'/number/'player.py'
    return path.read_bytes()

def fixture(version):
    with patch.object(BASE,'source_bytes',source):p,outgoing,local,errors=BASE.fixture(version)
    env=p._sendFinishedItemState.__globals__;events=[];reset_options=[]
    env['trakt'].sync_playbackProgress=lambda **kw:events.append(('sync',kw))
    env['trakt'].scrobbleReset=lambda **kw:events.append(('reset',kw))
    env['Bookmarks']().reset=lambda *a,**kw:(local.append(a),reset_options.append(kw))
    p._events=events;p._reset_options=reset_options
    return p,outgoing,env

class ZeroRouteTests(unittest.TestCase):
    def test_explicit_zero_before_av_ready_syncs_then_deletes_only_configured_trakt_resume(self):
        for version in ('apple','fire'):
            with self.subTest(version=version):
                p,outgoing,env=fixture(version)
                p.onPlayBackSeek(0,-750000);p.timing_lost=True;p.onPlayBackStopped()
                self.assertEqual([x[0] for x in p._events],['sync','reset'])
                self.assertEqual(p._events[0][1],{'forced':True})
                self.assertEqual(p._events[1][1],{'imdb':p.imdb,'tmdb':p.tmdb,'tvdb':p.tvdb,'season':p.season,'episode':p.episode,'refresh':False,'clear_local':True})
                self.assertEqual(outgoing,[])
                self.assertTrue(p._reset_options[-1]['clear_zero'])
                self.assertFalse(p.av_started_ran)

    def test_zero_without_accepted_seek_keeps_existing_failed_start_cleanup(self):
        for version in ('apple','fire'):
            with self.subTest(version=version):
                p,outgoing,_=fixture(version);p.current_time=0.;p.timing_lost=True;p.onPlayBackStopped()
                self.assertEqual(p._events,[])
                self.assertEqual(outgoing,[0.])
                self.assertFalse(p._reset_options[-1].get('clear_zero',False))

    def test_nonzero_seek_followed_by_native_zero_cannot_trigger_explicit_zero_delete(self):
        for version in ('apple','fire'):
            with self.subTest(version=version):
                p,outgoing,_=fixture(version)
                p.onPlayBackSeek(750000,722000);p.native_time=750.;p.getWatchedPercent()
                p.native_time=0.;p.getWatchedPercent();p.timing_lost=True;p.onPlayBackStopped()
                self.assertEqual(p._events,[])
                self.assertFalse(p._reset_options[-1].get('clear_zero',False))

    def test_unknown_or_invalid_duration_cannot_enter_new_network_delete_route(self):
        for version in ('apple','fire'):
            for duration in (0.,-1.,float('nan'),float('inf')):
                with self.subTest(version=version,duration=duration):
                    p,outgoing,_=fixture(version);p.media_length=p.native_total=duration
                    p.onPlayBackSeek(0,-750000);p.timing_lost=True;p.onPlayBackStopped()
                    self.assertEqual(p._events,[])
                    self.assertFalse(p._reset_options[-1].get('clear_zero',False))

    def test_unconfigured_or_local_source_does_not_enter_trakt_sync_delete_route(self):
        for version in ('apple','fire'):
            for mode in ('local','no_credentials','different_provider'):
                with self.subTest(version=version,mode=mode):
                    p,outgoing,_=fixture(version)
                    if mode=='local':p._settings['scrobble.source']='0'
                    elif mode=='no_credentials':p.traktCredentials=False
                    else:p._settings['scrobble.source']='2'
                    p.onPlayBackSeek(0,-750000);p.timing_lost=True;p.onPlayBackStopped()
                    self.assertEqual(p._events,[])
                    self.assertEqual(outgoing,[])

    def test_all_other_existing_provider_zero_payloads_stay_zero(self):
        for version in ('apple','fire'):
            for name,credential,provider_id in (('simkl','simkl','2'),('mdblist','mdblist','3'),('customtrakt','custom','4'),('floppy','floppy','5'),('scrob','scrob','6'),('punchplay','punchplay','7')):
                with self.subTest(version=version,provider=name):
                    p,outgoing,env=fixture(version);p.traktCredentials=False
                    setattr(p,credential+'Credentials',True);p._settings['scrobble.source']=provider_id
                    written=[]
                    env[name]=SimpleNamespace(isReadOnly=lambda:False,
                        scrobbleMovie=lambda *a,**kw:written.append(a[-1]),
                        scrobbleStopMovie=lambda *a,**kw:written.append(a[-1]))
                    p.onPlayBackSeek(0,-750000);p.timing_lost=True;p.onPlayBackStopped()
                    self.assertEqual(p._events,[])
                    self.assertEqual(written,[0.])


    def test_duplicate_zero_stop_does_not_sync_or_delete_twice(self):
        for version in ('apple','fire'):
            with self.subTest(version=version):
                p,outgoing,_=fixture(version)
                p.onPlayBackSeek(0,-750000);p.timing_lost=True
                p.onPlayBackStopped();p.onPlayBackStopped()
                self.assertEqual([x[0] for x in p._events],['sync','reset'])
                self.assertEqual(outgoing,[])

class LocalBookmarkZeroTests(unittest.TestCase):
    def test_actual_sqlite_reset_deletes_only_current_title_resume_after_explicit_zero(self):
        for version in ('apple','fire'):
            with self.subTest(version=version),tempfile.TemporaryDirectory() as folder:
                target,db,errors=self.bookmarks(version,folder)
                kwargs={'clear_zero':True} if 'clear_zero' in inspect.signature(target.reset).parameters else {}
                target.reset(0.,6004.,'Fixture A','2018',**kwargs)
                self.assertEqual(self.rows(db),[('Fixture A','2025'),('Fixture B','2018')],errors)

    def test_default_zero_and_invalid_duration_keep_all_existing_local_records(self):
        for version in ('apple','fire'):
            for duration,explicit in ((6004.,False),(0.,True),(-1.,True),(float('nan'),True),(float('inf'),True)):
                with self.subTest(version=version,duration=duration,explicit=explicit),tempfile.TemporaryDirectory() as folder:
                    target,db,errors=self.bookmarks(version,folder)
                    kwargs={'clear_zero':explicit} if 'clear_zero' in inspect.signature(target.reset).parameters else {}
                    target.reset(0.,duration,'Fixture A','2018',**kwargs)
                    self.assertEqual(self.rows(db),[('Fixture A','2018'),('Fixture A','2025'),('Fixture B','2018')],errors)

    def bookmarks(self,version,folder):
        db=Path(folder)/'bookmarks.db';errors=[]
        with sqlite3.connect(db) as connection:
            connection.execute('CREATE TABLE bookmark (idFile TEXT,timeInSeconds TEXT,Name TEXT,year TEXT,UNIQUE(idFile))')
            connection.executemany('INSERT INTO bookmark VALUES(?,?,?,?)',[('a','750','Fixture A','2018'),('b','500','Fixture B','2018'),('c','750','Fixture A','2025')])
        tree=ast.parse(source(version));nodes=[n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Bookmarks' or isinstance(n,ast.FunctionDef) and n.name.startswith('_progress_')]
        env={'database':sqlite3,'md5':hashlib.md5,'clear_local_bookmarks':lambda:None,
             'getSetting':lambda key:{'bookmarks':'true','markwatched.percent':'85'}.get(key,'false'),
             'control':SimpleNamespace(dataPath=folder,bookmarksFile=str(db),makeFile=lambda _:None),
             'log_utils':SimpleNamespace(error=lambda:errors.append('error'))}
        exec(compile(ast.Module(body=nodes,type_ignores=[]),version,'exec'),env)
        target=env['Bookmarks'].__new__(env['Bookmarks'])
        return target,db,errors

    def rows(self,db):
        with sqlite3.connect(db) as connection:return list(connection.execute('SELECT Name,year FROM bookmark ORDER BY Name,year'))



class ZeroPositiveRegressions(BASE.OriginalProgressContract):
    """Re-run the complete prior behavior suite on each actual new variant."""
    def setUp(self):
        replacement=patch.object(BASE,'source_bytes',source)
        replacement.start();self.addCleanup(replacement.stop)

    def test_seek_to_zero_then_stop_does_not_restore_prior_position(self):
        # Explicit zero now clears the selected Trakt resume rather than sending
        # the API's rejected zero-percent pause. Other provider tests retain zero.
        for version in self.each_version():
            with self.subTest(version=version):
                p,outgoing,_=fixture(version)
                p.current_time=750.;p.native_time=0.
                p.onPlayBackSeek(0,-750000);p.timing_lost=True;p.onPlayBackStopped()
                self.assertEqual(outgoing,[])
                self.assertEqual([event[0] for event in p._events],['sync','reset'])

if __name__=='__main__':unittest.main(verbosity=2)
