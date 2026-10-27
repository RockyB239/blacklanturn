import unittest,sys,threading,tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
class RequestSettings(unittest.TestCase):
 def test_settings_reused_only_within_request_and_invalidated_explicitly(self):
  from youtube_saved_runtime import SavedYouTube
  owner=SavedYouTube();reads=[];values={}
  addon=SimpleNamespace(getAddonInfo=lambda k:'7',getSetting=lambda k:reads.append(k) or values.get(k,''),getSettingBool=lambda k:True)
  with owner.youtube_saved_request():
   a=owner.request_saved_settings('account',addon)
   self.assertEqual(a,owner.request_saved_settings('account',addon));self.assertEqual(len(reads),12)
   values['youtube.region']='changed';owner.invalidate_saved_youtube_settings()
   self.assertNotEqual(a,owner.request_saved_settings('account',addon));self.assertEqual(len(reads),24)
  owner.request_saved_settings('account',addon);self.assertEqual(len(reads),36)
 def test_account_identity_is_part_of_request_memo_key(self):
  from youtube_saved_runtime import SavedYouTube
  owner=SavedYouTube();addon=SimpleNamespace(getAddonInfo=lambda k:'7',getSetting=lambda k:'',getSettingBool=lambda k:True)
  with owner.youtube_saved_request():self.assertNotEqual(owner.request_saved_settings('one',addon),owner.request_saved_settings('two',addon))
class LatestJobs(unittest.TestCase):
 def test_running_job_is_bounded_and_only_newest_queued_job_runs(self):
  from provider_work import LatestWorker
  started=threading.Event();release=threading.Event();done=threading.Event();calls=[]
  pool=LatestWorker()
  def first():started.set();release.wait(2);calls.append('first')
  pool.submit('rows',first);self.assertTrue(started.wait(1))
  for n in range(100):pool.submit('rows',lambda n=n:calls.append(n))
  pool.submit('rows',lambda:(calls.append('last'),done.set()))
  self.assertEqual(pool.pending_count(),1);release.set();self.assertTrue(done.wait(1));self.assertEqual(calls,['first','last'])
 def test_cancelled_queued_owner_does_not_execute(self):
  from provider_work import LatestWorker
  pool=LatestWorker();start=threading.Event();release=threading.Event();done=threading.Event();calls=[]
  pool.submit('a',lambda:(start.set(),release.wait(2)));self.assertTrue(start.wait(1));pool.submit('b',lambda:calls.append('bad'));pool.cancel('b');pool.submit('c',done.set);release.set();self.assertTrue(done.wait(1));self.assertEqual(calls,[])
