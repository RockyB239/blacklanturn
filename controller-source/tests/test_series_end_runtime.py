import unittest,sys,tempfile,json,types,time,importlib
from pathlib import Path
from unittest.mock import patch
from test_window_lifecycle import extract,ROOT
class SeriesRuntime(unittest.TestCase):
 def modules(self,d,playing=False):
  return {'xbmc':types.SimpleNamespace(getSkinDir=lambda:'owner',Player=lambda:types.SimpleNamespace(isPlaying=lambda:playing)), 'xbmcaddon':types.SimpleNamespace(Addon=lambda _:types.SimpleNamespace(getAddonInfo=lambda _:d)), 'xbmcvfs':types.SimpleNamespace(translatePath=lambda _:d)}
 def target(self):return {'file':'plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=tv&tmdb_id=1&season=1&episode=1','showtitle':'Show','type':'episode','season':1,'episode':1}
 def test_disabled_session_and_stop_never_open_dialog_or_contact_provider(self):
  from series_end import SeriesEndSession
  with tempfile.TemporaryDirectory() as d:
   Path(d,'rows.json').write_text(json.dumps({'SeriesEndSuggestions':False}))
   with patch.dict(sys.modules,self.modules(d)):
    s=SeriesEndSession(self.target(),'owner');self.assertFalse(s.enabled);s.observe_current(None,{});self.assertIsNone(s.worker);self.assertIsNone(s.prompt());s.close()
 def test_chained_identity_clears_old_ready_suggestions(self):
  from series_end import SeriesEndSession
  with tempfile.TemporaryDirectory() as d:
   Path(d,'rows.json').write_text('{}')
   with patch.dict(sys.modules,self.modules(d)):
    s=SeriesEndSession(self.target(),'owner');s.key=('1',1,1);s.items=[{'label':'old'}];s.qualified=True;s.reason='ended'
    p=types.SimpleNamespace(getTime=lambda:10,getTotalTime=lambda:120)
    s.observe_current(p,{'type':'episode','showtitle':'Show','season':2,'episode':1})
    self.assertEqual(s.key,('1',2,1));self.assertEqual(s.items,[]);self.assertFalse(s.qualified);self.assertEqual(s.reason,'');self.assertIsNone(s.worker)
 def test_foreign_playback_invalidates_session(self):
  from series_end import SeriesEndSession
  with tempfile.TemporaryDirectory() as d:
   Path(d,'rows.json').write_text('{}')
   with patch.dict(sys.modules,self.modules(d)):
    s=SeriesEndSession(self.target(),'owner');s.observe_current(None,{'type':'movie','title':'Other'});self.assertFalse(s.current());self.assertIsNone(s.prompt())
 def test_unknown_playback_after_known_episode_retires_prepared_suggestions(self):
  from series_end import SeriesEndSession
  for current in ({'type':'unknown','title':'Unrelated stream'},{'type':'episode','season':1,'episode':1}):
   with self.subTest(current=current),tempfile.TemporaryDirectory() as d:
    Path(d,'rows.json').write_text('{}')
    with patch.dict(sys.modules,self.modules(d)):
     s=SeriesEndSession(self.target(),'owner');s.key=('1',1,1);s.items=[{'label':'old'}];s.qualified=True;s.reason='ended'
     s.observe_current(None,current)
     self.assertFalse(s.current());self.assertFalse(s.qualified);self.assertEqual(s.items,[]);self.assertIsNone(s.prompt())
 def test_missing_startup_metadata_does_not_retire_unobserved_episode(self):
  from series_end import SeriesEndSession
  with tempfile.TemporaryDirectory() as d:
   Path(d,'rows.json').write_text('{}')
   with patch.dict(sys.modules,self.modules(d)):
    s=SeriesEndSession(self.target(),'owner');s.observe_current(None,{'type':'unknown'})
    self.assertTrue(s.current());self.assertFalse(s.qualified)
    p=types.SimpleNamespace(getTime=lambda:10,getTotalTime=lambda:120)
    s.observe_current(p,{'type':'episode','showtitle':'Show','season':1,'episode':1});self.assertEqual(s.key,('1',1,1))
 def test_late_result_cannot_publish_after_close(self):
  import series_end
  from threading import Event
  with tempfile.TemporaryDirectory() as d:
   Path(d,'rows.json').write_text('{}');started=Event();release=Event();calls=[]
   def provider(path):calls.append(path);started.set();release.wait(2);return []
   fake=types.SimpleNamespace(load_show_package=provider)
   with patch.dict(sys.modules,dict(self.modules(d),series_metadata=fake)),patch.object(series_end,'completed_latest',return_value=True):
    s=series_end.SeriesEndSession(self.target(),'owner');s.observe_current(types.SimpleNamespace(getTime=lambda:90,getTotalTime=lambda:120),{'type':'episode','showtitle':'Show','season':1,'episode':1})
    self.assertTrue(started.wait(2));s.close();release.set();s.worker.join(2)
    self.assertEqual(calls,['1']);self.assertEqual(s.items,[]);self.assertFalse(s.qualified)
 def test_returned_choice_opens_details_without_starting_another_series(self):
  # Actual production start() handles this browsing return, no Player.Open.
  calls=[];state={'_series_end_open':{'label':'New show'}}
  w=types.SimpleNamespace(alive=True,window_lifetime=1,resume_backend=None,resume_playback=state,restore_browse=lambda s:True,details=lambda item:calls.append(item),refresh_watch_status=lambda **kw:self.fail('must not refresh old title'))
  extract(ROOT/'live_review.py','start',{},'LiveReview')(w)
  self.assertEqual(calls,[{'label':'New show'}])
