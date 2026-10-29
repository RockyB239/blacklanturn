import copy,tempfile,sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from test_window_lifecycle import extract,ROOT
from row_layout import RowLayouts
try:from row_layout_ui import RowCustomization
except ImportError:RowCustomization=None
class LayoutUI(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(RowCustomization,'Customization controls are missing')
 def test_root_only_scopes_keep_episode_search_and_genre_routes_separate(self):
  w=SimpleNamespace(section='Movies',mode='home',active_page=None,search_state=None,episode_browser_context=None,person_context=None,discovery_stack=[])
  self.assertEqual(RowCustomization.row_layout_scope(w),'Movies')
  for name,value in [('episode_browser_context',{}),('search_state',{}),('active_page','horror'),('discovery_stack',[{}]),('mode','details')]:
   old=getattr(w,name);setattr(w,name,value);self.assertIsNone(RowCustomization.row_layout_scope(w));setattr(w,name,old)
  w.section='YouTube';w.active_page='library';w.youtube_tab='library';self.assertEqual(RowCustomization.row_layout_scope(w),'YouTube/library')
  w.youtube_tab='search';self.assertIsNone(RowCustomization.row_layout_scope(w))
 def test_set_rows_routes_through_arrangement_before_first_fetch(self):
  original=[{'label':'A','path':'plugin://a/'},{'label':'B','path':'plugin://b/'}];seen=[]
  w=SimpleNamespace(arrange_rows=lambda rows:list(reversed(rows)),show_row_window=lambda *a:seen.extend(w.page_definitions))
  extract(ROOT/'live_review.py','set_rows',{},'LiveReview')(w,original);self.assertEqual([r['label'] for r in seen],['B','A']);self.assertEqual(original[0]['label'],'A')
 def test_menu_claims_modal_before_stop_and_refreshes_delay(self):
  from unittest.mock import Mock
  with tempfile.TemporaryDirectory() as f:
   rows=[{'label':'A','path':'plugin://a/'},{'label':'B','path':'plugin://b/'}];w=SimpleNamespace(alive=True,actions_open=False,dwell=-10,input_generation=0,row_layouts=RowLayouts(Path(f)/'rows.json'),section='Home',active_page=None,config={'Home':rows})
   w.stop_preview=lambda:self.assertTrue(w.actions_open);w.row_layout_scope=lambda:'Home';w.customization_definitions=lambda section,tab=None:rows
   w.load_section=Mock();w.getFocusId=lambda:900;w.setFocusId=Mock()
   dialog=SimpleNamespace(select=Mock(side_effect=[0,2,-1]),ok=Mock(),yesno=Mock(return_value=False))
   with patch.dict(sys.modules,{'xbmcgui':SimpleNamespace(Dialog=lambda:dialog)}):RowCustomization.customize_rows(w,current_only=True)
   self.assertFalse(w.actions_open);self.assertGreater(w.dwell,0);self.assertEqual([x['label'] for x in w.row_layouts.rows('Home',rows)],['A','B']);self.assertTrue(w.row_layouts.flags('Home',rows[0])[1])
 def test_late_shelves_obey_hidden_and_do_not_duplicate_existing_rows(self):
  with tempfile.TemporaryDirectory() as f:
   a={'label':'Recommended','path':'plugin://yt/a'};b={'label':'Science','path':'plugin://yt/s?bl_shelf=1','youtube_category':True};new=dict(b,path='plugin://yt/s?bl_shelf=2');c={'label':'Music','path':'plugin://yt/m','youtube_category':True}
   store=RowLayouts(Path(f)/'layouts.json');store.change('YouTube/home',[a,b],b,'hide')
   w=SimpleNamespace(row_layouts=store,layout_raw_rows=[a,b],page_definitions=[a],row_layout_scope=lambda:'YouTube/home')
   self.assertEqual(RowCustomization.append_layout_rows(w,[new,c]),[c])
 def test_catalog_refresh_keeps_current_rows_and_never_revives_hidden_categories(self):
  with tempfile.TemporaryDirectory() as f:
   a={'label':'Recommended','path':'plugin://yt/a'};b={'label':'Science','path':'plugin://yt/s?bl_shelf=1','youtube_category':True};c={'label':'Music','path':'plugin://yt/m','youtube_category':True};new=dict(b,path='plugin://yt/s?bl_shelf=2')
   store=RowLayouts(Path(f)/'layouts.json');store.change('YouTube/home',[a,b,c],b,'hide');w=SimpleNamespace(row_layouts=store,layout_raw_rows=[a,b,c],page_definitions=[a,c],row_offset=0,row_layout_scope=lambda:'YouTube/home')
   rows,offset=RowCustomization.refreshed_layout_catalog(w,[a,new,c]);self.assertEqual(rows,[a,c]);self.assertEqual(offset,0)
 def test_refresh_retains_active_pair_when_catalog_drops_current_and_earlier_rows(self):
  rows=[{'label':x,'path':'plugin://yt/'+x,'youtube_category':True} for x in 'ABCDE']
  with tempfile.TemporaryDirectory() as f:
   w=SimpleNamespace(row_layouts=RowLayouts(Path(f)/'rows.json'),page_definitions=rows[:4],row_offset=2,row_layout_scope=lambda:'YouTube/home')
   for incoming in ([rows[1],rows[3],rows[4]],[rows[0],rows[2],rows[4]]):
    result,offset=RowCustomization.refreshed_layout_catalog(w,incoming);self.assertEqual(result[offset:offset+2],rows[2:4]);self.assertEqual(offset,2)
 def test_browse_capture_restores_raw_catalog_scope_after_nested_search(self):
  import test_snapshot_review_regressions as fixture
  from types import MethodType
  with tempfile.TemporaryDirectory() as f:
   w,_,_,queue=fixture.ControllerReview().state(f,lambda path:[])
   definitions=[{'label':'Local','path':'','local_items':[{'file':'a'}]}]
   w.set_rows(definitions);fixture.ControllerReview().drain(queue)
   w.layout_raw_rows=definitions+[{'label':'Hidden','path':'plugin://yt/hidden'}];w.layout_active_scope='Home'
   state=w.capture_browse();before=copy.deepcopy(w.layout_raw_rows)
   w.layout_raw_rows=[{'label':'Search results','path':'plugin://yt/search'}];w.layout_active_scope=None
   w.restore_browse(state);self.assertEqual(w.layout_raw_rows,before);self.assertEqual(w.layout_active_scope,'Home')
 def test_nested_set_rows_cannot_replace_root_raw_catalog(self):
  root=[{'label':'Home row','path':'plugin://a'}];nested=[{'label':'Search','path':'plugin://b'}]
  w=SimpleNamespace(layout_raw_rows=root,layout_active_scope='Home',row_layout_scope=lambda:None)
  self.assertEqual(RowCustomization.arrange_rows(w,nested),nested);self.assertEqual(w.layout_raw_rows,root);self.assertEqual(w.layout_active_scope,'Home')
 def test_refresh_primary_definition_updates_raw_cards_and_cursor_when_reordered(self):
  import test_youtube_row_updates as fixture
  from types import MethodType
  from youtube_core import BASE
  from test_youtube_continuation import video
  case=fixture.RowUpdates();self.addCleanup(case.doCleanups);w=case.window();w.youtube_pages={};primary=w.page_definitions[0];category={'label':'Category','path':BASE+'/special/recommendations?bl_shelf=old','youtube_category':True};w.page_definitions=[category,primary,w.page_definitions[1]];w.layout_raw_rows=copy.deepcopy(w.page_definitions)
  w.row_layout_scope=lambda:'YouTube/home';w.refreshed_layout_catalog=MethodType(RowCustomization.refreshed_layout_catalog,w)
  fresh=dict(primary,local_items=[video(4),video(5)],youtube_cursor={'continuation':'fresh'})
  with patch.object(fixture.mod,'_focus_id',return_value=900):w._apply_youtube_refresh_row(fresh)
  self.assertEqual(next(r for r in w.layout_raw_rows if r['path']==primary['path']).get('local_items'),fresh['local_items'])
  w._apply_youtube_refresh_shelves([{'label':'Unused'},category],'account-a')
  current=next(r for r in w.page_definitions if r['path']==primary['path']);self.assertEqual(current['local_items'],fresh['local_items']);self.assertEqual(current['youtube_cursor'],fresh['youtube_cursor'])
