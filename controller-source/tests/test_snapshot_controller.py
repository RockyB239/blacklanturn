"""Run real controller methods with queued threads and real bounded caches."""
import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
from public_rows import PublicRowSnapshots
import test_discovery_controller as fixture
from test_public_row_snapshots import P,ITEM

class SnapshotController(unittest.TestCase):
 def state(self,folder,provider):
  queue=[]
  class QueuedThread(fixture.SyncThread):
   def start(self):queue.append(self.target)
  s,calls,controls=fixture.DiscoveryController().state(QueuedThread,provider)
  from cache_fixture import bind
  bind(s,{'row_items':__import__('live_core').row_items,'get_list':lambda path:calls.append(path) or provider(path)})
  from native_list_fixture import native_cards
  native_cards(s,controls)
  s.snapshot_cache=PublicRowSnapshots(Path(folder)/'snapshot.json','scope')
  s.snapshot_cache.put(P,[ITEM]);s.config={};s.focus=900;s.getFocusId=lambda:s.focus;s.setFocusId=lambda cid:setattr(s,'focus',cid)
  return s,calls,controls,queue
 def test_snapshot_is_visible_before_provider_worker_and_refresh_keeps_selected_title(self):
  with tempfile.TemporaryDirectory() as folder:
   later=dict(ITEM,file=ITEM['file'].replace('42','43'),title='Second',playcount=0)
   s,calls,controls,queue=self.state(folder,lambda path:[later,ITEM])
   s.update=lambda item:setattr(s,'selected',item)
   s.set_rows([{'label':'Public','path':P}])
   self.assertEqual([x.get('title') for x in s.rows[0]],['Public title']);self.assertEqual(calls,[])
   self.assertNotIn('playcount',s.rows[0][0]);s.focus=105
   queue.pop(0)()
   self.assertEqual(calls,[P]);self.assertEqual(controls[900].pos,0);self.assertEqual(s.focus,105)
   self.assertEqual([x['title'] for x in s.rows[0]],['Public title'])
   self.assertEqual(s.rows[0][0]['playcount'],1)
   self.assertEqual(s.selected.get('playcount'),1,'Hero actions must use the refreshed status while focus stays on a button')
 def test_refresh_hydrates_native_watch_and_resume_without_list_or_focus_messages(self):
  with tempfile.TemporaryDirectory() as folder:
   s,calls,controls,queue=self.state(folder,lambda path:[dict(ITEM,playcount=2,resume={'position':40,'total':100})])
   s.set_rows([{'label':'Public','path':P}]);card=controls[900].items[0]
   self.assertEqual(card.properties['watchState'],'unknown');self.assertEqual(card.resume,(0,0))
   mutations=[]
   for method in ('reset','addItems','selectItem'):
    original=getattr(controls[900],method)
    setattr(controls[900],method,lambda *a,m=method,fn=original:(mutations.append(m),fn(*a)))
   s.setFocusId=lambda cid:mutations.append('focus')
   queue.pop(0)()
   self.assertEqual(mutations,[],'Automatic refresh may only mutate existing item watch metadata')
   self.assertIs(controls[900].items[0],card)
   self.assertEqual(card.info['playcount'],2);self.assertEqual(card.resume,(40.,100.))
   self.assertEqual({k:card.properties[k] for k in ('watchState','watchLabel','watchPercent')},{'watchState':'progress','watchLabel':'In progress · 40%','watchPercent':'40'})
 def test_refresh_keeps_visible_membership_then_revisit_adopts_fresh_order_and_title(self):
  with tempfile.TemporaryDirectory() as folder:
   later=dict(ITEM,file=ITEM['file'].replace('42','43'),title='Second')
   removed=dict(ITEM,file=ITEM['file'].replace('42','44'),title='Removed')
   s,calls,controls,queue=self.state(folder,lambda path:[later,ITEM])
   s.snapshot_cache.put(P,[ITEM,removed]);s.set_rows([{'label':'Public','path':P},{'label':'Other','path':'other'},{'label':'Third','path':'third'}])
   queue.pop(0)()
   self.assertEqual([x['title'] for x in s.rows[0]],['Public title','Removed'])
   self.assertEqual([x['title'] for x in s.result_cache.get(P)],['Second','Public title'])
   s.show_row_window(1,0);s.show_row_window(0,0)
   self.assertEqual([x['title'] for x in s.rows[0]],['Second','Public title'])
   self.assertEqual(controls[900].pos,1);self.assertEqual(calls.count(P),1)
 def test_empty_fresh_row_is_adopted_on_revisit_without_refetch_or_live_removal(self):
  with tempfile.TemporaryDirectory() as folder:
   s,calls,controls,queue=self.state(folder,lambda path:[])
   s.set_rows([{'label':'Public','path':P},{'label':'Local','path':'','local_items':[{'file':'local'}]},{'label':'Third','path':'','local_items':[{'file':'third'}]}])
   card=controls[900].items[0];queue.pop(0)()
   self.assertEqual(s.rows[0][0]['title'],'Public title');self.assertIs(controls[900].items[0],card)
   s.show_row_window(1,0);s.show_row_window(0,0)
   self.assertEqual(s.rows[0],[]);self.assertEqual(controls[900].items,[])
   self.assertEqual(s.row_states[0],'empty');self.assertEqual(calls,[P])
 def test_fresh_order_and_selected_identity_survive_session_ttl_and_eviction(self):
  from row_feedback import RowResultCache
  for boundary in ('expiry','eviction'):
   with self.subTest(boundary=boundary),tempfile.TemporaryDirectory() as folder:
    later=dict(ITEM,file=ITEM['file'].replace('42','43'),title='Second')
    s,calls,controls,queue=self.state(folder,lambda path:[later,ITEM]);now=[1000.]
    s.result_cache=RowResultCache(clock=lambda:now[0],max_rows=1)
    s.set_rows([{'label':'Public','path':P},{'label':'Local','path':'','local_items':[{'file':'local'}]},{'label':'Third','path':'','local_items':[{'file':'third'}]}]);queue.pop(0)()
    if boundary=='expiry':now[0]+=121
    else:s.result_cache.put(P+'&page=2',[later])
    self.assertIsNone(s.result_cache.get(P));self.assertEqual([x['title'] for x in s.rows[0]],['Public title'])
    s.show_row_window(1,0);s.show_row_window(0,0)
    self.assertEqual([x['title'] for x in s.rows[0]],['Second','Public title'])
    self.assertEqual(controls[900].pos,1);self.assertEqual(calls,[P])
 def test_deferred_revisit_anchors_the_title_selected_after_hydration(self):
  from row_feedback import RowResultCache
  with tempfile.TemporaryDirectory() as folder:
   other=dict(ITEM,file=ITEM['file'].replace('42','43'),title='Other');later=dict(ITEM,file=ITEM['file'].replace('42','44'),title='New')
   s,calls,controls,queue=self.state(folder,lambda path:[later,ITEM,other]);now=[1000.];s.result_cache=RowResultCache(clock=lambda:now[0])
   s.snapshot_cache.put(P,[ITEM,other]);s.set_rows([{'label':'Public','path':P},{'label':'Local','path':'','local_items':[{'file':'local'}]},{'label':'Third','path':'','local_items':[{'file':'third'}]}]);queue.pop(0)()
   controls[900].selectItem(1);now[0]+=121;s.show_row_window(1,0);s.show_row_window(0,0)
   self.assertEqual([x['title'] for x in s.rows[0]],['New','Public title','Other']);self.assertEqual(controls[900].pos,2)
 def test_native_card_replaced_during_lookup_cannot_receive_previous_title_watch_state(self):
  from native_list_fixture import NativeItem
  with tempfile.TemporaryDirectory() as folder:
   s,calls,controls,queue=self.state(folder,lambda path:[ITEM]);s.set_rows([{'label':'Public','path':P}])
   replacement=NativeItem('New card','new-path')
   def changed(position):
    controls[900].items=[replacement]
    return replacement
   controls[900].getListItem=changed
   queue.pop(0)()
   self.assertEqual(replacement.properties,{});self.assertEqual(replacement.info,{})
   self.assertNotIn('playcount',s.rows[0][0]);self.assertTrue(s.snapshot_rows[0])
 def test_navigation_during_native_lookup_rejects_old_hydration_flags_and_hero(self):
  from native_list_fixture import NativeItem
  with tempfile.TemporaryDirectory() as folder:
   s,calls,controls,queue=self.state(folder,lambda path:[ITEM]);s.set_rows([{'label':'Public','path':P}])
   old=controls[900].items[0];new={'file':'new-path','title':'New row'};new_card=NativeItem('New row','new-path');updates=[];s.update=updates.append
   def navigate(position):
    s.rows[0]=[new];s.paths[0]='new-row';s.generation+=1;s.snapshot_rows[0]=True
    controls[900].items=[new_card]
    return old
   controls[900].getListItem=navigate
   queue.pop(0)()
   self.assertEqual(s.rows[0],[new]);self.assertEqual(new_card.properties,{})
   self.assertTrue(s.snapshot_rows[0]);self.assertEqual(updates,[])
 def test_hydration_clears_old_resume_and_uses_unknown_for_absent_watch_fields(self):
  with tempfile.TemporaryDirectory() as folder:
   s,calls,controls,queue=self.state(folder,lambda path:[ITEM]);s.set_rows([{'label':'Public','path':P}]);queue.pop(0)()
   card=controls[900].items[0]
   s.apply_refreshed_row(0,[dict(ITEM,playcount=1,resume={})],'Public')
   self.assertIs(controls[900].items[0],card);self.assertEqual(card.resume,(0.,0.))
   self.assertEqual(card.properties['watchState'],'watched');self.assertEqual(card.properties['watchPercent'],'100')
   s.apply_refreshed_row(0,[{'file':ITEM['file'],'title':'Changed public title'}],'Public')
   self.assertEqual(card.resume,(0.,0.));self.assertEqual(card.info['playcount'],0)
   self.assertEqual(card.properties['watchState'],'unknown');self.assertEqual(card.properties['watchPercent'],'0');self.assertEqual(card.properties['watchLabel'],'')
   self.assertNotIn('resume',s.rows[0][0]);self.assertNotIn('playcount',s.rows[0][0]);self.assertEqual(s.rows[0][0]['title'],'Public title')
 def test_lookup_with_replaced_row_of_same_path_cannot_mark_or_update_new_owner(self):
  with tempfile.TemporaryDirectory() as folder:
   s,calls,controls,queue=self.state(folder,lambda path:[ITEM]);s.set_rows([{'label':'Public','path':P}])
   old=controls[900].items[0];new=[dict(s.rows[0][0])];updates=[];s.update=updates.append
   def changed(position):
    s.rows[0]=new
    return old
   controls[900].getListItem=changed;queue.pop(0)()
   self.assertEqual(old.properties['watchState'],'unknown');self.assertNotIn('playcount',new[0])
   self.assertTrue(s.snapshot_rows[0]);self.assertEqual(updates,[])
 def test_invalidation_during_native_metadata_update_does_not_mark_old_snapshot_or_update_hero(self):
  with tempfile.TemporaryDirectory() as folder:
   s,calls,controls,queue=self.state(folder,lambda path:[ITEM]);s.set_rows([{'label':'Public','path':P}])
   card=controls[900].items[0];original=card.setProperty;updates=[];s.update=updates.append
   def invalidated(key,value):
    original(key,value)
    if key=='watchState':s.invalidate_row_results()
   card.setProperty=invalidated;queue.pop(0)()
   self.assertTrue(s.snapshot_rows[0]);self.assertNotIn('playcount',s.rows[0][0]);self.assertEqual(updates,[])
   self.assertIsNone(s.snapshot_cache.get(P));self.assertIsNone(s.result_cache.get(P))
 def test_snapshot_refresh_failure_retains_cards_and_recoverable_error(self):
  def offline(path):raise OSError('offline')
  with tempfile.TemporaryDirectory() as folder:
   s,calls,controls,queue=self.state(folder,offline);s.set_rows([{'label':'Public','path':P}]);queue.pop(0)()
   self.assertEqual(s.rows[0][0]['title'],'Public title');self.assertEqual(s.row_states[0],'error')
   self.assertEqual(s.getProperty('rowState0'),'ready');self.assertIn('retry',s.getProperty('rowMessage0'))
 def test_invalidation_rejects_queued_and_running_refresh_in_ui_memory_and_disk(self):
  with tempfile.TemporaryDirectory() as folder:
   s,calls,controls,queue=self.state(folder,lambda path:[ITEM]);s.set_rows([{'label':'Public','path':P}]);s.invalidate_row_results();queue.pop(0)()
   self.assertEqual(calls,[]);self.assertIsNone(s.snapshot_cache.get(P))
  with tempfile.TemporaryDirectory() as folder:
   def provider(path):s.invalidate_row_results();return [dict(ITEM,title='Late result')]
   s,calls,controls,queue=self.state(folder,provider);s.set_rows([{'label':'Public','path':P}]);queue.pop(0)()
   self.assertEqual(s.rows[0][0]['title'],'Public title');self.assertIsNone(s.snapshot_cache.get(P));self.assertIsNone(s.result_cache.get(P))
 def test_cached_interactive_rows_render_while_provider_lock_is_busy(self):
  with tempfile.TemporaryDirectory() as folder:
   s,calls,controls,queue=self.state(folder,lambda path:[ITEM])
   s.result_cache.put(P,[ITEM]);s.list_lock.acquire()
   try:s.set_rows([{'label':'Public','path':P}]);self.assertEqual(s.rows[0],[ITEM]);self.assertEqual(calls,[])
   finally:s.list_lock.release()

class IdlePrefetch(unittest.TestCase):
 def state(self):
  from types import SimpleNamespace,MethodType
  import threading,time
  from row_feedback import RowResultCache
  queue=[];calls=[]
  class QueuedThread(fixture.SyncThread):
   def start(self):queue.append(self.target)
  ns=fixture.methods(['prefetch_next_row'],{'time':time,'public_path':__import__('public_rows').public_path,'threading':SimpleNamespace(Thread=QueuedThread),'xbmcgui':SimpleNamespace(getCurrentWindowDialogId=lambda:s.dialog_id),'event':lambda *a,**kw:None})
  s=SimpleNamespace(dialog_id=0,alive=True,prefetch_trial=True,prefetch_busy=False,prefetch_attempted=set(),window_ready=[True,True],row_window_busy=False,settings_open=False,actions_open=False,owned_preview=False,preview_mode='manual',mode='home',search_state=None,episode_browser_context=None,discovery_stack=[],dwell=time.monotonic()-5,generation=1,row_offset=0,page_definitions=[{'path':P},{'path':P},{'path':P+'&page=2','label':'Next'}],result_cache=RowResultCache(),list_lock=threading.Lock(),player=SimpleNamespace(isPlaying=lambda:False),getProperty=lambda k:'',getFocusId=lambda:900,cached_row_items=lambda definition,**kw:calls.append(definition['path']))
  s.prefetch_next_row=MethodType(ns['prefetch_next_row'],s)
  return s,calls,queue
 def test_prefetch_is_explicit_one_next_public_row_and_provider_lock_is_nonblocking(self):
  s,calls,queue=self.state();s.prefetch_trial=False;s.prefetch_next_row();self.assertEqual(queue,[])
  s.prefetch_trial=True;s.prefetch_next_row();self.assertEqual(calls,[]);queue.pop(0)();s.prefetch_next_row()
  self.assertEqual(calls,[P+'&page=2']);self.assertEqual(queue,[])
  s,calls,queue=self.state();s.list_lock.acquire()
  try:s.prefetch_next_row();queue.pop(0)();self.assertEqual(calls,[])
  finally:s.list_lock.release()
 def test_prefetch_yields_to_visible_refresh_preview_playback_and_dialogs(self):
  for key,value in [('window_ready',[True,False]),('row_window_busy',True),('owned_preview',True),('preview_mode','auto'),('actions_open',True),('settings_open',True),('search_state',{'query':'private'}),('prefetch_busy',True)]:
   s,calls,queue=self.state();setattr(s,key,value);s.prefetch_next_row();self.assertEqual(queue,[],key)
  s,calls,queue=self.state();s.dialog_id=12000;s.prefetch_next_row();self.assertEqual(queue,[])
  s,calls,queue=self.state();s.player.isPlaying=lambda:True;s.prefetch_next_row();self.assertEqual(queue,[])
  s,calls,queue=self.state();s.page_definitions[2]['path']=P.replace('popular','trakt_watchlist');s.prefetch_next_row();self.assertEqual(queue,[])
 def test_prefetch_rechecks_generation_and_activity_before_provider(self):
  s,calls,queue=self.state();s.prefetch_next_row();s.generation+=1;queue.pop(0)();self.assertEqual(calls,[])
  s,calls,queue=self.state();s.prefetch_next_row();s.owned_preview=True;queue.pop(0)();self.assertEqual(calls,[])

class SnapshotReturn(unittest.TestCase):
 def test_returning_to_snapshot_row_restarts_cancelled_refresh(self):
  with tempfile.TemporaryDirectory() as folder:
   s,calls,controls,queue=SnapshotController().state(folder,lambda path:[ITEM])
   s.set_rows([{'label':'Public','path':P},{'label':'Other','path':'other'},{'label':'Third','path':'third'}])
   s.show_row_window(1,0);s.show_row_window(0,0)
   queue[-1]()
   self.assertIn(P,calls,'Returning to a retained disk snapshot must refresh rather than remain unknown for the session')
   self.assertEqual(s.rows[0][0]['playcount'],1)

class InvalidationBoundary(unittest.TestCase):
 def test_worker_revision_is_checked_again_at_provider_entry(self):
  with tempfile.TemporaryDirectory() as folder:
   s,calls,controls,queue=SnapshotController().state(folder,lambda path:[ITEM])
   old=s.result_cache.revision;s.invalidate_row_results()
   # Invalidation can happen between the worker's first check and provider entry.
   self.assertEqual(s.cached_row_items({'path':P},expected_revision=old),[])
   self.assertEqual(calls,[]);self.assertIsNone(s.snapshot_cache.get(P))
