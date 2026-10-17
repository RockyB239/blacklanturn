"""Review regressions: real native-method interleavings, no deployed Kodi access."""
import copy,json,sys,tempfile,time,unittest
from pathlib import Path
from types import MethodType,SimpleNamespace
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
import test_discovery_controller as fixture
import test_snapshot_controller as snapshot_fixture
from test_public_row_snapshots import P,ITEM
from live_core import valid_source,PageHistory,card_artwork,title_presentation,show_identity,title_details_params
from playback_core import restored_position,refreshed_watch_item,item_key,trakt_command
from search_ui import search_sources
from row_feedback import provider_page_label,row_message

class ControllerReview(unittest.TestCase):
 def state(self,folder,provider):
  s,calls,controls,queue=snapshot_fixture.SnapshotController().state(folder,provider)
  class Thread(fixture.SyncThread):
   def start(self):queue.append(self.target)
  ns=dict(copy=copy,json=json,time=time,STORE=Path(folder),valid_source=valid_source,PageHistory=PageHistory,
          provider_page_label=provider_page_label,row_message=row_message,show_identity=show_identity,search_sources=search_sources,
          restored_position=restored_position,refreshed_watch_item=refreshed_watch_item,item_key=item_key,trakt_command=trakt_command,title_details_params=title_details_params,
          tmdb=lambda info,kind,**kw:'plugin://plugin.video.themoviedb.helper/?info='+info+'&tmdb_type='+kind+'&tmdb_id='+kw.get('tmdb_id',''),threading=SimpleNamespace(Thread=Thread),
          get_list=lambda path:calls.append(path) or provider(path),event=lambda *a,**kw:None)
  names=['save','load_path','capture_browse','restore_browse','open_discovery','browse_all_episodes','restore_episode_browser','open_search','select_search','refresh_watch_status']
  ns=fixture.methods(names,ns)
  for name in names:setattr(s,name,MethodType(ns[name],s))
  for control in controls.values():control.setHeight=lambda value:None
  s.actions_open=False;s.section='Home';s.navigation_id='home';s.return_focus=900;s.last_row=0;s.person_context=None;s.active_page=None
  s.season_sources=[];s.season_title='';s.season_position=0;s.search_state=None;s.search_origin=None;s.discovery_stack=[]
  s.refresh_navigation=lambda:None;s.load_browse_sources=lambda:None;s.populate_seasons=lambda:None;s.populate_search=lambda:None
  s.update=lambda item:setattr(s,'selected',item)
  return s,calls,controls,queue
 def drain(self,queue):
  for _ in range(20):
   if not queue:return
   queue.pop(0)()
  self.fail('Visible requests did not settle')
 def test_save_before_pending_snapshot_worker_restarts_both_visible_rows_and_preserves_focus(self):
  with tempfile.TemporaryDirectory() as folder:
   s,calls,controls,queue=self.state(folder,lambda path:[dict(ITEM,title=path)])
   s.set_rows([{'label':'Public','path':P},{'label':'Second','path':P+'&page=2'}]);s.focus=105;s.save();queue.pop(0)();self.assertTrue(s.row_window_busy);self.drain(queue)
   self.assertTrue(all(s.window_ready));self.assertNotEqual(s.getProperty('rowState1'),'loading')
   self.assertEqual(s.rows[0][0]['playcount'],1);self.assertEqual(s.focus,105)
 def test_save_during_provider_request_restarts_pending_rows_and_rejects_old_commit(self):
  with tempfile.TemporaryDirectory() as folder:
   saved=[False]
   def provider(path):
    if not saved[0]:saved[0]=True;s.save();return [dict(ITEM,title='Obsolete')]
    return [dict(ITEM,title='Fresh')]
   s,calls,controls,queue=self.state(folder,provider)
   s.set_rows([{'label':'Public','path':P},{'label':'Second','path':P+'&page=2'}]);s.focus=105;self.drain(queue)
   self.assertTrue(all(s.window_ready));self.assertEqual(s.rows[0][0]['title'],'Public title');self.assertEqual(s.rows[0][0]['playcount'],1);self.assertEqual(s.result_cache.get(P)[0]['title'],'Fresh');self.assertEqual(s.focus,105)
 def test_completed_load_path_cannot_be_overwritten_by_old_snapshot_refresh(self):
  with tempfile.TemporaryDirectory() as folder:
   page2=P+'&page=2'
   def provider(path):
    if path==P:
     s.load_path(0,page2,'Page two');queue.pop()()
     return [dict(ITEM,title='Old page one')]
    return [dict(ITEM,title='Current page two')]
   s,calls,controls,queue=self.state(folder,provider)
   s.set_rows([{'label':'Public','path':P}]);self.drain(queue)
   self.assertEqual(s.paths[0],page2);self.assertEqual(s.rows[0][0]['_page_control'],'previous');self.assertEqual(s.rows[0][1]['title'],'Current page two')
   self.assertFalse(s.snapshot_rows.get(0,False))
 def test_capture_restore_restarts_snapshot_and_unfinished_visible_row(self):
  for destination in ('discovery','settings','search'):
   with self.subTest(destination=destination),tempfile.TemporaryDirectory() as folder:
    s,calls,controls,queue=self.state(folder,lambda path:[dict(ITEM,title='Fresh')])
    s.set_rows([{'label':'Public','path':P},{'label':'Second','path':P+'&page=2'}]);s.focus=105
    if destination=='discovery':
     s.open_discovery({'heading':'Explore','rows':[{'label':'Explore','path':'other'}]});state=s.discovery_stack.pop()
    elif destination=='search':s.open_search('Public query');state=s.search_origin
    else:state=s.capture_browse();s.generation+=1
    self.assertTrue(state.get('snapshot_rows',{}).get(0),'Snapshot provenance must survive capture')
    s.restore_browse(state);self.drain(queue)
    self.assertEqual(s.rows[0][0]['playcount'],1);self.assertTrue(all(s.window_ready));self.assertEqual(s.focus,105)

 def test_episode_browser_return_restarts_origin_snapshot_refresh(self):
  with tempfile.TemporaryDirectory() as folder:
   tv_item=dict(ITEM,file=ITEM['file'].replace('tmdb_type=movie','tmdb_type=tv'))
   s,calls,controls,queue=self.state(folder,lambda path:[tv_item]);s.snapshot_cache.put(P,[tv_item])
   s.set_rows([{'label':'Shows','path':P},{'label':'Second','path':P+'&page=2'}])
   s.browse_all_episodes();self.assertTrue(s.episode_browser_context.get('snapshot_rows',{}).get(0))
   s.restore_episode_browser();self.drain(queue)
   self.assertEqual(s.rows[0][0]['playcount'],1);self.assertTrue(all(s.window_ready));self.assertFalse(s.snapshot_rows[0])
 def test_capture_restore_keeps_deferred_reorder_until_explicit_row_revisit(self):
  from row_feedback import RowResultCache
  with tempfile.TemporaryDirectory() as folder:
   later=dict(ITEM,file=ITEM['file'].replace('42','43'),title='Second');now=[1000.]
   s,calls,controls,queue=self.state(folder,lambda path:[later,ITEM]);s.result_cache=RowResultCache(clock=lambda:now[0])
   definitions=[{'label':'Public','path':P},{'label':'Local','path':'','local_items':[{'file':'local'}]},{'label':'Third','path':'','local_items':[{'file':'third'}]}]
   s.set_rows(definitions);self.drain(queue);state=s.capture_browse();s.set_rows([{'label':'Other context','path':'','local_items':[{'file':'other'}]}]);self.drain(queue)
   s.restore_browse(state);self.assertEqual([x['title'] for x in s.rows[0]],['Public title'])
   now[0]+=121;s.show_row_window(1,0);s.show_row_window(0,0)
   self.assertEqual([x['title'] for x in s.rows[0]],['Second','Public title']);self.assertEqual(controls[900].pos,1);self.assertEqual(calls,[P])
 def test_save_invalidates_deferred_layout_even_inside_captured_context(self):
  with tempfile.TemporaryDirectory() as folder:
   later=dict(ITEM,file=ITEM['file'].replace('42','43'),title='Old account result')
   s,calls,controls,queue=self.state(folder,lambda path:[later,ITEM])
   definitions=[{'label':'Public','path':P},{'label':'Local','path':'','local_items':[{'file':'local'}]},{'label':'Third','path':'','local_items':[{'file':'third'}]}]
   s.set_rows(definitions);self.drain(queue);state=s.capture_browse();s.save()
   s.restore_browse(state);s.show_row_window(1,0);s.show_row_window(0,0)
   self.assertEqual([x['title'] for x in s.rows[0]],['Public title'],'Old deferred provider membership must not survive cache invalidation through a saved context')
 def test_new_row_context_cannot_adopt_previous_context_deferred_layout(self):
  with tempfile.TemporaryDirectory() as folder:
   later=dict(ITEM,file=ITEM['file'].replace('42','43'),title='Previous row')
   s,calls,controls,queue=self.state(folder,lambda path:[later,ITEM]);s.set_rows([{'label':'Public','path':P}]);self.drain(queue)
   s.set_rows([{'label':'Different context','path':'','local_items':[{'file':'local','title':'New row'}]},{'label':'Second','path':'','local_items':[{'file':'second'}]},{'label':'Third','path':'','local_items':[{'file':'third'}]}]);self.drain(queue)
   s.show_row_window(1,0);s.show_row_window(0,0)
   self.assertEqual([x['title'] for x in s.rows[0]],['New row'])
 def test_deferred_rows_share_the_existing_eight_row_payload_retention_budget(self):
  with tempfile.TemporaryDirectory() as folder:
   s,calls,controls,queue=self.state(folder,lambda path:[ITEM]);definitions=[{'label':str(n),'path':P+'&page='+str(n+1)} for n in range(12)]
   for definition in definitions:s.snapshot_cache.put(definition['path'],[ITEM])
   s.set_rows(definitions);self.drain(queue)
   for offset in range(1,11):
    s.show_row_window(offset,0);self.drain(queue)
    self.assertLessEqual(sum(entry.get('files') is not None for entry in s.row_cache.values()),8)
   self.assertIsNone(s.row_cache[0]['files'],'Far-away deferred payload must be evicted by the normal row window budget')
 def test_explicit_provider_page_return_replaces_previous_deferred_response(self):
  for latest in ([dict(ITEM,title='Latest explicit response',playcount=3,resume={'position':60,'total':100})],[]):
   with self.subTest(empty=not latest),tempfile.TemporaryDirectory() as folder:
    response=[dict(ITEM,title='Old deferred response',playcount=1)]
    s,calls,controls,queue=self.state(folder,lambda path:response)
    definitions=[{'label':'Public','path':P},{'label':'Local','path':'','local_items':[{'file':'local'}]},{'label':'Third','path':'','local_items':[{'file':'third'}]}]
    s.set_rows(definitions);self.drain(queue)
    s.load_path(0,P+'&page=2','Page two');self.drain(queue)
    response=latest;s.histories[0].pop();s.load_path(0,P,'Public',back=True);self.drain(queue)
    self.assertEqual(s.rows[0],latest)
    s.show_row_window(1,0);s.show_row_window(0,0)
    self.assertEqual(s.rows[0],latest,'Explicit latest provider response must win over old deferred/session responses')
    if latest:self.assertEqual(controls[900].items[0].info['playcount'],3);self.assertEqual(controls[900].items[0].resume,(60.,100.))
 def test_watch_refresh_cancels_older_snapshot_without_republishing_it(self):
  with tempfile.TemporaryDirectory() as folder:
   started=[False]
   def provider(path):
    if not started[0]:
     started[0]=True;s.refresh_watch_status();return [dict(ITEM,title='Obsolete snapshot response')]
    return [dict(ITEM,title='Fresh watched response',playcount=3)]
   s,calls,controls,queue=self.state(folder,provider)
   s.set_rows([{'label':'Public','path':P},{'label':'Second','path':P+'&page=2'}]);self.drain(queue)
   self.assertEqual(s.rows[0][0]['playcount'],3);self.assertEqual(s.rows[0][0]['title'],'Fresh watched response')
   self.assertIsNone(s.snapshot_cache.get(P));self.assertIsNone(s.result_cache.get(P));self.assertFalse(s.actions_open);self.assertFalse(s.row_window_busy)

 def test_pending_local_saved_row_restarts_after_capture_restore_without_provider(self):
  for destination in ('settings','search'):
   with self.subTest(destination=destination),tempfile.TemporaryDirectory() as folder:
    s,calls,controls,queue=self.state(folder,lambda path:self.fail('Local Saved restart must not call a provider'))
    saved=[dict(ITEM,title='Saved locally',resume={'position':30,'total':100})]
    s.section='My Stuff';s.set_rows([{'label':'Saved on this device','path':'','local_items':saved}])
    if destination=='search':s.open_search('Public query');state=s.search_origin
    else:state=s.capture_browse();s.generation+=1
    s.restore_browse(state);self.drain(queue)
    self.assertTrue(all(s.window_ready));self.assertEqual(s.rows[0],saved);self.assertEqual(calls,[])
    self.assertEqual(s.getProperty('rowState0'),'ready')
 def test_save_during_new_section_load_keeps_new_heading_instead_of_previous_slot_label(self):
  with tempfile.TemporaryDirectory() as folder:
   s,calls,controls,queue=self.state(folder,lambda path:[dict(ITEM,title=path)])
   s.set_rows([{'label':'Previous section heading','path':'old-section'}]);self.drain(queue)
   s.set_rows([{'label':'Current section heading','path':'new-section'}]);s.save();self.drain(queue)
   self.assertEqual(s.rows[0][0]['title'],'new-section')
   self.assertEqual(s.row_labels[0],'Current section heading');self.assertEqual(s.getProperty('row0'),'Current section heading')

 def test_snapshot_refresh_does_not_restore_stale_focus_or_update_hero_after_lookup_sidebar_move(self):
  with tempfile.TemporaryDirectory() as folder:
   s,calls,controls,queue=self.state(folder,lambda path:[dict(ITEM,title='Fresh title')])
   s.set_rows([{'label':'Public','path':P}]);s.focus=900
   updates=[];s.update=updates.append
   original_get=controls[900].getListItem
   def native_lookup_with_sidebar_move(position):
    s.focus=50
    return original_get(position)
   controls[900].getListItem=native_lookup_with_sidebar_move
   focus_calls=[];s.setFocusId=lambda cid:(focus_calls.append(cid),setattr(s,'focus',cid))
   self.drain(queue)
   self.assertEqual(s.focus,50);self.assertEqual(focus_calls,[],'Background snapshot work must never set native focus')
   self.assertEqual(updates,[],'Sidebar movement must not receive an outdated row hero update')
   self.assertEqual(s.rows[0][0]['title'],'Public title');self.assertEqual(s.rows[0][0]['playcount'],1)
 def test_snapshot_hero_update_uses_current_card_after_lookup_shelf_move(self):
  with tempfile.TemporaryDirectory() as folder:
   other=dict(ITEM,file=ITEM['file'].replace('42','43'),title='Other title')
   s,calls,controls,queue=self.state(folder,lambda path:[ITEM,other])
   s.snapshot_cache.put(P,[ITEM,other]);s.set_rows([{'label':'Public','path':P}]);s.focus=105
   original_get=controls[900].getListItem
   def native_lookup_with_row_move(position):
    controls[900].selectItem(1);s.focus=900
    return original_get(position)
   controls[900].getListItem=native_lookup_with_row_move
   updates=[];s.update=updates.append
   self.drain(queue)
   self.assertEqual(s.focus,900);self.assertEqual(updates[-1]['title'],'Other title')

class MalformedSnapshotReview(unittest.TestCase):
 def load(self,folder,item=ITEM,stamp=1000):
  from public_rows import PublicRowSnapshots
  path=Path(folder)/'bad.json';path.write_text(json.dumps({'version':1,'scope':'a','rows':[{'path':P,'time':stamp,'items':[item]}]}))
  return PublicRowSnapshots(path,'a',clock=lambda:1000).get(P)
 def test_malformed_rendering_fields_are_rejected_before_real_card_helpers(self):
  for field,value in [('episode','broken'),('season',{}),('title',99),('year','broken'),('runtime',10**1000),('rating',float('nan')),('art',[]),('uniqueid',[]),('plot',{'private':'object'})]:
   with self.subTest(field=field),tempfile.TemporaryDirectory() as folder:
    files=self.load(folder,dict(ITEM,**{field:value}))
    if files:
     card_artwork(files[0]);title_presentation(files[0])
    self.assertIsNone(files,'Malformed typed field must miss safely')
 def test_unrepresentable_or_nonfinite_timestamps_miss_safely(self):
  for stamp in (10**1000,float('nan'),float('inf'),True,'1000',{},[]):
   with self.subTest(kind=type(stamp).__name__),tempfile.TemporaryDirectory() as folder:
    self.assertIsNone(self.load(folder,stamp=stamp))
