import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
from action_panel_model import build_panel, panel_header

class ActionPanelTests(unittest.TestCase):
 def test_primary_order_and_all_other_actions_are_retained(self):
  actions=[('local','Save'),('refresh','Refresh watched status'),('details','Details'),('genre','Choose genre…'),('play','Play'),('player','Play using…'),('trakt','Trakt'),('library_add','Add'),('discover','Discover'),('title_hide','Hide'),('default_player','Set default player…'),('extension','Extension action')]
  panel=build_panel(actions)
  self.assertEqual([x['id'] for x in panel['quick']],['play','player','details','genre'])
  flattened=panel['quick']+panel['playback']+[a for g in panel['groups'] for a in g['actions']]
  self.assertCountEqual([x['id'] for x in flattened],[x[0] for x in actions])
  self.assertEqual([x['id'] for x in panel['groups']],['save','trakt','discover','recommend','refresh'])
 def test_episode_genre_is_excluded_without_losing_playback(self):
  panel=build_panel([('play','Play'),('player','Play using…'),('details','Details'),('genre','Choose genre…')],episode=True)
  self.assertEqual([x['id'] for x in panel['quick']],['play','player','details'])
 def test_empty_groups_are_not_dead_remote_targets(self):
  self.assertEqual(build_panel([('play','Play')])['groups'],[])
 def test_header_uses_landscape_not_stretched_poster(self):
  h=panel_header({'label':'Example','year':2026,'type':'episode','season':3,'episode':2,'art':{'poster':'poster','thumb':'thumb','landscape':'wide'}})
  self.assertEqual(h['art'],'wide');self.assertIn('S03',h['meta']);self.assertIn('E02',h['meta'])
 def test_episode_header_recognizes_provider_url_without_numeric_fields(self):
  h=panel_header({'label':'The Engram','showtitle':'The Terminal List','file':'plugin://plugin.video.themoviedb.helper/?tmdb_type=tv&tmdb_id=1&season=1&episode=2'},'Shows')
  self.assertIn('S01',h['meta']);self.assertIn('E02',h['meta'])
 def test_malformed_episode_number_does_not_break_options(self):
  h=panel_header({'label':'Special','type':'episode','season':'Specials','episode':'unknown'},'Shows')
  self.assertTrue(h['meta'])
 def test_movie_with_kodi_default_episode_fields_stays_a_movie(self):
  h=panel_header({'title':'Movie','type':'movie','season':-1,'episode':-1,'year':2026},'Movies')
  self.assertEqual(h['meta'],'Movie · 2026')
 def test_show_cards_ignore_provider_summary_episode_numbers(self):
  h=panel_header({'title':'A show','type':'tvshow','filetype':'directory','season':2,'episode':16,'year':2022,'file':'plugin://plugin.video.themoviedb.helper/?info=seasons&tmdb_type=tv&tmdb_id=1'},'Shows')
  self.assertEqual(h['meta'],'Show · 2022')
 def test_refresh_actions_match_the_approved_priority(self):
  p=build_panel([('refresh','Refresh watched status'),('reload_list','Reload this list'),('refresh_metadata','Refresh title information')])
  self.assertEqual([a['id'] for a in p['groups'][0]['actions']],['reload_list','refresh_metadata','refresh'])
 def test_unknown_action_survives_and_long_lists_are_supported(self):
  p=build_panel([('extra'+str(i),'Extra '+str(i)) for i in range(20)])
  self.assertEqual(sum(len(g['actions']) for g in p['groups']),20)

if __name__=='__main__':unittest.main()

class NativePanelIntegration(unittest.TestCase):
 def test_native_panel_owns_options_and_returns_existing_dispatch_index(self):
  from types import SimpleNamespace
  from test_window_lifecycle import ROOT,extract
  captured=[]
  def choose(options,**kw):captured.append((options,kw));return 'details'
  state=SimpleNamespace(mode='home',section='Shows',config={},episode_browser_context=None,paths=[''],last_row=0)
  method=extract(ROOT/'live_review.py','show_title_actions',{'choose_action_panel':choose,'episode_identity':lambda i:True,'title_details_params':lambda i:{},'valid_source':lambda p:False},'LiveReview')
  options=[('play','Play'),('details','Details')]
  self.assertEqual(method(state,options,{'label':'Episode'},900),1)
  self.assertTrue(captured[0][1]['episode'])
 def test_panel_cancel_does_not_dispatch_an_action(self):
  from types import SimpleNamespace
  from test_window_lifecycle import ROOT,extract
  state=SimpleNamespace(mode='home',section='Shows',config={},episode_browser_context=None,paths=[],last_row=0)
  method=extract(ROOT/'live_review.py','show_title_actions',{'choose_action_panel':lambda *a,**k:None,'episode_identity':lambda i:False,'title_details_params':lambda i:{},'valid_source':lambda p:False},'LiveReview')
  self.assertEqual(method(state,[('play','Play')],{},900),-1)
