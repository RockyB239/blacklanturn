"""User navigation owns the view while an explicit provider refresh is pending."""
import sys, threading, unittest
from types import SimpleNamespace
from unittest.mock import patch
from test_window_lifecycle import ROOT, extract
from playback_core import restored_position, item_key
from browse_controls import page_cards, page_card
from live_core import PageHistory
from row_feedback import row_message

class Control:
 def __init__(self,items,position=0):self.items=list(items);self.position=position
 def getSelectedPosition(self):return self.position
 def reset(self):self.items=[]
 def addItems(self,items):self.items.extend(items)
 def selectItem(self,p):self.position=p
 def setVisible(self,*args):pass

class PanelRefreshOwnership(unittest.TestCase):
 def state(self,related=False,previous=False,filtered=False):
  a={'file':'plugin://x/a','title':'A'};b={'file':'plugin://x/b','title':'B'};c={'file':'plugin://x/c','title':'C'}
  raw=[a,b,c];shown=[b,c] if filtered else raw
  history=PageHistory()
  if previous:history.pages=[('plugin://x/page1',0)];shown=[page_card('previous','blacklanturn://previous-page')]+shown
  controls={900:Control(shown,shown.index(b)),3100:Control(shown,shown.index(b))};focus=3100 if related else 900;events=[];jobs=[]
  w=SimpleNamespace(alive=True,window_lifetime=object(),generation=3,input_generation=7,preview_generation=2,
   paths=['plugin://x/page2',''],rows=[list(shown),[]],selected=b,last_row=0,mode='details' if related else 'home',
   related_path='plugin://x/related',related=list(shown),related_history=history,related_owner=object(),related_request=object(),
   row_offset=0,row_cache={0:'old'},row_labels={0:'Titles'},histories=[history,PageHistory()],window_ready=[True,True],
   section='Movies',row_states={},episode_browser_context=None,preview_dispatch_lock=threading.RLock(),actions_open=False,
   getFocusId=lambda:focus,getControl=lambda cid:controls[cid],setFocusId=lambda cid:events.append(('focus',cid)),
   setProperty=lambda *a:events.append(a),finish_loading=lambda *a:None,row_navigation=lambda:None,
   stop_preview=lambda:None,update=lambda item:events.append(('update',item)),title_preferences=SimpleNamespace(apply=lambda f:[x for x in f if x['title']!='A']) if filtered else None)
  if filtered:w.prepare_title_row=lambda n,f:[x for x in f if x['title']!='A']
  class Deferred:
   def __init__(self,target,**kw):self.target=target
   def start(self):jobs.append(self.target)
  ns={'threading':SimpleNamespace(Thread=Deferred),'get_list':lambda p:raw,'valid_source':lambda p:True,
   'provider_path':lambda p:p,'restored_position':restored_position,'item_key':item_key,'page_cards':page_cards,'row_message':row_message,'media_item':lambda x,**kw:x}
  apply=extract(ROOT/'live_review.py','apply_row',ns,'LiveReview');w.apply_row=lambda *a,**kw:apply(w,*a,**kw)
  method=extract(ROOT/'live_review.py','refresh_panel_list',ns,'LiveReview');w.refresh_panel_list=lambda *a,**kw:method(w,*a,**kw)
  return w,controls,events,jobs,ns,raw
 def test_list_refresh_keeps_anchor_after_previous_card_is_inserted(self):
  w,c,e,j,ns,raw=self.state(previous=True);w.refresh_panel_list();j.pop()()
  self.assertIn(('notice','List refreshed'),e);self.assertEqual(c[900].items[c[900].position]['title'],'B')
 def test_list_refresh_keeps_anchor_after_title_filtering(self):
  w,c,e,j,ns,raw=self.state(filtered=True);w.refresh_panel_list();j.pop()()
  self.assertIn(('notice','List refreshed'),e);self.assertEqual(c[900].items[c[900].position]['title'],'B')
 def test_related_refresh_keeps_anchor_after_previous_card(self):
  w,c,e,j,ns,raw=self.state(related=True,previous=True);w.refresh_panel_list();j.pop()()
  self.assertIn(('notice','List refreshed'),e);self.assertEqual(c[3100].items[c[3100].position]['title'],'B')
 def test_related_refresh_keeps_anchor_after_title_filtering(self):
  w,c,e,j,ns,raw=self.state(related=True,filtered=True);w.refresh_panel_list();j.pop()()
  self.assertIn(('notice','List refreshed'),e);self.assertEqual(c[3100].items[c[3100].position]['title'],'B')
 def test_pending_refresh_leaves_back_available_and_discards_after_input(self):
  w,c,e,j,ns,raw=self.state();w.refresh_panel_list();self.assertFalse(w.actions_open)
  before=list(c[900].items);w.input_generation+=1;j.pop()()
  self.assertEqual(c[900].items,before);self.assertFalse(any(x[0]=='focus' for x in e))
 def test_stale_worker_cannot_clear_new_lifetime_modal_or_focus(self):
  w,c,e,j,ns,raw=self.state();w.refresh_panel_list();w.generation+=1;w.window_lifetime=object();w.actions_open=True;w.dwell=123;w.focus_key='new'
  j.pop()();self.assertTrue(w.actions_open);self.assertEqual(w.dwell,123);self.assertEqual(w.focus_key,'new')
 def test_duplicate_refresh_and_metadata_share_one_pending_provider_worker(self):
  w,c,e,j,ns,raw=self.state();w.refresh_panel_list();w.refresh_panel_list()
  ns['title_details_params']=lambda i:{'tmdb_type':'movie','tmdb_id':'42'}
  extract(ROOT/'live_review.py','refresh_panel_metadata',ns,'LiveReview')(w,raw[1]);self.assertEqual(len(j),1)
 def test_replaced_row_owner_discards_pending_result(self):
  w,c,e,j,ns,raw=self.state();w.refresh_panel_list();w.paths[0]='plugin://x/new';w.rows[0]=[{'file':'new'}];e.clear();j.pop()()
  self.assertFalse(any(x[0] in ('focus','update','notice') for x in e))
 def test_failed_refresh_keeps_current_cards_and_selection(self):
  w,c,e,j,ns,raw=self.state(previous=True);before=list(c[900].items);position=c[900].position
  ns['get_list']=lambda p:(_ for _ in ()).throw(OSError('offline'));w.refresh_panel_list();j.pop()()
  self.assertEqual(c[900].items,before);self.assertEqual(c[900].position,position)
 def metadata(self,w,ns):
  ns.update(title_details_params=lambda i:{'tmdb_type':'movie','tmdb_id':'42'},tmdb=lambda *a,**k:'plugin://x/details',merge_title_details=lambda item,fresh:dict(item,title=fresh['title']))
  return extract(ROOT/'live_review.py','refresh_panel_metadata',ns,'LiveReview')
 def test_metadata_navigation_cancels_before_second_provider_request(self):
  w,c,e,j,ns,raw=self.state();fetch=[];ns['get_list']=lambda p:fetch.append(p) or [{'title':'fresh'}]
  run=self.metadata(w,ns);run(w,raw[1]);self.assertFalse(w.actions_open)
  def refresh(params):w.input_generation+=1
  with patch.dict(sys.modules,{'title_refresh':SimpleNamespace(refresh_title=refresh)}):j.pop()()
  self.assertEqual(fetch,[]);self.assertFalse(any(x[0]=='update' for x in e))
 def test_metadata_old_cleanup_cannot_unlock_reinitialized_modal(self):
  w,c,e,j,ns,raw=self.state();run=self.metadata(w,ns);run(w,raw[1])
  def refresh(params):w.window_lifetime=object();w.generation+=1;w.actions_open=True;w.dwell=123
  with patch.dict(sys.modules,{'title_refresh':SimpleNamespace(refresh_title=refresh)}):j.pop()()
  self.assertTrue(w.actions_open);self.assertEqual(w.dwell,123)
 def test_metadata_success_reloads_only_original_focused_list(self):
  w,c,e,j,ns,raw=self.state();run=self.metadata(w,ns);run(w,raw[1]);ns['get_list']=lambda p:[{'title':'fresh'}];reload=[];w.refresh_panel_list=lambda focus=None:reload.append(focus)
  with patch.dict(sys.modules,{'title_refresh':SimpleNamespace(refresh_title=lambda p:None)}):j.pop()()
  self.assertEqual(reload,[900]);self.assertTrue(any(x[0]=='update' and x[1]['title']=='fresh' for x in e))
