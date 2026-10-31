"""Completed anime-filtered Home shelves must remain usable across restart."""
import copy,sys,tempfile,unittest
from pathlib import Path
from urllib.parse import parse_qs,urlsplit
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
from home_rows import HomeRowSnapshots,home_browse_item_path
from browse_controls import AnimeMetadata
from filtered_pages import PageCancelled
import test_snapshot_controller as fixture
BASE='plugin://plugin.video.themoviedb.helper/?'
W=BASE+'info=trending_week&tmdb_type=tv&nextpage=true&widget=true'
def title(n,anime=False):return {'file':BASE+'info=play&tmdb_type=tv&tmdb_id='+str(n),'filetype':'file','label':str(n),'title':str(n),'genre':['Animation' if anime else 'Drama'],'country':['JP'],'playcount':1,'resume':{'position':10,'total':100}}
def more(page):return {'file':W+'&page='+str(page),'filetype':'directory','label':'Next page'}
def pages():return {W:[title(n,n>2) for n in range(1,21)]+[more(2)],W+'&page=2':[title(n) for n in range(21,41)]+[more(3)]}
def expected():return [title(1),title(2)]+[title(n) for n in range(21,39)]+[{'file':W+'&page=2&bl_start=18','filetype':'directory','label':'Next'}]
class HomeFilteredSnapshots(unittest.TestCase):
 def state(self,folder,provider,scope='account'):
  state,calls,controls,queue=fixture.SnapshotController().state(folder,provider);state.section='Home';state.search_state=None;state.person_context=None;state.discovery_stack=[];state.anime_metadata=AnimeMetadata(folder);state.home_snapshot_cache=HomeRowSnapshots(Path(folder)/'home.json',scope);return state,calls,controls,queue
 def test_completed_home_fill_survives_new_controller_and_paints_exact_order_before_refresh(self):
  with tempfile.TemporaryDirectory() as folder:
   data=pages();s,calls,_,_=self.state(folder,lambda path:data[path]);filled=s.cached_row_items({'path':W,'label':'Weekly'})
   self.assertEqual([item['label'] for item in filled],[str(n) for n in (1,2)]+[str(n) for n in range(21,39)]+['Next']);self.assertEqual(calls,[W,W+'&page=2']);self.assertEqual(s.result_cache.get(W),data[W],'Raw session provider page must remain unchanged')
   fresh,new_calls,controls,queue=self.state(folder,lambda path:self.fail('No provider call before queued refresh'))
   fresh.set_rows([{'path':W,'label':'Weekly'},{'path':'','label':'Local','local_items':[title(999)]}])
   self.assertEqual(new_calls,[]);self.assertEqual([item['label'] for item in fresh.rows[0]],[str(n) for n in (1,2)]+[str(n) for n in range(21,39)]+['Next']);self.assertEqual(fresh.rows[0][-1]['_page_control'],'next');self.assertEqual(parse_qs(urlsplit(fresh.rows[0][-1]['file']).query)['bl_start'],['18']);self.assertEqual(fresh.rows[0][-1]['file'],W+'&page=2&bl_start=18');self.assertTrue(fresh.snapshot_rows[0]);self.assertEqual(len(queue),1)
 def test_complete_home_snapshot_is_used_when_public_raw_candidate_needs_fill(self):
  with tempfile.TemporaryDirectory() as folder:
   data=pages();s,_,_,_=self.state(folder,lambda path:data[path]);s.cached_row_items({'path':W,'label':'Weekly'})
   fresh,calls,_,_=self.state(folder,lambda path:self.fail('Saved completed Home should paint first'));fresh.snapshot_cache.put(W,data[W]);fresh.set_rows([{'path':W,'label':'Weekly'},{'path':'','label':'Local','local_items':[title(999)]}])
   self.assertEqual(calls,[]);self.assertEqual([x['label'] for x in fresh.rows[0]],[str(n) for n in (1,2)]+[str(n) for n in range(21,39)]+['Next']);self.assertEqual(fresh.rows[0][-1]['_page_control'],'next')
 def test_account_scope_is_checked_again_after_fill_before_saving(self):
  with tempfile.TemporaryDirectory() as folder:
   data=pages();changed=[False]
   def provider(path):
    if path!=W:changed[0]=True
    return data[path]
   s,_,_,_=self.state(folder,provider);old=s.home_snapshot_cache
   def configure():
    if changed[0]:
     changed[0]=False;s.invalidate_row_results();s.home_snapshot_cache=HomeRowSnapshots(old.path,'new-native-scope');return True
    return False
   s.configure_row_snapshots=configure
   with self.assertRaises(PageCancelled):s.cached_row_items({'path':W,'label':'Weekly'})
   self.assertIsNone(s.home_snapshot_cache.get(W));self.assertIsNone(HomeRowSnapshots(old.path,'account').get(W))
 def test_filtered_session_fast_hit_persists_complete_home_without_more_requests(self):
  with tempfile.TemporaryDirectory() as folder:
   s,calls,_,_=self.state(folder,lambda path:self.fail('Cached fill must not fetch'));s.result_cache.put('filtered-v1:'+W,expected());s.home_snapshot_cache.put(W,[title(999)])
   self.assertEqual(s.cached_row_items({'path':W,'label':'Weekly'}),expected());self.assertEqual(calls,[])
   retained=HomeRowSnapshots(s.home_snapshot_cache.path,'account').get(W);self.assertEqual([x['label'] for x in retained],[str(n) for n in (1,2)]+[str(n) for n in range(21,39)]+['Next'])
 def test_failed_or_canceled_fill_keeps_previous_good_home_snapshot(self):
  for canceled in (False,True):
   with self.subTest(canceled=canceled),tempfile.TemporaryDirectory() as folder:
    data=pages()
    def provider(path):
     if path!=W:
      if canceled:s.generation+=1;return data[path]
      raise OSError('offline')
     return data[path]
    s,calls,_,_=self.state(folder,provider);s.home_snapshot_cache.put(W,[title(999)]);before=s.home_snapshot_cache.path.read_bytes()
    with self.assertRaises(PageCancelled if canceled else OSError):s.cached_row_items({'path':W,'label':'Weekly'})
    self.assertEqual(s.home_snapshot_cache.path.read_bytes(),before);self.assertEqual(HomeRowSnapshots(s.home_snapshot_cache.path,'account').get(W)[0]['label'],'999')
 def test_account_config_store_replacement_during_fill_cannot_receive_old_work(self):
  with tempfile.TemporaryDirectory() as folder:
   data=pages()
   def provider(path):
    if path!=W:s.invalidate_row_results();s.home_snapshot_cache=HomeRowSnapshots(Path(folder)/'home.json','new-config-scope')
    return data[path]
   s,_,_,_=self.state(folder,provider)
   with self.assertRaises(PageCancelled):s.cached_row_items({'path':W,'label':'Weekly'})
   self.assertIsNone(s.home_snapshot_cache.get(W));self.assertIsNone(HomeRowSnapshots(Path(folder)/'home.json','account').get(W))
 def test_successful_completed_empty_fill_removes_old_home(self):
  with tempfile.TemporaryDirectory() as folder:
   s,_,_,_=self.state(folder,lambda path:[title(n,True) for n in range(20)]+[more(2)] if path==W else []);s.home_snapshot_cache.put(W,[title(999)])
   self.assertEqual(s.cached_row_items({'path':W,'label':'Weekly'}),[]);self.assertIsNone(HomeRowSnapshots(s.home_snapshot_cache.path,'account').get(W))
 def test_shows_weekly_uses_shared_complete_home_display_without_duplicating_public_store(self):
  with tempfile.TemporaryDirectory() as folder:
   data=pages();s,_,_,_=self.state(folder,lambda path:data[path]);s.section='Shows';s.cached_row_items({'path':W,'label':'Weekly'})
   self.assertEqual([x['label'] for x in s.home_snapshot_cache.get(W)],[str(n) for n in (1,2)]+[str(n) for n in range(21,39)]+['Next']);self.assertEqual(s.result_cache.get(W),data[W]);self.assertIsNone(s.snapshot_cache.get(W))
 def test_home_next_cursor_is_bounded_and_cannot_be_a_row_or_unknown_action(self):
  with tempfile.TemporaryDirectory() as folder:
   store=HomeRowSnapshots(Path(folder)/'home.json','account')
   for cursor in (W+'&page=2&bl_start=18',W+'&bl_start=20'):
    self.assertTrue(store.put(W,[title(1),{'file':cursor,'filetype':'directory','label':'Next'}]));self.assertEqual(HomeRowSnapshots(store.path,'account').get(W)[-1]['file'],cursor);self.assertFalse(store.put(cursor,[title(1)]))
   for bad in (W+'&bl_start=0',W+'&bl_start=10001',W+'&page=2&bl_start=-1',W+'&bl_start=1&token=secret',W+'&bl_start=1&bl_start=2',W+'&bl_start=1,2'):
    self.assertFalse(home_browse_item_path(bad),bad)
if __name__=='__main__':unittest.main()
