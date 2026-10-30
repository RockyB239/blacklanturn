import unittest,tempfile,sqlite3
from pathlib import Path
from datetime import date
import series_end_core as core
from test_personal_library import title
class SeriesEndCore(unittest.TestCase):
 def test_only_natural_qualified_owned_ready_end_can_show(self):
  self.assertTrue(core.should_offer('ended',True,True,True,True))
  for reason in ('stopped','error',''):
   self.assertFalse(core.should_offer(reason,True,True,True,True))
  for i in range(4):
   values=[True]*4;values[i]=False;self.assertFalse(core.should_offer('ended',*values))
 def test_actual_episode_identity_tracks_chain_but_rejects_other_show_and_movie(self):
  target={'file':'plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=tv&tmdb_id=1413&season=1&episode=1','showtitle':'Show','season':1,'episode':1}
  self.assertEqual(core.current_episode(target,{'type':'episode','showtitle':'SHOW','season':2,'episode':3}),('1413',2,3))
  for current in ({'type':'episode','showtitle':'Other','season':1,'episode':1},{'type':'movie','showtitle':'Show','season':1,'episode':1},{'type':'episode','showtitle':'Show','season':-1,'episode':1}):self.assertIsNone(core.current_episode(target,current))
 def test_fresh_last_aired_requires_exact_episode_and_no_next_aired_today(self):
  with tempfile.TemporaryDirectory() as d:
   folder=Path(d)/'database_1';folder.mkdir();db=folder/'ItemDetails.db'
   with sqlite3.connect(db) as c:
    c.executescript('CREATE TABLE baseitem(id TEXT,expiry INTEGER);CREATE TABLE tvshow(id TEXT,tmdb_id INTEGER,last_episode_to_air_id TEXT,next_episode_to_air_id TEXT);CREATE TABLE episode(id TEXT,season_id TEXT,episode INTEGER,premiered TEXT);CREATE TABLE season(id TEXT,season INTEGER);')
    c.execute('INSERT INTO baseitem VALUES (?,?)',('tv.1',200));c.execute('INSERT INTO tvshow VALUES (?,?,?,?)',('tv.1',1,'ep.last','ep.next'))
    c.execute('INSERT INTO season VALUES (?,?)',('s.2',2));c.executemany('INSERT INTO episode VALUES (?,?,?,?)',[('ep.last','s.2',8,'2026-10-20'),('ep.next','s.2',9,'2026-11-01')])
   self.assertTrue(core.latest_available(d,('1',2,8),100,date(2026,10,29)))
   self.assertFalse(core.latest_available(d,('1',2,7),100,date(2026,10,29)));self.assertFalse(core.latest_available(d,('1',2,8),201,date(2026,10,29)))
   with sqlite3.connect(db) as c:c.execute("UPDATE episode SET premiered='2026-10-29' WHERE id='ep.next'")
   self.assertFalse(core.latest_available(d,('1',2,8),100,date(2026,10,29)))
 def test_missing_or_broken_metadata_cannot_mean_caught_up(self):
  with tempfile.TemporaryDirectory() as d:self.assertFalse(core.latest_available(d,('1',1,1),100,date(2026,10,29)))
 def test_suggestions_exclude_current_watched_hidden_and_duplicates(self):
  items=[title(1,'tv'),title(2,'tv'),title(2,'tv'),title(3,'tv'),title(4,'tv'),title(5,'movie')]
  for x in items:x['playcount']=0
  items[4]['playcount']=1
  class Pref:
   def apply(self,values):return [x for x in values if 'tmdb_id=3' not in x['file']]
  result=core.suggestions(items,'1',Pref());self.assertEqual([x['label'] for x in result],['Title 2'])
class LiveMetadata(unittest.TestCase):
 def test_response_identity_last_aired_and_next_airdate_are_required(self):
  data={'id':1,'last_episode_to_air':{'season_number':2,'episode_number':8,'air_date':'2026-10-20'},'next_episode_to_air':{'season_number':3,'episode_number':1,'air_date':'2027-01-01'}}
  self.assertTrue(core.completed_latest(data,('1',2,8),date(2026,10,29)))
  self.assertFalse(core.completed_latest(data,('1',2,7),date(2026,10,29)))
  self.assertFalse(core.completed_latest(dict(data,id=2),('1',2,8),date(2026,10,29)))
  self.assertFalse(core.completed_latest(dict(data,next_episode_to_air={'air_date':'2026-10-29'}),('1',2,8),date(2026,10,29)))
  self.assertFalse(core.completed_latest({},('1',2,8),date(2026,10,29)))
 def test_public_recommendation_mapping_uses_safe_provider_routes_and_wide_art(self):
  result=core.map_recommendations({'recommendations':{'results':[{'id':2,'name':'New Show','overview':'Story','first_air_date':'2024-01-02','backdrop_path':'/wide.jpg','poster_path':'/poster.jpg'},{'id':-1,'name':'Bad'}]}})
  self.assertEqual(len(result),1);self.assertEqual(result[0]['file'],'plugin://plugin.video.themoviedb.helper/?info=seasons&tmdb_type=tv&tmdb_id=2');self.assertEqual(result[0]['art']['landscape'],'https://image.tmdb.org/t/p/w780/wide.jpg')
class NativeEpisodeObservation(unittest.TestCase):
 def test_native_episode_tag_recovers_missing_rpc_fields_without_guessing(self):
  from types import SimpleNamespace as NS
  target={'file':'plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=tv&tmdb_id=1396&season=5&episode=16','showtitle':'Breaking Bad'}
  tag=NS(getMediaType=lambda:'episode',getTVShowTitle=lambda:'Breaking Bad',getSeason=lambda:5,getEpisode=lambda:16)
  player=NS(getVideoInfoTag=lambda:tag)
  self.assertEqual(core.observed_episode(target,{'type':'unknown','showtitle':'','season':-1,'episode':-1},player),('1396',5,16))
  self.assertIsNone(core.observed_episode(target,{'type':'movie'},player))
  self.assertIsNone(core.observed_episode(target,{'type':'episode','showtitle':'Other show','season':5,'episode':16},player))
  self.assertIsNone(core.observed_episode(target,{'type':'unknown','season':2},player))
  tag.getMediaType=lambda:'movie'
  self.assertIsNone(core.observed_episode(target,{'type':'unknown'},player))
 def test_unknown_native_tag_or_missing_player_never_means_episode(self):
  self.assertIsNone(core.observed_episode({'file':'bad'}, {'type':'unknown'},None))
