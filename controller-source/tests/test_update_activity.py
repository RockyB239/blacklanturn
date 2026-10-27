import sys,time,threading,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
class DeferredWork(unittest.TestCase):
 def test_pending_rows_are_bounded_and_resume_with_latest_after_update(self):
  from provider_work import LatestWorker
  paused=threading.Event();paused.set();done=threading.Event();calls=[]
  try:pool=LatestWorker(paused=paused.is_set)
  except TypeError:self.fail('Provider worker has no updater pause boundary')
  for n in range(100):pool.submit('rows',lambda n=n:(calls.append(n),done.set()))
  self.assertFalse(done.wait(.15));self.assertEqual(pool.pending_count(),1)
  paused.clear();self.assertTrue(done.wait(1));self.assertEqual(calls,[99])
 def test_expired_update_lease_does_not_delay_normal_work(self):
  from provider_work import LatestWorker
  done=threading.Event();pool=LatestWorker();pool.submit('rows',done.set);self.assertTrue(done.wait(1))

 def test_background_provider_boundary_waits_and_exits_on_abort(self):
  from unittest.mock import patch
  import update_activity
  with patch.object(update_activity,'active',side_effect=[True,True,False]),patch.object(update_activity.time,'sleep') as sleep:
   self.assertTrue(update_activity.wait_for_idle());self.assertEqual(sleep.call_count,2)
  with patch.object(update_activity,'active',return_value=True):self.assertFalse(update_activity.wait_for_idle(lambda:True))
 def test_only_owned_preview_is_stopped_during_update(self):
  import ast,types
  from unittest.mock import patch
  path=Path(__file__).parents[1]/'addon/live_review.py'
  cls=next(n for n in ast.parse(path.read_text()).body if isinstance(n,ast.ClassDef) and n.name=='LiveReview')
  fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='update_work_paused');ns={}
  exec(compile(ast.Module(body=[fn],type_ignores=[]),str(path),'exec'),ns)
  calls=[];w=types.SimpleNamespace(owned_preview=False,stop_preview=lambda:calls.append('stop'))
  with patch('update_activity.active',return_value=True):
   self.assertTrue(ns['update_work_paused'](w));self.assertEqual(calls,[])
   w.owned_preview=True;self.assertTrue(ns['update_work_paused'](w));self.assertEqual(calls,['stop'])
