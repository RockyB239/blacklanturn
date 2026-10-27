import importlib.util,unittest
from pathlib import Path
class PerformanceGate(unittest.TestCase):
 def module(self):
  spec=importlib.util.spec_from_file_location('performance_gate',Path(__file__).parents[1]/'tools/device_validation/performance_gate.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
 def test_warm_regression_and_mismatched_protocol_cannot_pass(self):
  m=self.module();before={'protocol':'matched','passed':True,'row_visits':[{'section':s,'seconds':.4} for n in range(4) for s in ('Home','Shows','Movies','YouTube','My Stuff')]}
  after=dict(before,row_visits=[dict(x,seconds=2) for x in before['row_visits']]);self.assertFalse(m.compare(before,after)['passed'])
  self.assertFalse(m.compare(before,dict(before,protocol='different'))['passed']);self.assertTrue(m.compare(before,before)['passed'])
 def test_missing_sections_and_false_receipts_fail_closed(self):
  m=self.module();self.assertFalse(m.compare({'protocol':'same','row_visits':[]},{'protocol':'same','row_visits':[]})['passed'])

 def test_soak_requires_twenty_visits_to_every_section(self):
  m=self.module();receipt={'passed':True,'row_visits':[{'section':'Home','seconds':.3} for _ in range(84)]+[{'section':s,'seconds':.3} for s in ('Shows','Movies','YouTube','My Stuff') for _ in range(4)],'memory':{'rss_start':100,'rss_end':100}}
  self.assertFalse(m.soak(receipt)['passed'])
