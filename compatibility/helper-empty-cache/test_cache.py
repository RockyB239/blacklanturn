"""Native Kodi regression suite using the real list parser, decorator and SQLite cache.
The only fakes are the external provider response and title metadata mapping.
Mutations caught: converting failed/malformed requests to [], accepting HTTP errors,
partial multi-page cache writes, or rejecting legitimate empty successes.
"""
import sys,json,unittest,io,sqlite3,importlib.util,uuid
from pathlib import Path

def run(root,mode,addon_root=None):
 import xbmcaddon,xbmcvfs
 home=Path(xbmcvfs.translatePath('special://home/'));addon=Path(addon_root) if addon_root else home/'addons/plugin.video.themoviedb.helper'
 real_addon=xbmcaddon.Addon;xbmcaddon.Addon=lambda id=None:real_addon(id or 'plugin.video.themoviedb.helper')
 sys.path.insert(0,str(addon/'resources'));sys.path.insert(0,str(addon/'resources/modules'))
 for dep in (home/'addons').glob('script.module.*'):
  if (dep/'lib').is_dir():sys.path.append(str(dep/'lib'))
 def load(name,path):
  spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
 if mode=='candidate':
  import tmdbhelper.lib.items.directories
  load('tmdbhelper.lib.items.directories.lists_default',root/'candidate/lists_default.py')
  load('tmdbhelper.lib.items.directories.trakt.lists_standard',root/'candidate/lists_trakt.py')
 import tmdbhelper.lib.items.directories.lists_default as loaded_parser
 if addon_root and not str(Path(loaded_parser.__file__).resolve()).startswith(str(addon.resolve())+'/'):
  raise RuntimeError('Wrong helper loaded')
 from tmdbhelper.lib.items.directories.lists_default import ListProperties,ItemCache
 from tmdbhelper.lib.items.directories.tmdb.lists_standard import ListStandardProperties
 from tmdbhelper.lib.items.directories.trakt.lists_standard import ListTraktStandardProperties
 from tmdbhelper.lib.files.bcache import BasicCache
 from tmdbhelper.lib.files.scache import SimpleCache
 import requests
 class IsolatedCache(SimpleCache):
  _basefolder=str(root)+'/tests-'+mode+'/'
 class QuietBasicCache(BasicCache):
  @staticmethod
  def kodi_traceback(exc,msg):pass  # Expected failures must not show UI notifications.
 holder=next(c.cell_contents for c in ListProperties.get_cached_items.__closure__ if isinstance(c.cell_contents,ItemCache))
 original_cache=holder.cache
 run_id=uuid.uuid4().hex
 calls=[]
 def response(body,status=200):
  r=requests.Response();r.status_code=status;r._content=json.dumps(body).encode();r.headers={'x-pagination-page-count':'2','x-pagination-item-count':'21'};return r
 def props(kind,key,responses,pages=1):
  cls=ListTraktStandardProperties if kind=='trakt' else ListStandardProperties
  class Provider(cls):
   def get_api_response(self,page=1):
    calls.append(page);v=responses[page-1]
    if isinstance(v,Exception):raise v
    return v
   def get_mapped_item(self,item,add_infoproperties=None):return item
  p=Provider();p.cache_name=key;p.page=1;p.pmax=pages;p.results_key='results';return p
 good=[{'title':'Recovered title','id':123}]
 def payload(kind,items):return response(items) if kind=='trakt' else {'results':items,'total_pages':2,'total_results':21}
 class Tests(unittest.TestCase):
  def setUp(self):
   calls.clear();self.cache=QuietBasicCache();self.cache._cache=IsolatedCache(folder='db-'+run_id,filename=self._testMethodName+'.db');holder.cache=self.cache
  def tearDown(self):holder.cache=original_cache
  def assert_retry(self,kind,bad):
   p=props(kind,'retry',[bad]);first=p.get_cached_items()
   self.assertIsNone(self.cache.get_cache('retry'),'failed result was cached')
   with sqlite3.connect(self.cache._cache._db_file) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM simplecache').fetchone()[0],0)
   self.assertIsNone(first)
   result=props(kind,'retry',[payload(kind,good)]).get_cached_items()
   self.assertEqual(result['items'],good);self.assertEqual(len(calls),2)
  def test_trakt_missing_response_retries(self):self.assert_retry('trakt',None)
  def test_tmdb_missing_response_retries(self):self.assert_retry('tmdb',None)
  def test_trakt_null_json_retries(self):self.assert_retry('trakt',response(None))
  def test_trakt_error_object_retries(self):self.assert_retry('trakt',response({'error':'unavailable'}))
  def test_tmdb_error_object_retries(self):self.assert_retry('tmdb',{'success':False})
  def test_tmdb_null_results_retries(self):self.assert_retry('tmdb',{'results':None})
  def test_http_errors_never_cache(self):
   for status in (401,403,429,500,503):
    with self.subTest(status=status):
     calls.clear();key='http'+str(status)
     props('trakt',key,[response([],status)]).get_cached_items()
     self.assertIsNone(self.cache.get_cache(key),'HTTP failure became cached empty success')
     self.assertEqual(props('trakt',key,[response(good)]).get_cached_items()['items'],good)
     self.assertEqual(len(calls),2)
  def test_invalid_json_retries(self):
   r=response([]);r._content=b'<html>gateway error</html>';self.assert_retry('trakt',r)
  def test_transport_exception_retries(self):self.assert_retry('trakt',TimeoutError('simulated transport timeout'))
  def test_successful_empty_lists_cache(self):
   for kind in ('trakt','tmdb'):
    with self.subTest(kind=kind):
     calls.clear();a=props(kind,kind+'empty',[payload(kind,[])]).get_cached_items()
     b=props(kind,kind+'empty',[TimeoutError('must use cached success')]).get_cached_items()
     self.assertEqual(a['items'],[]);self.assertEqual(a,b);self.assertEqual(len(calls),1)
  def test_successful_lists_cache_and_keep_pagination(self):
   for kind in ('trakt','tmdb'):
    with self.subTest(kind=kind):
     calls.clear();a=props(kind,kind+'success',[payload(kind,good)]).get_cached_items()
     b=props(kind,kind+'success',[TimeoutError('must use cache')]).get_cached_items()
     self.assertEqual(a,{'items':good,'pages':2,'count':21});self.assertEqual(a,b);self.assertEqual(len(calls),1)
  def test_partial_tmdb_page_failure_does_not_cache(self):
   p=props('tmdb','partial',[payload('tmdb',good),None],pages=2);p.get_cached_items()
   self.assertIsNone(self.cache.get_cache('partial'),'partial result was cached as complete')
   result=props('tmdb','partial',[payload('tmdb',good),payload('tmdb',[{'title':'Page two','id':124}])],pages=2).get_cached_items()
   self.assertEqual(len(result['items']),2)
 out=io.StringIO()
 try:
  result=unittest.TextTestRunner(stream=out,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
  return {'mode':mode,'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'passed':result.wasSuccessful(),'output':out.getvalue()}
 finally:holder.cache=original_cache;xbmcaddon.Addon=real_addon
