"""Actual new provider selection must preserve explicit legacy choices without writes."""
import importlib.util,sys,types,unittest,xml.etree.ElementTree as E
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'patched/plugin.video.themoviedb.helper'
class SyncMigration(unittest.TestCase):
 def module(self,values):
  from unittest.mock import patch
  self.reads=[]
  def get(key,kind=None):self.reads.append(key);return values.get(key,'' if kind=='str' else False)
  plugin=types.SimpleNamespace(get_setting=get,set_setting=lambda *a:(_ for _ in ()).throw(AssertionError('Unexpected settings write')))
  with patch.dict(sys.modules,{'tmdbhelper.lib.addon.plugin':plugin,'tmdbhelper.lib.sync.providers.features':types.SimpleNamespace(FEATURE_LABELS={})}):
   s=importlib.util.spec_from_file_location('selection_under_test',ROOT/'resources/tmdbhelper/lib/sync/providers/selection.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
  return m
 def test_legacy_watched_watchlist_collection_choose_saved_provider(self):
  for capability in ('watched','watchlist','collection'):
   for old,new in [('Trakt','trakt'),('MDbList','mdblist')]:
    with self.subTest(capability=capability,provider=old):self.assertEqual(self.module({'sync_source_'+capability:old}).SyncProviderSetting(capability).provider_id,new)
 def test_saved_disabled_scrobbling_stays_off(self):
  self.assertEqual(self.module({'trakt_scrobbling':False,'mdblist_scrobbling':False}).SyncProviderSetting('scrobbling').provider_id,'')
 def test_existing_authorized_trakt_uses_same_provider(self):
  self.assertEqual(self.module({'trakt_scrobbling':True,'trakt_token':'synthetic'}).SyncProviderSetting('scrobbling').provider_id,'trakt')
 def test_existing_authorized_mdblist_keeps_provider(self):
  self.assertEqual(self.module({'trakt_scrobbling':False,'mdblist_scrobbling':True,'mdblist_apikey':'synthetic'}).SyncProviderSetting('scrobbling').provider_id,'mdblist')
 def test_explicit_new_selection_and_never_override_legacy(self):
  for value,want in [('kodi','kodi'),('never','')]:
   m=self.module({'sync_provider_watched':value,'sync_source_watched':'Trakt'});self.assertEqual(m.SyncProviderSetting('watched').provider_id,want)
 def test_existing_context_menu_visibility_choice_still_controls_sync_actions(self):
  nodes={n.get('id') for n in E.parse(ROOT/'resources/settings.xml').iter('setting')}
  self.assertIn('contextmenu_sync_trakt',nodes)
  context=(ROOT/'resources/tmdbhelper/lib/items/context.py').read_text()
  self.assertNotIn('contextmenu_sync_options',context)
  self.assertIn('contextmenu_sync_trakt',context)
 def test_group_ids_follow_kodi_integer_schema(self):
  for group in E.parse(ROOT/'resources/settings.xml').iter('group'):self.assertTrue(group.get('id','').isdigit())
 def test_legacy_settings_remain_registered_and_hidden(self):
  nodes={n.get('id'):n for n in E.parse(ROOT/'resources/settings.xml').iter('setting')}
  for name in ('sync_source_watched','sync_source_watchlist','sync_source_collection','trakt_scrobbling','mdblist_scrobbling'):
   self.assertIn(name,nodes);self.assertEqual(nodes[name].findtext('visible'),'false')
if __name__=='__main__':unittest.main()
