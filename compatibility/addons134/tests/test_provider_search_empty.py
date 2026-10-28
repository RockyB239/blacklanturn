"""Exercise the scoped provider patch without importing Kodi or credentials."""
import ast,unittest
from pathlib import Path
from types import SimpleNamespace
P=Path(__file__).parents[1]/'patched/plugin.video.themoviedb.helper/resources/tmdbhelper/lib/items/directories/tmdb/lists_search.py'
EMPTY={'page':1,'results':[],'total_pages':0,'total_results':0}
class Base:
 def get_directory_items(self):return self.items
class ProviderEmpty(unittest.TestCase):
 def state(self,response=EMPTY,items=None):
  node=next(n for n in ast.parse(P.read_text()).body if isinstance(n,ast.ClassDef) and n.name=='ListSearch')
  methods=[n for n in node.body if isinstance(n,ast.FunctionDef) and n.name in ('get_directory_items','validate_empty_search')]
  self.assertTrue(methods,'Provider must finish only verified empty search directories')
  cls=ast.ClassDef(name='Patched',bases=[ast.Name(id='Base',ctx=ast.Load())],keywords=[],body=methods,decorator_list=[])
  ns={'Base':Base};exec(compile(ast.fix_missing_locations(ast.Module(body=[cls],type_ignores=[])),str(P),'exec'),ns)
  s=ns['Patched']();s.items=items;s.handle=1;calls=[]
  s.list_properties=SimpleNamespace(query='A24',page=1,get_api_response=lambda page:calls.append(('request',page)) or response)
  s.trakt_playdata=SimpleNamespace(pre_sync_join=lambda:calls.append('join'));s.finish_container=lambda:calls.append('finish')
  return s,calls
 def test_valid_empty_finishes_once_after_sync(self):
  s,calls=self.state();self.assertIsNone(s.get_directory_items());self.assertEqual(calls,[('request',1),'join','finish'])
 def test_populated_results_unchanged_no_extra_request(self):
  items=[{'full':'metadata','cast':['actor']}];s,calls=self.state(items=items)
  self.assertIs(s.get_directory_items(),items);self.assertEqual(calls,[])
 def test_failures_and_nonempty_responses_never_finish_as_success(self):
  for r in ({},None,{'success':False},dict(EMPTY,results=[{'id':7}]),dict(EMPTY,total_results=3),dict(EMPTY,page=2),dict(EMPTY,total_pages=True),dict(EMPTY,total_results='0')):
   s,calls=self.state(r)
   with self.assertRaises(RuntimeError):s.get_directory_items()
   self.assertNotIn('finish',calls)
 def test_cancelled_keyboard_does_not_turn_into_a_completed_search(self):
  s,calls=self.state();s.list_properties.query='';self.assertIsNone(s.get_directory_items());self.assertEqual(calls,[])
 def test_internal_search_handle_does_not_finish_a_plugin_directory(self):
  s,calls=self.state();s.handle=-1;self.assertIsNone(s.get_directory_items());self.assertEqual(calls,[])
 def test_no_more_results_beyond_last_page_is_empty_success(self):
  s,calls=self.state(dict(EMPTY,page=3,total_pages=2,total_results=24));s.list_properties.page=3;s.get_directory_items();self.assertEqual(calls[-1],'finish')
 def test_transport_exception_is_not_swallowed(self):
  s,calls=self.state()
  def fail(page):raise OSError('offline')
  s.list_properties.get_api_response=fail
  with self.assertRaises(OSError):s.get_directory_items()
  self.assertEqual(calls,[])
if __name__=='__main__':unittest.main()
