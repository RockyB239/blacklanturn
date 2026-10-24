import copy,tempfile,unittest,time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import youtube_browser as browser,youtube_saved_runtime as runtime
from youtube_browser import YouTubeBrowser
from youtube_core import tab_rows
from youtube_saved import SavedRows
from test_youtube_saved import item,row

class Window(YouTubeBrowser):
 def __init__(self,path):
  self.store=SavedRows(path,'one');self.history=path.with_name('missing.sqlite');self.alive=True;self.window_lifetime=object();self.generation=1
  self.youtube_connection=SimpleNamespace(connected=True,identity='one');self.section='YouTube';self.youtube_tab='home';self.mode='home';self.discovery_stack=[]
  self.config={};self.properties={};self.refreshed=0;self.row_window_busy=False;self.paths=[d['path'] for d in tab_rows('home')]
 def saved_youtube_context(self):return self.store,self.history,True
 def setProperty(self,k,v):self.properties[k]=v
 def populate_youtube_tabs(self):pass
 def set_rows(self,rows):self.page_definitions=rows
 def stop_preview(self):pass
 def refresh_youtube_recommendations(self):self.refreshed+=1
 def youtube_home_visible(self):return self.section=='YouTube' and self.youtube_tab=='home'

class Integration(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.w=Window(Path(self.tmp.name)/'rows.json')
 def save(self):
  self.w.store.put(row());self.w.store.put(dict(row(),path=tab_rows('home')[1]['path'],label='Subscriptions'))
  self.w.store.put(dict(row(),path=row()['path']+'?bl_shelf=adaptive',label='Adaptive',youtube_category=True))
 def test_fresh_process_reuses_primary_rows_and_art_without_provider_or_extra_worker(self):
  self.save();self.w.store=SavedRows(self.w.store.path,'one')
  with patch.object(browser,'load_home_rows',side_effect=AssertionError('Unexpected provider fetch')):
   self.w.load_youtube_section();self.w.maybe_refresh_saved_youtube()
  self.assertTrue(self.w.page_definitions[0]['_youtube_saved']);self.assertEqual(self.w.page_definitions[0]['local_items'][0]['art'],item()['art']);self.assertEqual(self.w.refreshed,0)
 def test_saved_values_get_current_history_before_they_can_be_rendered(self):
  self.save();self.w.load_youtube_section();definition=self.w.page_definitions[0]
  values=self.w.resolve_saved_youtube_row(definition,lambda:True)
  self.assertEqual(values[0]['playcount'],0);self.assertEqual(values[0]['resume']['position'],0);self.assertEqual(definition['youtube_cursor'],row()['youtube_cursor'])
 def test_overdue_recommendations_refresh_once_after_rows_are_usable(self):
  self.w.store.clock=lambda:time.time()-301;self.save();self.w.store.clock=time.time
  self.w.load_youtube_section();self.w.row_window_busy=True;self.w.maybe_refresh_saved_youtube();self.assertEqual(self.w.refreshed,0)
  self.w.row_window_busy=False;self.w.maybe_refresh_saved_youtube();self.w.maybe_refresh_saved_youtube();self.assertEqual(self.w.refreshed,1)
 def test_primary_only_snapshot_still_finishes_adaptive_categories_in_background(self):
  self.w.store.put(row());self.w.store.put(dict(row(),path=tab_rows('home')[1]['path'],label='Subscriptions'))
  self.w.load_youtube_section();self.w.maybe_refresh_saved_youtube();self.assertEqual(self.w.refreshed,1)
 def test_unknown_history_uses_provider_watch_overlay_without_relabeling_categories_or_replacing_cursor(self):
  self.save();self.w.load_youtube_section()
  definition=dict(self.w.page_definitions[0],youtube_category=True);before=copy.deepcopy(definition)
  with patch.object(runtime,'current_watch',side_effect=runtime.HistoryUnavailable()),patch.object(runtime,'provider_watch',return_value=[dict(item(),playcount=1)]) as fetch:
   self.assertEqual(self.w.resolve_saved_youtube_row(definition,lambda:True)[0]['playcount'],1)
   self.assertEqual(fetch.call_args.args[0],definition['local_items']);self.assertEqual(definition,before)
 def test_native_content_preferences_each_change_snapshot_scope(self):
  from types import SimpleNamespace
  values={};addon=SimpleNamespace(getAddonInfo=lambda k:'1:7.4.4+blacklanturn.1',getSetting=lambda k:values.get(k,''))
  original=runtime.saved_scope('account',addon)
  for key in ('kodion.content.max_per_page','kodion.safe.search','youtube.view.hide_videos','youtube.view.filter.list','youtube.folder.my_subscriptions.sources'):
   values.clear();values[key]='changed';self.assertNotEqual(runtime.saved_scope('account',addon),original,key)
 def test_unproven_account_cannot_fall_back_to_general_feed_under_category_label(self):
  from test_window_lifecycle import extract,ROOT
  class Cancelled(RuntimeError):pass
  w=SimpleNamespace(section='YouTube',resolve_saved_youtube_row=lambda *a:None,youtube_saved_guard=lambda guard:guard)
  def provider(*a):self.fail('Unproven saved category cannot fetch general recommendations')
  method=extract(ROOT/'live_review.py','cached_row_items',{'get_list':provider,'row_items':lambda d,p:p(d['path']),'PageCancelled':Cancelled},'LiveReview')
  with self.assertRaises(Cancelled):method(w,dict(row(),_youtube_saved=True,youtube_category=True))
 def test_settings_change_after_selection_rejects_old_saved_definitions(self):
  self.save();self.w.load_youtube_section();old=self.w.page_definitions[0];self.w.store=SavedRows(self.w.store.path,'changed-settings')
  self.assertIsNone(self.w.resolve_saved_youtube_row(old,lambda:True))
 def test_settings_change_during_fetch_retires_writer_and_cannot_renew_snapshot(self):
  self.save();guard=self.w.youtube_saved_guard(lambda:True);self.w.store=SavedRows(self.w.store.path.with_name('changed.json'),'changed-settings')
  self.assertFalse(guard());self.w.remember_fetched_youtube_row(row(),[item(2)],guard);self.w.remember_youtube_shelves([row(),dict(row(),youtube_category=True)],guard)
  self.assertEqual(self.w.store.get(),[]);self.assertFalse(self.w.store.path.exists())
 def test_late_or_other_account_work_cannot_read_or_save_rows(self):
  self.save();raw=self.w.store.path.read_bytes();self.assertIsNone(self.w.resolve_saved_youtube_row(dict(row(),_youtube_saved=True),lambda:False))
  self.w.remember_fetched_youtube_row(row(),[item(2)],lambda:False);self.assertEqual(self.w.store.path.read_bytes(),raw)
 def test_new_categories_replace_retired_categories_but_keep_primary_rows(self):
  self.save();self.w.remember_youtube_shelves([row(),dict(row(),path=row()['path']+'?bl_shelf=old',label='Old',youtube_category=True)])
  self.w.remember_youtube_shelves([row(),dict(row(),path=row()['path']+'?bl_shelf=new',label='New',youtube_category=True)])
  labels=[r['label'] for r in self.w.store.get()];self.assertIn('Subscriptions',labels);self.assertIn('New',labels);self.assertNotIn('Old',labels)
 def test_refresh_updates_reuse_age_but_read_does_not(self):
  self.save();self.w.load_youtube_section();before=self.w.store.path.read_bytes();self.w.resolve_saved_youtube_row(self.w.page_definitions[0],lambda:True);self.assertEqual(before,self.w.store.path.read_bytes())
  self.w.remember_fetched_youtube_row(row(),[item(2)],lambda:True);fresh=next(r for r in self.w.store.get() if r['path']==row()['path']);self.assertEqual(fresh['local_items'][0]['file'],item(2)['file'])
 def test_account_switch_during_context_read_cannot_store_old_shelves_under_new_account(self):
  self.save();other=SavedRows(self.w.store.path.with_name('other.json'),'two');valid=[True]
  def switched():valid[0]=False;return other,self.w.history,True
  self.w.saved_youtube_context=switched
  self.w.remember_youtube_shelves([row(),dict(row(),path=row()['path']+'?bl_shelf=private',youtube_category=True)],lambda:valid[0])
  self.assertEqual(other.get(),[]);self.assertFalse(other.path.exists())
