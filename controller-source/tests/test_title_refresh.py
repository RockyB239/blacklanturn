import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"addon"))
from title_refresh import refresh_title
class Refresh(unittest.TestCase):
 def test_tv_refresh_is_targeted_and_keeps_custom_art(self):
  calls=[]
  class Request:
   def __init__(self,kind):self.kind=kind
   @property
   def data(self):calls.append(self.__dict__.copy());return {"id":42}
  refresh_title({'tmdb_type':'tv','tmdb_id':'42','season':2,'episode':3},Request)
  self.assertEqual([c['kind'] for c in calls],['tvshow','season','episode'])
  self.assertTrue(all(c['clear_user_art'] is False and c['cache_refresh']=='force' for c in calls))
  self.assertEqual([(c['season'],c['episode']) for c in calls],[(None,None),(2,None),(2,3)])
 def test_invalid_identity_never_calls_provider(self):
  for params in ({},{'tmdb_type':'person','tmdb_id':'42'},{'tmdb_type':'tv','tmdb_id':'oops'}):
   with self.assertRaises(ValueError):refresh_title(params,lambda _:self.fail('invalid provider call'))
 def test_failure_is_reported_to_owner_without_followup_requests(self):
  calls=[]
  class Request:
   def __init__(self,kind):calls.append(kind)
   @property
   def data(self):raise OSError('unavailable')
  with self.assertRaises(OSError):refresh_title({'tmdb_type':'tv','tmdb_id':'42','season':2},Request)
  self.assertEqual(calls,['tvshow'])
 def test_missing_data_is_not_a_success(self):
  class Request:
   def __init__(self,kind):pass
   @property
   def data(self):return None
  with self.assertRaises(RuntimeError):refresh_title({'tmdb_type':'tv','tmdb_id':'42'},Request)
