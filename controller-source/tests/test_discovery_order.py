import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/"addon"))
try:from discovery_order import Selector
except ModuleNotFoundError:Selector=None

def item(n,title=None,**extra):return {'file':f'plugin://plugin.video.themoviedb.helper/?info=details&tmdb_type=movie&tmdb_id={n}','label':title or f'Title {n}','title':title or f'Title {n}','year':2020,'art':{'landscape':f'https://image.tmdb.org/t/p/w780/{n}.jpg'},'playcount':n%2,'resume':{'position':n,'total':3600},**extra}
class SelectorTests(unittest.TestCase):
 def setUp(self):self.assertTrue(callable(Selector),"Missing production first-page discovery ordering")
 def test_personal_rows_untouched(self):
  s=Selector();a=[item(n) for n in range(20)];self.assertEqual(s.choose('p','personal','x',a,{}),a)
 def test_reduce_repeats_without_losing_any_item(self):
  s=Selector();s.choose('p','r1','p1',[item(n) for n in range(20)],{'enabled':True})
  files=[item(n) for n in range(10,30)];out=s.choose('p','r2','p1',files,{'enabled':True})
  self.assertLessEqual(len({x['file'] for x in out[:12]}&{item(n)['file'] for n in range(12)}),2)
  self.assertEqual({x['file'] for x in out},{x['file'] for x in files})
 def test_deficient_pool_is_retained_and_reported(self):
  s=Selector();files=[item(n) for n in range(20)];s.choose('p','r1','p1',files,{'enabled':True})
  out=s.choose('p','r2','p1',files,{'enabled':True});self.assertEqual(len(out),20);self.assertGreater(s.last['head_repeats'],2)
 def test_metadata_is_not_mutated(self):
  s=Selector();files=[item(n) for n in range(20)];before=copy.deepcopy(files);out=s.choose('p','r','page',files,{'enabled':True})
  self.assertEqual(files,before);self.assertEqual({x['file']:x for x in out},{x['file']:x for x in before})
 def test_return_to_page_keeps_order_but_uses_new_watch_metadata(self):
  s=Selector();files=[item(n) for n in range(20)];first=s.choose('p','r','page',files,{'enabled':True});s.choose('p','other','page',files[4:]+[item(30)],{'enabled':True})
  fresh=copy.deepcopy(files);fresh[0]['playcount']=9
  out=s.choose('p','r','page',list(reversed(fresh)),{'enabled':True});self.assertEqual([x['file'] for x in out],[x['file'] for x in first]);self.assertEqual(out[0]['playcount'],9)
 def test_next_control_remains_last(self):
  s=Selector();nextitem={'label':'Next','filetype':'directory','file':'plugin://plugin.video.themoviedb.helper/?info=discover&tmdb_type=movie&page=2'}
  out=s.choose('p','r','page',[item(1),nextitem],{'enabled':True});self.assertEqual(out[-1],nextitem)
 def test_franchise_head_limit_and_lossless_tail(self):
  s=Selector();files=[item(n,f'Star Trek: Story {n}') for n in range(8)]+[item(100+n) for n in range(12)]
  out=s.choose('p','r','page',files,{'enabled':True});self.assertLessEqual(sum(x['title'].startswith('Star Trek') for x in out[:12]),2);self.assertEqual(len(out),20)
 def test_curated_exclusion_is_scoped_to_theme(self):
  s=Selector();files=[item(1,'Ghosts'),item(2,'The Haunting of Hill House')]
  out=s.choose('p','r','page',files,{'enabled':True,'exclude_ids':['movie:1']});self.assertEqual([x['title'] for x in out],['The Haunting of Hill House'])
  self.assertEqual(len(s.choose('p','comedy','page',files,{'enabled':True})),2)
 def test_only_quality_rows_enforce_vote_ceiling(self):
  s=Selector();files=[item(1,votes='9,000'),item(2,votes='200')]
  self.assertEqual(len(s.choose('p','r','page',files,{'enabled':True,'max_votes':3000})),1)
  self.assertEqual(len(s.choose('p','ordinary','page',files,{'enabled':True})),2)
 def test_memory_bound(self):
  s=Selector(max_entries=8)
  for i in range(100):s.choose(str(i),'r','page',[item(i)],{'enabled':True})
  self.assertLessEqual(len(s.orders),8);self.assertLessEqual(len(s.exposed),8)
 def test_page_and_namespace_isolation(self):
  s=Selector();files=[item(n) for n in range(20)]
  a=s.choose('p','r1','page1',files,{'enabled':True});b=s.choose('q','r1','page1',files,{'enabled':True});self.assertEqual(a,b)
 def test_numeric_metadata_errors_do_not_crash(self):
  s=Selector();out=s.choose('p','r','page',[item(1,votes='bad'),item(2,votes='200')],{'enabled':True,'max_votes':3000});self.assertEqual(len(out),1)
if __name__=='__main__':unittest.main()
