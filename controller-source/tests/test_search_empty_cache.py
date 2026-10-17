import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
from row_feedback import RowResultCache
from search_ui import load_best_matches,route
class VerifiedEmptySearchCache(unittest.TestCase):
 def test_explicit_empty_cache_has_short_expiry_and_revision_guard(self):
  now=[0];c=RowResultCache(clock=lambda:now[0]);self.assertFalse(c.put('ordinary',[]))
  self.assertTrue(c.put('verified',[],allow_empty=True,ttl=30,revision=c.revision));self.assertEqual(c.get('verified'),[])
  now[0]=31;self.assertIsNone(c.get('verified'));old=c.revision;c.clear();self.assertFalse(c.put('old',[],allow_empty=True,revision=old))
  self.assertFalse(c.put('unknown',None,allow_empty=True))
 def test_only_successful_empty_batch_components_are_reused(self):
  c=RowResultCache();raw=[{'file':'blacklanturn://search-status?version=2&both=0&company=0&collection=0&movie=-1'}]
  self.assertEqual(load_best_matches('q',lambda p:[],batch_provider=lambda p:raw,cache=c,revision=c.revision),[])
  for kind in ('both','company','collection'):self.assertEqual(c.get(route('search',kind,query='q')),[])
  self.assertIsNone(c.get(route('search','movie',query='q')))
  self.assertEqual(load_best_matches('q',lambda p:self.fail('unnecessary call'),batch_provider=lambda p:self.fail('unnecessary batch'),cache=c,revision=c.revision),[])
if __name__=='__main__':unittest.main()
