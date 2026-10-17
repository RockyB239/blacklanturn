import ast,sys,unittest
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs,urlsplit
from test_window_lifecycle import extract,ROOT
import search_ui
from live_core import PageHistory
from browse_controls import page_cards

def result(label,kind,identity,info=None,**params):
 return {'label':label,'title':label,'file':search_ui.route(info or ('credits_in_both' if kind=='person' else 'play'),kind,tmdb_id=identity,**params),'filetype':'directory' if kind in ('person','collection') or params else 'file'}

class SmartSearch(unittest.TestCase):
 def test_default_all_contains_best_matches_and_every_search_kind(self):
  sources=search_ui.search_sources('A24')
  self.assertEqual(sources[0]['label'],'All')
  self.assertEqual([r['label'] for r in sources[0]['rows']],['Best matches','Movies','Shows','People','Studios','Collections'])
  self.assertIn(('company','Studios'),search_ui.SEARCH_KINDS)
 def test_exact_actor_beats_a_documentary_about_the_actor(self):
  actor=result('Leonardo DiCaprio','person',6193);doc=result('Leonardo DiCaprio: Most Wanted!','movie',792166)
  files=search_ui.best_matches('leonardo dicaprio',[doc,actor])
  self.assertEqual(files[0],actor)
 def test_exact_studio_beats_titles_that_happen_to_contain_its_name(self):
  studio=result('A24','movie',41077,info='discover',with_companies=41077,with_id='True');film=result('Untitled A24 Horror Film','movie',42)
  self.assertEqual(search_ui.best_matches('a24',[film,studio])[0],studio)
 def test_franchise_suffix_matches_and_same_name_distinct_ids_remain_available(self):
  a=result('Home Alone Collection','collection',9888,info='collection',year=1990)
  b=result('Home Alone Collection','collection',1586337,info='collection')
  other=result('Home Not Alone Collection','collection',1448545,info='collection')
  files=search_ui.best_matches('Home Alone',[other,a,b,a])
  self.assertEqual([x['file'] for x in files],[a['file'],b['file'],other['file']])
 def test_same_name_titles_use_vote_count_to_rank_familiar_release_first(self):
  show=dict(result('Home Alone','tv',65282),votes='18',year=2013)
  film=dict(result('Home Alone','movie',771),votes='12,951',year=1990)
  self.assertEqual(search_ui.best_matches('Home Alone',[show,film])[0],film)
 def test_search_captions_distinguish_types_years_and_studio_countries(self):
  studio=dict(result('A24','movie',41077,info='discover',with_companies=41077),country=['US'])
  self.assertEqual(search_ui.search_caption(studio),'Studio · US')
  self.assertEqual(search_ui.search_caption(dict(result('Home Alone','movie',771),year=1990)),'Movie · 1990')
 def test_studio_logo_keeps_its_square_shape(self):
  from live_core import card_artwork
  studio=result('A24','movie',41077,info='discover',with_companies=41077)
  studio['art']={'thumb':'image://https%3a%2f%2fexample.com%2flogo.png/'}
  self.assertEqual(card_artwork(studio),{'image':studio['art']['thumb'],'kind':'square'})
 def test_studio_opens_movie_and_show_discovery_without_playback_identity(self):
  studio=result('A24','movie',41077,info='discover',with_companies=41077,with_id='True')
  found=search_ui.discovery_result(studio)
  self.assertIsNotNone(found)
  self.assertEqual(found['button'],'View titles')
  self.assertEqual([parse_qs(urlsplit(x['path']).query)['tmdb_type'][0] for x in found['rows']],['movie','tv'])
  for row in found['rows']:self.assertEqual(parse_qs(urlsplit(row['path']).query)['with_companies'],['41077'])
 def test_studio_next_page_is_navigation_instead_of_a_new_studio(self):
  page=result('Next page →','movie',41077,info='discover',with_companies=41077,with_id='True',page=2)
  page['_page_control']='next'
  self.assertIsNone(search_ui.discovery_result(page))
  calls=[]
  w=SimpleNamespace(actions_open=False,chosen=lambda cid:page,load_path=lambda *a,**kw:calls.append(('page',a)),open_discovery=lambda d:calls.append(('studio',d)))
  from live_core import is_browse_folder,episode_identity
  method=extract(ROOT/'live_review.py','onClick',{'discovery_result':search_ui.discovery_result,'is_browse_folder':is_browse_folder,'episode_identity':episode_identity},'LiveReview')
  method(w,900)
  self.assertEqual(calls,[('page',(0,page['file'],page['label']))])
 def test_search_refresh_keeps_the_anchor_resolved_by_the_provider_caller(self):
  from test_discovery_controller import DiscoveryController
  files=[result('A24 Film','movie',1),result('A24','movie',2)]
  w,_,controls=DiscoveryController().state();w.set_rows([{'label':'Initial','path':'plugin://test/initial'}]);w.search_state={'query':'A24'};w.paths[0]=search_ui.route('search','movie',query='A24')
  w.apply_row(0,files,'Movies',0,update_selected=False)
  self.assertEqual(w.rows[0][controls[900].getSelectedPosition()]['file'],files[0]['file'])
 def test_entity_hero_does_not_reintroduce_inherited_movie_ratings(self):
  from live_core import select_rating_badges
  studio=dict(result('A24','movie',41077,info='discover',with_companies=41077),rating=8.1,_rating_source='TMDb')
  props={};w=SimpleNamespace(selected=studio,config={'RatingSources':['themoviedatabase']},setProperty=props.__setitem__)
  method=extract(ROOT/'live_review.py','display_ratings',{'select_rating_badges':select_rating_badges,'DEFAULT_RATINGS':['themoviedatabase'],'discovery_result':search_ui.discovery_result},'LiveReview')
  method(w,[])
  self.assertEqual(props['ratingValue0'],'')
 def test_search_does_not_misrepresent_all_failed_requests_as_zero_matches(self):
  def provider(path):raise ValueError('Unavailable')
  with self.assertRaises(ValueError):search_ui.load_best_matches('A24',provider)
 def test_best_matches_uses_three_provider_searches_and_keeps_partial_results(self):
  calls=[];actor=result('Leonardo DiCaprio','person',6193)
  def provider(path):
   calls.append(path)
   if parse_qs(urlsplit(path).query)['tmdb_type']==['both']:return [actor]
   raise ValueError('Empty directory or unavailable')
  self.assertEqual(search_ui.load_best_matches('Leonardo DiCaprio',provider),[actor]);self.assertEqual(len(calls),3)
 def test_obsolete_best_match_search_stops_before_the_next_provider(self):
  calls=[];active=[True]
  def provider(path):calls.append(path);active[0]=False;return []
  with self.assertRaises(ValueError):search_ui.load_best_matches('old',provider,lambda:active[0])
  self.assertEqual(len(calls),1)
 def test_page_card_keeps_provider_route_and_uses_owned_navigation_art(self):
  path=search_ui.route('popular','movie');n={'filetype':'directory','file':path+'&page=2','art':{'landscape':'provider-next.png'}}
  cards,_=page_cards([n],PageHistory(),path)
  self.assertEqual(cards[0]['file'],n['file']);self.assertIn('navigation',cards[0]['art']);self.assertNotIn('landscape',cards[0]['art'])
 def test_clearing_search_selection_removes_old_title_actions_and_art(self):
  props={'title':'Old movie','hero':'old.jpg','plot':'Old plot','hasSelection':'true','ratingValue0':'9.8'}
  w=SimpleNamespace(selected={'title':'Old movie'},setProperty=props.__setitem__)
  search_ui.clear_search_selection(w)
  for key in ['title','hero','plot','ratingValue0']:self.assertEqual(props[key],'')
  self.assertEqual(props['hasSelection'],'false');self.assertIsNone(w.selected)
 def test_hidden_search_rows_never_receive_initial_focus(self):
  from test_discovery_controller import DiscoveryController,SyncThread
  queue=[]
  class Queued(SyncThread):
   def start(self):queue.append(self.target)
  w,_,controls=DiscoveryController().state(thread=Queued);w.search_state={'query':'A24'};focused=[];w.setFocusId=focused.append
  w.set_rows([{'label':'People','path':'plugin://test/people'}])
  self.assertTrue(focused)
  self.assertNotIn(900,focused,'Hidden loading rows must not steal focus from search categories')
  self.assertEqual(focused[-1],600)

 def test_completed_empty_search_does_not_take_focus_from_sidebar(self):
  from test_discovery_controller import DiscoveryController,SyncThread
  queue=[]
  class Queued(SyncThread):
   def start(self):queue.append(self.target)
  w,_,_=DiscoveryController().state(thread=Queued,provider=lambda path:[] if path.endswith('/empty') else [result('Found','movie',1)])
  focus=[600];w.getFocusId=lambda:focus[0];w.setFocusId=lambda cid:focus.__setitem__(0,cid);w.search_state={'query':'Found'}
  w.set_rows([{'label':'Empty','path':'plugin://test/empty'},{'label':'Found','path':'plugin://test/found'}]);focus[0]=50
  for run in queue:run()
  self.assertEqual(focus[0],50)

 def test_sidebar_right_returns_to_categories_when_search_has_no_results(self):
  focused=[];props={}
  w=SimpleNamespace(actions_open=False,nav=True,mode='home',search_state={'query':'A24'},rows=[[],[]],return_focus=900,
    setProperty=props.__setitem__,set_nav=lambda x,**kw:None,setFocusId=focused.append)
  extract(ROOT/'live_review.py','onAction',{},'LiveReview')(w,SimpleNamespace(getId=lambda:2))
  self.assertEqual(focused,[600])

class PreviewSetup(unittest.TestCase):
 def test_empty_or_partial_setup_is_not_ready(self):
  import preview_setup as p
  self.assertFalse(p.configured({},{}))
  self.assertFalse(p.configured({'youtube.api.key':'key','youtube.api.id':'id'},{}))
 def test_manual_and_configuration_page_keys_are_recognized_without_login_export(self):
  import preview_setup as p
  fields={'youtube.api.key':'key','youtube.api.id':'id','youtube.api.secret':'secret'}
  self.assertTrue(p.configured(fields,{}))
  self.assertTrue(p.configured({}, {'keys':{'user':{'api_key':'key','client_id':'id','client_secret':'secret'}}}))
  self.assertFalse(p.configured(fields,{},enabled=False))
 def test_hidden_preview_does_not_block_all_episodes_navigation(self):
  from test_discovery_controller import DiscoveryController
  w,_,c=DiscoveryController().state();w.selected=result('Show','tv',1);w.previews_ready=False
  route=[];c[103].controlRight=route.append
  w.row_navigation()
  self.assertIs(route[-1],c[106])
 def test_youtube_settings_return_rechecks_readiness_and_navigation(self):
  calls=[]
  w=SimpleNamespace(refresh_preview_setup=lambda:calls.append('checked'),row_navigation=lambda:calls.append('navigation'))
  addon=SimpleNamespace(openSettings=lambda:calls.append('settings'))
  method=extract(ROOT/'live_review.py','run_setting',{'event':lambda *a,**k:None,'xbmcaddon':SimpleNamespace(Addon=lambda _:addon)},'LiveReview')
  method(w,'addon:plugin.video.youtube')
  self.assertEqual(calls,['settings','checked','navigation'])
 def test_preview_button_requires_readiness_and_selection(self):
  import xml.etree.ElementTree as E
  c=E.parse(ROOT/'resources/skins/Default/1080i/LiveReview.xml').getroot().find('.//control[@id="105"]')
  self.assertIn('previewsReady',c.findtext('visible'));self.assertIn('hasSelection',c.findtext('visible'))

if __name__=='__main__':unittest.main()
