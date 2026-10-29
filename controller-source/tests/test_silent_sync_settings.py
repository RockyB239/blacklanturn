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
  self.assertEqual([g[0] for g in SETTINGS_GROUPS],['Kodi settings','Playback & sync','Appearance','Skin & discovery','Recommendations','Previews','Ratings','Help'])
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
