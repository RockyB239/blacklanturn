import ast,threading,time,unittest
from pathlib import Path
P=Path(__file__).parents[1]/'cocoscrapers-source/lib/cocoscrapers/modules/source_utils.py'
def decorator():
 node=next(n for n in ast.parse(P.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='airdate_sources')
 ns={'episode_airdate':lambda data:data.get('aired'),'scraper_error':lambda *args:None}
 exec(compile(ast.Module(body=[node],type_ignores=[]),str(P),'exec'),ns);return ns['airdate_sources']
DATA={'tvshowtitle':'Example','aired':'2026.10.21'}
class ParallelAirdate(unittest.TestCase):
 def test_opted_in_numbered_and_dated_searches_overlap_and_keep_identical_ordered_union(self):
  primary=threading.Event();dated=threading.Event();overlap=[]
  class Provider:
   parallel_airdate=True
   @decorator()
   def sources(self,data,hosts):
    if data.get('_coco_airdate_query'):
     dated.set();self.assert_event=primary.wait(.4);return [{'hash':'DUP','name':'dated duplicate'},{'hash':'two'}]
    primary.set();overlap.append(dated.wait(.4));return [{'hash':'dup','name':'original'},{'hash':'one'}]
  original=dict(DATA);result=Provider().sources(DATA,{})
  self.assertEqual(overlap,[True]);self.assertEqual(result,[{'hash':'dup','name':'original'},{'hash':'one'},{'hash':'two'}]);self.assertEqual(DATA,original)
 def test_stateful_providers_remain_sequential_and_capture_each_result_list(self):
  order=[]
  class Provider:
   @decorator()
   def sources(self,data,hosts):
    value='dated' if data.get('_coco_airdate_query') else 'primary';order.append(value);self.sources_list=[{'hash':value}];return self.sources_list
  self.assertEqual(Provider().sources(DATA,{}),[{'hash':'primary'},{'hash':'dated'}]);self.assertEqual(order,['primary','dated'])
 def test_dated_error_retains_primary_and_primary_error_still_propagates(self):
  class Provider:
   parallel_airdate=True
   @decorator()
   def sources(self,data,hosts):
    if data.get('_coco_airdate_query'):raise OSError('offline')
    return [{'hash':'valid'}]
  self.assertEqual(Provider().sources(DATA,{}),[{'hash':'valid'}])
  class Broken:
   parallel_airdate=True
   @decorator()
   def sources(self,data,hosts):raise ValueError('bad provider')
  with self.assertRaises(ValueError):Broken().sources(DATA,{})
 def test_movies_and_episodes_without_airdate_still_issue_only_one_search(self):
  calls=[]
  class Provider:
   parallel_airdate=True
   @decorator()
   def sources(self,data,hosts):calls.append(dict(data));return []
  p=Provider();p.sources({'title':'Movie'},{});p.sources({'tvshowtitle':'No date'},{});self.assertEqual(len(calls),2)
 def test_empty_numbered_results_still_include_dated_only_releases(self):
  class Provider:
   parallel_airdate=True
   @decorator()
   def sources(self,data,hosts):return [{'hash':'dated-only'}] if data.get('_coco_airdate_query') else []
  self.assertEqual(Provider().sources(DATA,{}),[{'hash':'dated-only'}])
 def test_only_reviewed_stateless_torrentdownload_provider_opts_in(self):
  source=P.parents[1]/'sources_cocoscrapers/torrents/torrentdownload.py';tree=ast.parse(source.read_text());cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='source');attributes={n.targets[0].id:ast.literal_eval(n.value) for n in cls.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and isinstance(n.value,ast.Constant)}
  self.assertTrue(attributes.get('parallel_airdate',False))

 def test_reviewed_bitsearch_single_search_can_overlap_without_mutating_provider_state(self):
  source=P.parents[1]/'sources_cocoscrapers/torrents/bitsearch.py';cls=next(n for n in ast.parse(source.read_text()).body if isinstance(n,ast.ClassDef) and n.name=='source')
  attrs={n.targets[0].id:ast.literal_eval(n.value) for n in cls.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and isinstance(n.value,ast.Constant)}
  self.assertTrue(attrs.get('parallel_airdate',False))
  method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='sources')
  writes=[n for n in ast.walk(method) if isinstance(n,ast.Attribute) and isinstance(n.ctx,ast.Store) and isinstance(n.value,ast.Name) and n.value.id=='self']
  self.assertEqual(writes,[],'Opt-in applies only to this stateless single search; pack methods stay unchanged')
