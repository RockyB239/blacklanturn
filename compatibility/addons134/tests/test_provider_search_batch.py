import ast, unittest
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlencode,parse_qs
P=Path(__file__).parents[1]/'patched/plugin.video.themoviedb.helper/resources/tmdbhelper/lib/items/directories/tmdb/lists_search.py'
class Batch(unittest.TestCase):
 def state(self,results):
  calls=[];results={"movie":[],**results}
  class Base:
   def __init__(self,handle,qs,**kw):
    self.handle=handle;self.params=kw;self.parent_params=kw.copy();self.trakt_playdata=SimpleNamespace(pre_sync_join=lambda:calls.append(('join',kw['tmdb_type'])))
   def get_directory(self,items_only=False,build_items=True):
    calls.append(('get',self.params.copy(),items_only,build_items))
    result=results[self.params['tmdb_type']]
    if isinstance(result,Exception):raise result
    return result
  methods=[n for n in next(n for n in ast.parse(P.read_text()).body if isinstance(n,ast.ClassDef) and n.name=='ListSearch').body if isinstance(n,ast.FunctionDef) and n.name in ('get_batch_items','get_tmdb_id')]
  cls=ast.ClassDef(name='ListSearch',bases=[ast.Name(id='Base',ctx=ast.Load())],keywords=[],body=methods or [ast.Pass()],decorator_list=[])
  ns={'Base':Base,'urlencode':urlencode};exec(compile(ast.fix_missing_locations(ast.Module(body=[cls],type_ignores=[])),str(P),'exec'),ns)
  C=ns['ListSearch'];C.validate_empty_search=lambda self:calls.append(('validate',self.params['tmdb_type']))
  s=C(1,'',info='search',tmdb_type='both',query='A24',blacklanturn_all='1',widget='true',nextpage='true')
  return s,calls
 def test_batch_retains_finalized_objects_and_standard_child_paths(self):
  a,b,c=object(),object(),object();s,calls=self.state({'both':[a],'company':[b],'collection':[c]})
  items,status=s.get_batch_items();self.assertEqual(items,[a,b,c]);self.assertEqual(status,[('both',1),('company',1),('collection',1),('movie',0)])
  gets=[x for x in calls if x[0]=='get'];self.assertEqual(len(gets),4)
  for _,params,only,build in gets:self.assertNotIn('blacklanturn_all',params);self.assertTrue(only);self.assertTrue(build)
  self.assertEqual([x[1] for x in calls if x[0]=='join'],['both','company','collection','movie'])
 def test_empty_validated_and_failure_joined_and_not_recorded_as_zero(self):
  a=object();s,calls=self.state({'both':[a],'company':None,'collection':RuntimeError('offline')})
  items,status=s.get_batch_items();self.assertEqual(items,[a]);self.assertEqual(status,[('both',1),('company',0),('collection',-1),('movie',0)])
  self.assertIn(('validate','company'),calls);self.assertIn(('join','collection'),calls)
 def test_finalizer_exclusions_match_native_emission_counts(self):
  a=object();s,calls=self.state({'both':[None,a,None],'company':[],'collection':[None]})
  items,status=s.get_batch_items();self.assertEqual(items,[a]);self.assertEqual(status,[('both',1),('company',0),('collection',0),('movie',0)])
  self.assertFalse(any(x[0]=='validate' for x in calls))
 def test_invalid_raw_empty_is_failure_and_joined(self):
  s,calls=self.state({'both':None,'company':[],'collection':[]})
  def invalid(self):raise RuntimeError('bad response')
  type(s).validate_empty_search=invalid
  items,status=s.get_batch_items();self.assertEqual(status,[('both',-1),('company',0),('collection',0),('movie',0)]);self.assertIn(('join','both'),calls)
 def test_search_does_not_resolve_unused_single_title_id(self):
  s,calls=self.state({});s.get_tmdb_id();self.assertEqual(calls,[])
 def test_initial_movies_are_built_in_same_native_pipeline(self):
  a,b=object(),object();s,calls=self.state({'both':[a],'company':[],'collection':[],'movie':[b]});items,status=s.get_batch_items();self.assertEqual(items,[a,b]);self.assertEqual(status[-1],('movie',1));self.assertIn(('join','movie'),calls)
if __name__=='__main__':unittest.main()
