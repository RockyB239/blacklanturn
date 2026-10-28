import importlib.util,json,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'addon'
def movie(n=1,label='Film',kind='movie'):
 return {'label':label,'title':label,'file':'plugin://plugin.video.themoviedb.helper/?info='+('seasons' if kind=='tv' else 'play')+'&tmdb_type='+kind+'&tmdb_id='+str(n),'genre':['Drama'],'resume':{'position':10,'total':100}}
def load(test):
 p=ROOT/'title_preferences.py';test.assertTrue(p.exists(),'Exact-title preferences are not implemented')
 s=importlib.util.spec_from_file_location('title_preferences',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
class Preferences(unittest.TestCase):
 def test_hide_is_exact_and_keeps_same_genre_neighbors_and_original_objects(self):
  m=load(self)
  with tempfile.TemporaryDirectory() as d:
   store=m.TitlePreferences(Path(d)/'prefs.json',session='one');a,b=movie(),movie(2);source=[a,b]
   store.set(a,'hide');out=store.apply(source)
   self.assertEqual(out,[b]);self.assertIs(out[0],b);self.assertEqual(source,[a,b]);self.assertEqual(a['resume']['position'],10)
   self.assertEqual(store.apply([movie(1,kind='tv')]),[movie(1,kind='tv')])
 def test_identity_rejects_ambiguous_titles_episodes_people_and_page_controls(self):
  m=load(self)
  for x in ({'label':'Film'},dict(movie(),type='episode',season=1,episode=1),dict(movie(),_page_control='next'),dict(movie(),file=movie()['file'].replace('tmdb_type=movie','tmdb_type=person')),dict(movie(),file=movie()['file'].replace('info=play','info=episodes')),dict(movie(),file=movie()['file'].replace('plugin.video.themoviedb.helper','untrusted'))):
   self.assertIsNone(m.title_key(x),str(x))
  self.assertEqual(m.title_key(movie()),'movie:1');self.assertEqual(m.title_key(movie(kind='tv')),'tv:1')
 def test_persistence_undo_and_mode_replacement_are_lossless(self):
  m=load(self)
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'prefs.json';s=m.TitlePreferences(p,session='one');a=movie();before=s.set(a,'less');self.assertIsNone(before)
   prior=s.set(a,'hide');self.assertEqual(prior['mode'],'less');self.assertEqual(len(s.entries('hide')),1);self.assertFalse(s.entries('less'))
   s.restore(a,prior);self.assertEqual(m.TitlePreferences(p,session='one').state(a),'less')
   s.restore(a,None);self.assertEqual(m.TitlePreferences(p).state(a),'');self.assertEqual(s.apply([a]),[a])
 def test_less_is_stable_and_reduces_only_exact_title_across_sessions(self):
  m=load(self)
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'prefs.json';a,b=movie(),movie(2);s=m.TitlePreferences(p,session='initial');s.set(a,'less');self.assertEqual(s.apply([a,b]),[b])
   visible=0
   for i in range(80):
    t=m.TitlePreferences(p,session='visit'+str(i));x=t.apply([a,b]);self.assertEqual(t.apply([a,b]),x);self.assertIn(b,x);visible+=a in x
   self.assertGreater(visible,8);self.assertLess(visible,32)
 def test_filter_keeps_native_paging_and_disabled_scopes(self):
  m=load(self)
  with tempfile.TemporaryDirectory() as d:
   s=m.TitlePreferences(Path(d)/'p');a=movie();n={'label':'Next','_page_control':'next','file':'plugin://next/'};s.set(a,'hide')
   self.assertEqual(s.apply([a,n]),[n]);self.assertEqual(s.apply([a,n],enabled=False),[a,n])
 def test_corrupt_store_is_not_overwritten_and_failed_write_keeps_memory(self):
  m=load(self)
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'p';p.write_text('{broken');s=m.TitlePreferences(p);self.assertEqual(s.apply([movie()]),[movie()])
   with self.assertRaises(ValueError):s.set(movie(),'hide')
   self.assertEqual(p.read_text(),'{broken')
   p.unlink();s=m.TitlePreferences(p);p.mkdir()
   with self.assertRaises(OSError):s.set(movie(),'hide')
   self.assertEqual(s.state(movie()),'')
 def test_preferences_have_no_render_time_disk_access(self):
  m=load(self)
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'p';s=m.TitlePreferences(p);s.set(movie(),'hide');p.unlink();p.mkdir()
   for i in range(10):self.assertEqual(s.apply([movie(),movie(2)]),[movie(2)])
if __name__=='__main__':unittest.main()

class FeedbackIntegration(unittest.TestCase):
 def test_discovery_scope_keeps_search_saved_trakt_progress_and_episodes(self):
  m=load(self)
  from types import SimpleNamespace
  s=SimpleNamespace(section='Movies',mode='home',search_state=None,episode_browser_context=None,person_context=None)
  base='plugin://plugin.video.themoviedb.helper/?info='
  self.assertTrue(m.discovery_scope(s,base+'popular&tmdb_type=movie'))
  for route in ('trakt_ondeck','trakt_inprogress','trakt_nextepisodes','trakt_watchlist','trakt_history','trakt_collection','episodes','seasons','search'):
   self.assertFalse(m.discovery_scope(s,base+route),route)
  s.search_state={'query':'Film'};self.assertFalse(m.discovery_scope(s,base+'popular'))
  s.search_state=None;s.section='My Stuff';self.assertFalse(m.discovery_scope(s,base+'popular'))
 def test_real_renderer_hides_without_poisoning_cache_and_restores_without_provider_fetch(self):
  m=load(self)
  from test_discovery_controller import DiscoveryController
  from types import MethodType
  from test_window_lifecycle import extract
  with tempfile.TemporaryDirectory() as d:
   p=ROOT/'title_feedback_ui.py';self.assertTrue(p.exists(),'Feedback integration missing')
   ns={'discovery_scope':m.discovery_scope}
   prepare=extract(p,'prepare_title_row',ns,'TitleFeedback');raw=extract(p,'raw_title_row',ns,'TitleFeedback')
   a,b=movie(),movie(2);s,calls,controls=DiscoveryController().state(provider=lambda _:[a,b]);s.section='Movies';s.search_state=None;s.person_context=None
   s.title_preferences=m.TitlePreferences(Path(d)/'p');s.title_preferences.set(a,'hide')
   s.prepare_title_row=MethodType(prepare,s);s.raw_title_row=MethodType(raw,s)
   path='plugin://plugin.video.themoviedb.helper/?info=popular&tmdb_type=movie';s.set_rows([{'label':'Popular','path':path}])
   self.assertEqual(s.rows[0],[b]);self.assertEqual(s.result_cache.get(path),[a,b]);before=len(calls)
   s.title_preferences.restore(a);s.apply_row(0,s.raw_title_row(0), 'Popular',update_selected=False)
   self.assertEqual(s.rows[0],[a,b]);self.assertEqual(len(calls),before)
 def test_title_menu_offers_restore_instead_of_another_hide(self):
  m=load(self)
  from types import SimpleNamespace
  from test_window_lifecycle import extract
  p=ROOT/'title_feedback_ui.py';self.assertTrue(p.exists(),'Feedback controls missing')
  with tempfile.TemporaryDirectory() as d:
   store=m.TitlePreferences(Path(d)/'p');s=SimpleNamespace(title_preferences=store)
   action=extract(p,'title_feedback_actions',{'title_key':m.title_key},'TitleFeedback')
   self.assertEqual(action(s,movie()),[('title_hide','Hide this movie'),('title_less','Show this title less often')])
   store.set(movie(),'hide');self.assertEqual(action(s,movie())[0],('title_restore','Unhide this movie'))
   store.restore(movie());store.set(movie(),'less');self.assertEqual(action(s,movie())[0],('title_restore','Restore normal frequency'))
   self.assertEqual(action(s,{'label':'Unknown'}),[])
 def test_all_hidden_titles_leave_row_empty_without_fetching_replacements(self):
  m=load(self)
  from test_discovery_controller import DiscoveryController
  from types import MethodType
  from test_window_lifecycle import extract
  p=ROOT/'title_feedback_ui.py';self.assertTrue(p.exists(),'Feedback integration missing')
  with tempfile.TemporaryDirectory() as d:
   s,calls,controls=DiscoveryController().state(provider=lambda _:[movie()]);
   from test_discovery_controller import Control
   controls[50]=Control();s.navigation_items=[1];s.set_nav=lambda *a,**k:None;s.section='Movies';s.search_state=None;s.person_context=None
   s.title_preferences=m.TitlePreferences(Path(d)/'p');s.title_preferences.set(movie(),'hide')
   s.prepare_title_row=MethodType(extract(p,'prepare_title_row',{'discovery_scope':m.discovery_scope},'TitleFeedback'),s)
   base='plugin://plugin.video.themoviedb.helper/?info=popular&tmdb_type=movie'
   s.set_rows([{'label':str(i),'path':base+'&slot='+str(i)} for i in range(5)])
   self.assertEqual(len(calls),2);self.assertEqual(s.row_offset,0);self.assertEqual(s.rows,[[],[]])

class ReviewRegressions(unittest.TestCase):
 def test_url_only_episode_never_turns_into_a_full_series_dislike(self):
  m=load(self)
  episode={'file':'plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=tv&tmdb_id=123&season=1&episode=2','filetype':'file'}
  self.assertIsNone(m.title_key(episode))
 def test_background_discovery_rows_remain_filtered_while_details_is_open(self):
  m=load(self)
  from types import SimpleNamespace
  path='plugin://plugin.video.themoviedb.helper/?info=popular&tmdb_type=movie'
  state=SimpleNamespace(section='Movies',mode='details',search_state=None,episode_browser_context=None,person_context=None)
  self.assertTrue(m.discovery_scope(state,path),'Details feedback must not unhide its background discovery rows')
 def test_background_watch_hydration_survives_feedback_repaint(self):
  m=load(self)
  from test_snapshot_controller import SnapshotController
  from test_public_row_snapshots import P,ITEM
  from test_window_lifecycle import extract
  from types import MethodType
  with tempfile.TemporaryDirectory() as d:
   s,calls,controls,queue=SnapshotController().state(d,lambda path:[dict(ITEM,playcount=2,resume={'position':40,'total':100})]);s.section='Movies';s.mode='home'
   s.title_preferences=m.TitlePreferences(Path(d)/'p')
   ui=ROOT/'title_feedback_ui.py'
   for name in ('prepare_title_row','raw_title_row'):
    setattr(s,name,MethodType(extract(ui,name,{'discovery_scope':m.discovery_scope},'TitleFeedback'),s))
   import ast
   if any(isinstance(x,ast.FunctionDef) and x.name=='hydrate_title_row' for n in ast.parse(ui.read_text()).body if isinstance(n,ast.ClassDef) and n.name=='TitleFeedback' for x in n.body):
    s.hydrate_title_row=MethodType(extract(ui,'hydrate_title_row',{},'TitleFeedback'),s)
   s.set_rows([{'label':'Popular','path':P}]);queue.pop(0)();s.apply_row(0,s.raw_title_row(0),'Popular',update_selected=False)
   self.assertEqual(s.rows[0][0].get('playcount'),2)
   self.assertEqual(s.rows[0][0].get('resume'),{'position':40,'total':100})
 def test_pending_related_page_rechecks_feedback_inside_commit_lock(self):
  m=load(self)
  from test_similar_navigation import SimilarPaging
  from urllib.parse import urlsplit,parse_qs
  fixture=SimilarPaging()
  self.addCleanup(fixture.doCleanups)
  def provider(path):
   return [movie()] if parse_qs(urlsplit(path).query).get('info')==['recommendations'] else []
  w,queue,controls,focus,_,_,tmdb=fixture.state(provider)
  fired=[]
  class Interleave:
   def __enter__(self):
    if not fired:w.title_preferences.set(movie(),'hide');fired.append(True)
   def __exit__(self,*a):pass
  w.preview_dispatch_lock=Interleave();w.load_related_page(tmdb('recommendations','movie',tmdb_id=42,page=2));queue.pop().run()
  self.assertEqual(fired,[True]);self.assertNotIn('movie:1',[m.title_key(x) for x in w.related])
 def test_show_season_and_episode_totals_do_not_make_the_series_an_episode(self):
  m=load(self)
  show=dict(movie(1413,'American Horror Story','tv'),type='tvshow',filetype='directory',season=13,episode=145)
  self.assertEqual(m.title_key(show),'tv:1413')
