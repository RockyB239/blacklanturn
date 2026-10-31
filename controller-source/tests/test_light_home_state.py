"""Exercise cache ownership and early intent behavior before Kodi boundaries."""
import importlib.util,json,tempfile,time,unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))

class LightHomeState(unittest.TestCase):
 def module(self):
  spec=importlib.util.find_spec('light_home_state')
  self.assertIsNotNone(spec,'Lightweight Home state implementation is absent')
  import light_home_state
  return light_home_state
 def test_latest_explicit_intent_keeps_original_item_and_runs_once(self):
  m=self.module();s=m.EarlyIntent();s.choose('click',102,'movie:1');s.choose('click',101,'movie:2')
  self.assertEqual(s.take(),('click',101,'movie:2'));self.assertIsNone(s.take())
 def test_back_cancels_prior_intent_and_retirement_rejects_late_work(self):
  m=self.module();s=m.EarlyIntent();s.choose('click',101,'movie:1');s.cancel();self.assertIsNone(s.take())
  s.retire();s.choose('click',101,'movie:2');self.assertIsNone(s.take())
 def test_record_mismatched_scope_and_future_or_expired_time_are_not_displayed(self):
  m=self.module()
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'display.json';base={'version':1,'scope':'scope','time':1000.,'rows':[]}
   for change in ({'scope':'other'},{'time':1001.},{'time':-90000.}):
    p.write_text(json.dumps(dict(base,**change)));self.assertIsNone(m.read_record(p,'scope',now=1000.))
 def test_oversized_or_malformed_record_is_ignored_without_writes(self):
  m=self.module()
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'display.json'
   for raw in (b'{bad',b' '* (m.MAX_BYTES+1)):
    p.write_bytes(raw);self.assertIsNone(m.read_record(p,'scope',now=1000.));self.assertEqual(p.read_bytes(),raw)
 def test_scope_includes_feedback_and_layout_but_never_raw_credentials(self):
  m=self.module();base=m.extend_scope('providerhash',b'rows',b'feedback')
  self.assertNotEqual(base,m.extend_scope('providerhash',b'changed',b'feedback'))
  self.assertNotEqual(base,m.extend_scope('providerhash',b'rows',b'changed'))
  self.assertEqual(len(base),64)

if __name__=='__main__':unittest.main()
