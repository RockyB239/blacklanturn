"""Discovery first pages must not await a second page just to fill 20 cards."""
import unittest
import test_filtered_pages as original
ORIGIN=original.ORIGIN
from browse_controls import is_next_page
class FirstPageLatency(unittest.TestCase):
 def fixture(self):
  f=original.ControllerFilteredPages();s,calls,controls,pages=f.state();self.addCleanup(f.doCleanups);return s,calls,controls,pages
 def test_available_first_page_renders_without_refill_and_retains_metadata(self):
  s,calls,controls,pages=self.fixture();first=pages[ORIGIN][0];first.update(art={'landscape':'first.jpg'},playcount=1,resume={'position':4,'total':90})
  definition={'label':'Discovery','path':ORIGIN,'discovery_order':{'enabled':True}}
  s.set_rows([definition])
  self.assertEqual(calls,[ORIGIN]);self.assertEqual([x['label'] for x in s.rows[0] if not x.get('_page_control')],['1','2'])
  item=s.rows[0][0];self.assertEqual(item['art'],{'landscape':'first.jpg'});self.assertEqual(item['playcount'],1);self.assertEqual(item['resume'],{'position':4,'total':90});self.assertEqual(s.rows[0][-1]['file'],ORIGIN+'&page=2')
  calls.clear();s.set_rows([definition]);self.assertEqual(calls,[]);self.assertEqual(len(s.rows[0]),3)
 def test_filtered_empty_first_page_still_advances_to_real_titles(self):
  s,calls,_,pages=self.fixture();pages[ORIGIN]=pages[ORIGIN][2:]
  s.set_rows([{'label':'Discovery','path':ORIGIN,'discovery_order':{'enabled':True}}])
  self.assertEqual(calls,[ORIGIN,ORIGIN+'&page=2']);self.assertTrue(any(not x.get('_page_control') for x in s.rows[0]))
 def test_other_routes_retain_full_page_contract(self):
  s,calls,_,_=self.fixture();s.set_rows([{'label':'Original','path':ORIGIN}]);self.assertEqual(len([x for x in s.rows[0] if not x.get('_page_control')]),20);self.assertEqual(len(calls),2)

 def test_next_then_previous_restores_same_partial_page_and_selection(self):
  f=original.ControllerFilteredPages();s,calls,controls,pages=f.state();self.addCleanup(f.doCleanups)
  definition={'label':'Discovery','path':ORIGIN,'discovery_order':{'enabled':True}};s.set_rows([definition]);f.bind_pages(s,calls,pages)
  import copy
  before=copy.deepcopy(s.rows[0]);controls[900].selectItem(2);s.load_path(0,before[-1]['file'],'Next')
  self.assertNotEqual(s.rows[0],before);previous,position=s.histories[0].pop();s.load_path(0,previous,back=True,position=position)
  self.assertEqual(s.rows[0],before);self.assertEqual(controls[900].getSelectedPosition(),2)

 def test_excluded_or_over_vote_limit_first_page_advances_before_publication(self):
  policies=({'enabled':True,'exclude_ids':['tv:1','tv:2']},{'enabled':True,'max_votes':100})
  for policy in policies:
   with self.subTest(policy=policy):
    s,calls,_,pages=self.fixture()
    for item in pages[ORIGIN][:2]:item['votes']=200
    for item in pages[ORIGIN+'&page=2'][:-1]:item['votes']=50
    definition={'label':'Discovery','path':ORIGIN,'discovery_order':policy}
    s.set_rows([definition])
    titles=[x for x in s.rows[0] if not x.get('_page_control')]
    self.assertEqual(calls,[ORIGIN,ORIGIN+'&page=2'])
    self.assertTrue(titles);self.assertEqual(titles[0]['label'],'21')
    calls.clear();s.set_rows([definition]);self.assertEqual(calls,[])
    self.assertTrue(any(not x.get('_page_control') for x in s.rows[0]))
