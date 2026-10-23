import copy,sys,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
import discovery_order as d
from test_discovery_order import item
P='plugin://plugin.video.themoviedb.helper/?info=discover&tmdb_type=movie&with_genres='
class ContextTests(unittest.TestCase):
 def setUp(self):
  self.assertTrue(callable(getattr(d,'order_discovery_row',None)),'Missing normal controller discovery ordering')
  self.w=SimpleNamespace(section='Movies',active_page=None,mode='home',search_state=None,episode_browser_context=None,person_context=None,discovery_stack=[],row_offset=0,paths=[P+'28',P+'12'],page_definitions=[{'label':'Action','path':P+'28','discovery_order':{'enabled':True}},{'label':'Adventure','path':P+'12','discovery_order':{'enabled':True}}],snapshot_cache=SimpleNamespace(scope='account/config A'))
 def order(self,n,files):return d.order_discovery_row(self.w,n,files)
 def test_same_first_page_only_no_added_provider_candidates(self):
  first=[item(n) for n in range(20)];self.order(0,first)
  files=[item(n) for n in range(10,30)];more={'label':'Next','file':P+'12&page=2','filetype':'directory'};files.append(more)
  out=self.order(1,files)
  self.assertEqual(len(out),21);self.assertEqual(out[-1],more)
  self.assertTrue(all(any(x is y for y in files) for x in out))
  self.assertLessEqual(sum(x['file'] in {i['file'] for i in first[:12]} for x in out[:12]),2)
 def test_repeats_remain_when_only_relevant_candidates_repeat(self):
  files=[item(n) for n in range(5)];self.order(0,files)
  self.assertEqual(self.order(1,files),files)
 def test_account_or_config_scope_change_does_not_carry_exposure(self):
  self.order(0,[item(n) for n in range(20)])
  self.w.snapshot_cache.scope='account/config B'
  files=[item(n) for n in range(10,30)]
  self.assertEqual(self.order(1,files),files)
 def test_watch_refresh_retains_frozen_order_and_current_objects(self):
  self.order(0,[item(n) for n in range(20)])
  first=self.order(1,[item(n) for n in range(10,30)])
  fresh=[item(n,playcount=9,resume={'position':55,'total':100}) for n in reversed(range(10,30))]
  out=self.order(1,fresh)
  self.assertEqual([x['file'] for x in out],[x['file'] for x in first])
  self.assertTrue(all(x['playcount']==9 and x['resume']['position']==55 for x in out))
 def test_no_policy_or_protected_context_is_never_reordered(self):
  files=[item(n) for n in range(10,30)];self.order(0,[item(n) for n in range(20)])
  for attr,value in [('section','Home'),('section','YouTube'),('section','My Stuff'),('mode','details'),('search_state',{}),('episode_browser_context',{}),('person_context',{}),('discovery_stack',[1]),('snapshot_cache',None)]:
   original=getattr(self.w,attr);setattr(self.w,attr,value)
   self.assertEqual(self.order(1,files),files,attr);setattr(self.w,attr,original)
  self.w.page_definitions[1].pop('discovery_order');self.assertEqual(self.order(1,files),files)
 def test_personal_route_cannot_opt_in_with_policy(self):
  self.order(0,[item(n) for n in range(20)])
  path='plugin://plugin.video.themoviedb.helper/?info=trakt_recommendations&tmdb_type=movie'
  self.w.paths[1]=path;self.w.page_definitions[1]['path']=path
  files=[item(n) for n in range(10,30)];self.assertEqual(self.order(1,files),files)
 def test_late_result_for_different_definition_is_not_reordered(self):
  self.order(0,[item(n) for n in range(20)]);self.w.paths[1]=P+'27'
  files=[item(n) for n in range(10,30)];self.assertEqual(self.order(1,files),files)
 def test_policy_edit_and_page_change_do_not_reuse_frozen_order(self):
  first=self.order(1,[item(n) for n in range(20)])
  self.w.page_definitions[1]['discovery_order']['exclude_ids']=['movie:0']
  after=self.order(1,[item(n) for n in reversed(range(20))]);self.assertNotIn('Title 0',[x['title'] for x in after])
  self.w.paths[1]+='&page=2';files=[item(n) for n in range(30,50)];self.assertEqual(self.order(1,files),files)
if __name__=='__main__':unittest.main()

class RendererIntegration(unittest.TestCase):
 def state(self):
  from test_discovery_controller import DiscoveryController
  from types import MethodType
  w,_,controls=DiscoveryController().state()
  from playback_core import restored_position
  w.apply_row.__func__.__globals__['restored_position']=restored_position
  w.selected=None;w.section='Movies';w.active_page=None;w.search_state=None;w.person_context=None;w.discovery_stack=[];w.snapshot_cache=SimpleNamespace(scope='A')
  w.paths=[P+'28',P+'12'];w.page_definitions=[{'label':'Action','path':P+'28','discovery_order':{'enabled':True}},{'label':'Adventure','path':P+'12','discovery_order':{'enabled':True}}]
  w.prepare_discovery_order=lambda n,files:d.order_discovery_row(w,n,files)
  return w,controls
 def test_initial_focus_leads_with_first_ranked_title_not_deferred_duplicate(self):
  w,c=self.state();w.apply_row(0,[item(n) for n in range(20)],'Action')
  w.apply_row(1,[item(n) for n in range(10,30)],'Adventure',ranked_start=True)
  self.assertEqual(w.rows[1][0]['title'],'Title 12')
  self.assertEqual(c[901].getSelectedPosition(),0)
 def test_watched_refresh_keeps_selected_title_after_reordering(self):
  w,c=self.state();w.apply_row(0,[item(n) for n in range(20)],'Action');w.apply_row(1,[item(n) for n in range(10,30)],'Adventure',ranked_start=True)
  old=list(w.rows[1]);anchor=old[4]['file'];c[901].selectItem(4)
  fresh=[dict(x,playcount=9) for x in reversed(old)];position=next(i for i,x in enumerate(fresh) if x['file']==anchor)
  w.apply_row(1,fresh,'Adventure',position,update_selected=False)
  self.assertEqual(w.rows[1][c[901].getSelectedPosition()]['file'],anchor)
  self.assertEqual(w.rows[1][c[901].getSelectedPosition()]['playcount'],9)
  self.assertEqual([x['file'] for x in w.rows[1]],[x['file'] for x in old])

class RestoredSelectionRegression(RendererIntegration):
 def test_restored_provider_zero_anchor_is_not_mistaken_for_initial_page(self):
  w,c=self.state();w.apply_row(0,[item(n) for n in range(20)],'Action')
  w.apply_row(1,[item(n) for n in range(10,30)],'Adventure',ranked_start=True)
  # A deferred provider response stores the actual selected Title 10 at
  # provider index zero, although frozen display order puts it near the end.
  fresh=[item(n,playcount=9) for n in range(10,30)]
  w.apply_row(1,fresh,'Adventure',0)
  self.assertEqual(w.rows[1][c[901].getSelectedPosition()]['title'],'Title 10')
