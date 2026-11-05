"""Read-only browse helpers must release their handles even if GC is delayed."""
from contextlib import closing
from datetime import date
from pathlib import Path
import sqlite3,tempfile,unittest
from unittest.mock import patch
import local_watch,series_status,movie_series,preview_language,series_end_core,browse_controls

class ReadConnections(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.profile=Path(self.tmp.name);folder=self.profile/'database_1';folder.mkdir();self.db=folder/'ItemDetails.db'
  with closing(sqlite3.connect(self.db)) as c:
   c.executescript("""CREATE TABLE simplecache(id TEXT,plays INTEGER,aired_episodes INTEGER,watched_episodes INTEGER,playback_progress REAL);
CREATE TABLE movie(id TEXT,tmdb_id INTEGER,title TEXT,originaltitle TEXT);
CREATE TABLE tvshow(id TEXT,tmdb_id INTEGER,status TEXT,title TEXT,originaltitle TEXT,last_episode_to_air_id TEXT,next_episode_to_air_id TEXT);
CREATE TABLE collection(id TEXT,tmdb_id INTEGER,title TEXT);CREATE TABLE belongs(id TEXT,parent_id TEXT);
CREATE TABLE baseitem(id TEXT,expiry REAL);CREATE TABLE season(id TEXT,season INTEGER);CREATE TABLE episode(id TEXT,episode INTEGER,premiered TEXT,season_id TEXT);
CREATE TABLE video(parent_id TEXT,key TEXT,name TEXT,iso_language TEXT,content TEXT);
CREATE TABLE genre(parent_id TEXT,tmdb_id INTEGER);CREATE TABLE country(parent_id TEXT,iso_country TEXT);
INSERT INTO simplecache VALUES('movie.1',0,NULL,NULL,50);INSERT INTO movie VALUES('movie.1',1,'Title','Original');
INSERT INTO tvshow VALUES('tv.1',1,'Ended','Show','Original show','ep.1',NULL);INSERT INTO baseitem VALUES('tv.1',9999999999);
INSERT INTO season VALUES('season.1',1);INSERT INTO episode VALUES('ep.1',1,'2020-01-01','season.1');
INSERT INTO collection VALUES('collection.7',7,'Collection');INSERT INTO belongs VALUES('movie.1','collection.7');
INSERT INTO video VALUES('movie.1','abc','Trailer','en','Trailer');INSERT INTO genre VALUES('movie.1',16);INSERT INTO country VALUES('movie.1','US');""");c.commit()
  self.movie={'file':'plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=movie&tmdb_id=1','filetype':'file','type':'movie','title':'Title','runtime':1200,'playcount':0,'genre':['Animation']}
  self.show={'file':'plugin://plugin.video.themoviedb.helper/?info=seasons&tmdb_type=tv&tmdb_id=1','filetype':'directory','type':'tvshow','title':'Show'}
  self.connections=[];self.sql=[];real=sqlite3.connect;owner=self
  class Tracked(sqlite3.Connection):
   released=False
   def close(self):self.released=True;return super().close()
  def connect(*args,**kwargs):
   owner.assertIn('mode=ro',str(args[0]));kwargs['factory']=Tracked;c=real(*args,**kwargs);c.set_trace_callback(owner.sql.append);owner.connections.append(c);return c
  self.real_connect=real;self.tracker=patch.object(sqlite3,'connect',connect);self.tracker.start();self.addCleanup(self.tracker.stop);self.addCleanup(self.close_all)
 def close_all(self):
  for c in self.connections:
   if not c.released:c.close()
 def readers(self):
  return [('watch',lambda:local_watch.hydrate_local(self.profile,[self.movie])),('status',lambda:series_status.SeriesStatus(self.profile).enrich([self.show])),('collection',lambda:movie_series.collection_identity(self.profile,1)),('video_language',lambda:preview_language.cached_video_metadata(self.profile,('movie',1))),('title_aliases',lambda:preview_language.cached_title_aliases(self.profile,('movie',1))),('series_end',lambda:series_end_core.latest_available(self.profile,('1',1,1),now=1,today=date(2025,1,1))),('anime',lambda:browse_controls.AnimeMetadata(self.profile).without_anime([self.movie]))]
 def check_readers(self):
  for name,read in self.readers():
   with self.subTest(reader=name):
    start=len(self.connections);read();opened=self.connections[start:];self.assertTrue(opened,'Reader must exercise real SQLite');self.assertTrue(all(c.released for c in opened),'Read handle remains open after '+name)
  self.assertTrue(all(q.lstrip().upper().startswith(('SELECT','PRAGMA')) for q in self.sql),self.sql)
 def test_success_closes_all_seven_read_paths(self):self.check_readers()
 def test_query_errors_close_read_handles_and_keep_fallbacks(self):
  with closing(self.real_connect(self.db)) as c:c.execute('DROP TABLE simplecache');c.execute('DROP TABLE tvshow');c.execute('DROP TABLE movie');c.execute('DROP TABLE genre');c.commit()
  self.check_readers()
 def test_schema_fallback_closes_newer_database_before_older_one(self):
  newer=self.profile/'database_2';newer.mkdir()
  with closing(self.real_connect(newer/'ItemDetails.db')) as c:c.execute('CREATE TABLE irrelevant(value TEXT)');c.commit()
  self.assertEqual(preview_language.cached_title_aliases(self.profile,('movie',1)),['Title','Original']);self.assertEqual(len(self.connections),2);self.assertTrue(all(c.released for c in self.connections))
 def test_watched_updates_are_read_fresh_after_closure(self):
  a=local_watch.hydrate_local(self.profile,[self.movie]);self.assertEqual(a[0]['resume']['position'],600)
  with closing(self.real_connect(self.db)) as c:c.execute("UPDATE simplecache SET plays=1,playback_progress=0 WHERE id='movie.1'");c.commit()
  b=local_watch.hydrate_local(self.profile,[self.movie]);self.assertEqual(b[0]['playcount'],1);self.assertEqual(b[0]['resume']['position'],0);self.assertTrue(all(c.released for c in self.connections));self.assertEqual(self.movie['playcount'],0)
 def test_locked_database_returns_previous_metadata_and_closes(self):
  writer=self.real_connect(self.db);self.addCleanup(writer.close);writer.execute('BEGIN EXCLUSIVE')
  self.assertEqual(local_watch.hydrate_local(self.profile,[self.movie]),[self.movie]);self.assertTrue(all(c.released for c in self.connections));writer.rollback()
