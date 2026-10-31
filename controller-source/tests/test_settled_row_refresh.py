import importlib,sys,tempfile,threading,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
from row_feedback import RowResultCache
from public_rows import PublicRowSnapshots
from test_public_row_snapshots import P,ITEM
from test_window_lifecycle import ROOT,extract

class SettledRows(unittest.TestCase):
 def module(self):
  self.assertTrue((ROOT/'settled_row_refresh.py').is_file(),'Public refresh still starts immediately during rapid scrolling')
  return importlib.import_module('settled_row_refresh')
 def owner(self):
  return SimpleNamespace(defer_public_refresh=True,section='Shows',mode='home',generation=1,result_cache=RowResultCache(),row_request_serial=1,paths=[P,''],path_tokens={},window_lifetime=object(),alive=True,row_window_busy=False,settings_open=False,actions_open=False,nav=False,owned_preview=False,window_ready=[True,True],dwell=10.,player=SimpleNamespace(isPlaying=lambda:False),getProperty=lambda key:'false',getFocusId=lambda:900)
 def pending(self):return [(0,{'path':P,'label':'Public','_snapshot_refresh':True})]
 def test_public_saved_refresh_waits_while_empty_rows_still_submit(self):
  m=self.module();s=self.owner();cold=(1,{'path':P+'&page=2','label':'Cold'})
  self.assertEqual(m.defer_refreshes(s,self.pending()+[cold],now=10.),[cold]);self.assertIsNotNone(s.deferred_public_refresh)
 def test_after_settle_submits_once_and_never_defers_its_own_submission(self):
  m=self.module();s=self.owner();calls=[];s.request_row_loads=lambda pending,focus:calls.append((pending,focus))
  m.defer_refreshes(s,self.pending(),now=10.);self.assertFalse(m.drain_refreshes(s,now=10.5));self.assertEqual(calls,[])
  self.assertTrue(m.drain_refreshes(s,now=10.7));self.assertEqual(len(calls),1);self.assertTrue(calls[0][0][0][1]['_settled_refresh']);self.assertFalse(m.drain_refreshes(s,now=11.))
  self.assertEqual(m.defer_refreshes(s,calls[0][0],now=11.),calls[0][0])
 def test_repeated_scroll_replaces_pending_and_cold_rows_never_wait(self):
  m=self.module();s=self.owner();m.defer_refreshes(s,self.pending(),now=10.)
  for stamp in (10.2,10.4,10.6):s.generation+=1;m.defer_refreshes(s,self.pending(),now=stamp);self.assertFalse(m.drain_refreshes(s,now=stamp+.1))
  cold=[(0,{'path':P+'&page=2','label':'Cold'})];self.assertEqual(m.defer_refreshes(s,cold,now=11.),cold);self.assertIsNone(s.deferred_public_refresh)
 def test_private_home_and_explicit_refresh_keep_existing_immediate_path(self):
  m=self.module();s=self.owner();s.home_snapshot_cache=SimpleNamespace(path_allowed=lambda p:True)
  self.assertEqual(m.defer_refreshes(s,self.pending(),now=10.),self.pending());s.home_snapshot_cache=None;s.section='Home';self.assertEqual(m.defer_refreshes(s,self.pending(),now=10.),self.pending())
 def test_changed_owner_path_token_revision_lifetime_or_serial_drops_work(self):
  m=self.module()
  changes=[lambda s:setattr(s,'alive',False),lambda s:setattr(s,'generation',2),lambda s:s.result_cache.clear(),lambda s:setattr(s,'row_request_serial',2),lambda s:s.paths.__setitem__(0,P+'&page=2'),lambda s:s.path_tokens.update({0:2}),lambda s:setattr(s,'window_lifetime',object())]
  for change in changes:
   s=self.owner();s.request_row_loads=lambda *a:self.fail('Retired refresh submitted');m.defer_refreshes(s,self.pending(),now=10.);change(s);self.assertFalse(m.drain_refreshes(s,now=11.));self.assertIsNone(s.deferred_public_refresh)
 def test_modal_playback_busy_and_active_input_delay_refresh_without_adding_worker(self):
  m=self.module()
  for change in [lambda s:setattr(s,'row_window_busy',True),lambda s:setattr(s,'nav',True),lambda s:setattr(s,'settings_open',True),lambda s:setattr(s,'actions_open',True),lambda s:setattr(s,'getFocusId',lambda:600),lambda s:setattr(s,'dwell',10.9),lambda s:setattr(s,'player',SimpleNamespace(isPlaying=lambda:True))]:
   s=self.owner();m.defer_refreshes(s,self.pending(),now=10.);change(s);self.assertFalse(m.drain_refreshes(s,now=11.));self.assertIsNotNone(s.deferred_public_refresh)
  s=self.owner();m.defer_refreshes(s,self.pending(),now=10.);self.assertFalse(m.drain_refreshes(s,now=11.,dialog=lambda:10106))
 def test_completed_first_row_is_durable_before_second_provider_wait(self):
  queue=[];observed=[]
  with tempfile.TemporaryDirectory() as folder:
   cache=PublicRowSnapshots(Path(folder)/'public.json','scope');second=P+'&page=2'
   def provider(definition,**kw):
    path=definition['path']
    if path==second:
     saved=PublicRowSnapshots(cache.path,'scope').get(P);observed.append(saved);self.assertIsNotNone(saved,'First complete row is still waiting in a two-row disk batch')
    cache.put(path,[ITEM]);return [ITEM]
   s=self.owner();s.defer_public_refresh=False;s.snapshot_cache=cache;s.paths=[P,second];s.list_lock=threading.Lock();s.preview_dispatch_lock=threading.RLock();s.cached_row_items=provider;s.rows=[[],[]];s.apply_row=lambda *a,**k:None;s.setProperty=lambda *a:None;s.failed_paths={};s.row_states={}
   request=extract(ROOT/'live_review.py','request_row_loads',{'submit_latest':lambda owner,work:queue.append(work),'event':lambda *a,**k:None},'LiveReview');request(s,[(0,{'path':P,'label':'First'}),(1,{'path':second,'label':'Second'})])
   with cache.batch():queue.pop()()
   self.assertEqual(len(observed),1);self.assertIsNotNone(observed[0])
 def test_navigation_inside_native_focus_read_cannot_replace_new_foreground_request(self):
  m=self.module();s=self.owner();queue=[];s.preview_dispatch_lock=threading.RLock();s.list_lock=threading.Lock();s.rows=[[],[]];s.cached_row_items=lambda *a,**k:[ITEM];s.apply_row=lambda *a,**k:None;s.setProperty=lambda *a:None
  request=extract(ROOT/'live_review.py','request_row_loads',{'submit_latest':lambda owner,work:queue.append(work),'event':lambda *a,**k:None},'LiveReview');s.request_row_loads=lambda pending,focus=None:request(s,pending,focus)
  m.defer_refreshes(s,self.pending(),now=10.)
  def focus():
   s.generation+=1;s.paths[0]=P+'&page=8';s.request_row_loads([(0,{'path':s.paths[0],'label':'New cold row'})]);return 900
  s.getFocusId=focus
  self.assertFalse(m.drain_refreshes(s,now=11.));self.assertEqual(s.row_request_serial,2);self.assertEqual(len(queue),1);self.assertTrue(s.row_window_busy)

if __name__=='__main__':unittest.main()
