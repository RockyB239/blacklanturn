"""Current Helper routing must not turn automatic refresh into a modal chooser."""
import ast,sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from test_window_lifecycle import ROOT,extract
from playback_core import watch_sync_command
from backend_core import SETTINGS_GROUPS
REPO=ROOT.parents[1]
INVALIDATOR=REPO/'compatibility/addons135/patched/plugin.video.themoviedb.helper/resources/tmdbhelper/lib/sync/invalidator.py'
class SilentSync(unittest.TestCase):
 def test_automatic_refresh_selects_watched_without_opening_current_provider_chooser(self):
  tree=ast.parse(INVALIDATOR.read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='SyncInvalidator');calls=[]
  names=['SyncInvalidatorWatchedProgress','SyncInvalidatorCollection','SyncInvalidatorWatchlist','SyncInvalidatorFavorites','SyncInvalidatorRatings','SyncInvalidatorAll']
  classes={n:type(n,(),{'localized_id':n}) for n in names};ns=dict(classes,Dialog=lambda:SimpleNamespace(select=lambda *a:calls.append(a) or -1),get_localized=lambda x:x)
  exec(compile(ast.Module(body=[node],type_ignores=[]),str(INVALIDATOR),'exec'),ns)
  params=dict(x.split('=',1) for x in watch_sync_command()[len('RunScript('):-1].split(',')[1:]);result=ns['SyncInvalidator'](params['invalidate_sync']);self.assertIsInstance(result,classes['SyncInvalidatorWatchedProgress']);self.assertEqual(calls,[]);self.assertEqual(params['notification'],'');self.assertEqual(params['sync'],'')
 def test_settings_start_with_kodi_then_most_used_groups(self):
  self.assertEqual([g[0] for g in SETTINGS_GROUPS],['Kodi settings','Playback & sync','Appearance','Skin & discovery','Recommendations','Previews','Help'])
 def test_kodi_rows_put_playback_and_device_controls_before_specialist_tools(self):
  rows=next(g[2] for g in SETTINGS_GROUPS if g[0]=='Kodi settings');self.assertEqual([r[0] for r in rows][:6],['kodi:settings','kodi:PlayerSettings','kodi:SystemSettings','kodi:InterfaceSettings','kodi:addonbrowser','kodi:ServiceSettings'])
 def test_tracking_configuration_is_explicit_and_retains_all_existing_integrations(self):
  rows=next((g[2] for g in SETTINGS_GROUPS if g[0]=='Playback & sync'),[]);self.assertEqual([r[0] for r in rows][:3],['addon:plugin.video.umbrella','sync_settings','addon:plugin.video.youtube']);actions=[r[0] for g in SETTINGS_GROUPS for r in g[2]];self.assertEqual(len(actions),len(set(actions)));self.assertIn('addon:plugin.video.themoviedb.helper',actions)
 def test_explicit_sync_settings_suppresses_previews_without_changing_saved_preferences(self):
  state=SimpleNamespace(actions_open=False,alive=True,config={'PreviewMode':'auto'},stop_preview=lambda:self.assertTrue(state.actions_open),dwell=0)
  opened=[]
  def addon(name):
   self.assertEqual(name,'plugin.video.themoviedb.helper');return SimpleNamespace(openSettings=lambda:opened.append(state.actions_open))
  ns={'xbmcaddon':SimpleNamespace(Addon=addon),'event':lambda *a,**kw:None};extract(ROOT/'live_review.py','run_setting',ns,'LiveReview')(state,'sync_settings');self.assertEqual(opened,[True]);self.assertFalse(state.actions_open);self.assertEqual(state.config,{'PreviewMode':'auto'});self.assertGreater(state.dwell,0)

 def test_rating_editors_live_in_appearance_once_without_changing_their_action_ids(self):
  appearance=next(g[2] for g in SETTINGS_GROUPS if g[0]=='Appearance')
  self.assertEqual([r[0] for r in appearance],['icon_pack','title_logos','ratings','rating_order','status_display'])
  self.assertEqual(sum(r[0] in ('ratings','rating_order') for g in SETTINGS_GROUPS for r in g[2]),2)
 def test_tracking_shortcut_only_for_supported_watchable_titles(self):
  from playback_core import trakt_command,choose_player_path,resume_options
  from search_ui import discovery_result
  from browse_controls import can_choose_genre
  supported=[{'type':kind,'file':'plugin://provider/?id=17'} for kind in ('movie','tvshow','season','episode')]
  supported.append({'file':'plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=tv&tmdb_id=712&season=1&episode=4'})
  unrelated=[{'type':kind,'file':'plugin://plugin.audio.example/'} for kind in ('addon','file','song','artist','album','person')]
  unrelated.extend([{'file':'plugin://plugin.video.youtube/play/?video_id=abc123def45','type':'episode'},{'file':'plugin://unknown/'}])
  for item in supported+unrelated:
   with self.subTest(item=item):
    menus=[]
    w=SimpleNamespace(section='Home',mode='home',nav=False,search_state=None,episode_browser_context=None,discovery_stack=[],getFocusId=lambda:900,rows=[[item],[]],histories=[],row_states={},config={'Saved':[]},chosen=lambda cid:item,rating_identity=lambda _:None,stop_preview=lambda:None)
    ns={'trakt_command':trakt_command,'choose_player_path':choose_player_path,'resume_options':resume_options,'discovery_result':discovery_result,'can_choose_genre':can_choose_genre,'event':lambda *a,**k:None,'xbmcgui':SimpleNamespace(Dialog=lambda:SimpleNamespace(contextmenu=lambda labels:menus.append(labels) or -1))}
    extract(ROOT/'live_review.py','title_actions',ns,'LiveReview')(w)
    self.assertEqual('Watch tracking & sync settings…' in menus[0],item in supported)
