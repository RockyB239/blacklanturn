"""Run Standard preference restoration with real migration and synthetic accounts."""
import copy,importlib.util,json,unittest
from pathlib import Path
import test_build_preferences as fixtures
ROOT=Path(__file__).resolve().parents[1];LIB=ROOT/'installer-source/plugin.program.blacklanturninstaller/resources/libs'
CAT=json.loads((LIB.parent/'discovery-lineup.json').read_text())
class DiscoveryMigration(unittest.TestCase):
 def setUp(self):
  spec=importlib.util.spec_from_file_location('discovery_defaults',LIB/'discovery_defaults.py')
  self.assertTrue((LIB/'discovery_defaults.py').exists(),'Missing installer default-lineup migration')
  self.m=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.m)
 def old_catalog(self):
  cfg={'Movies':[{'label':'Old movies','path':'old'}],'Shows':[{'label':'Old shows','path':'old-tv'}], 'Genres':[{'id':'action','section':'Movies','label':'My Action','enabled':False,'custom_page':'keep','rows':[{'label':'Old action','path':'old-action'}]}], 'Saved':[{'id':7}], 'RatingSources':['imdb'],'PreviewMode':'manual','custom':{'answer':42}}
  catalog=copy.deepcopy(CAT);catalog['recognized']={'sections':{'Movies':[self.m.fingerprint(cfg['Movies'])],'Shows':[self.m.fingerprint(cfg['Shows'])]},'pages':{'Genres:Movies:action':[self.m.fingerprint(cfg['Genres'][0]['rows'])]}}
  catalog['defaults']['Genres']=[{'id':'action','section':'Movies','label':'Action','rows':[{'label':'New action','path':'new-action'}]}]
  return cfg,catalog
 def test_known_default_rows_upgrade_but_all_other_data_is_preserved(self):
  cfg,cat=self.old_catalog();before=copy.deepcopy(cfg);out=json.loads(self.m.upgrade(json.dumps(cfg),cat))
  self.assertEqual(out['Movies'],cat['defaults']['Movies']);self.assertEqual(out['Shows'],cat['defaults']['Shows'])
  self.assertEqual(out['Genres'][0]['rows'],[{'label':'New action','path':'new-action'}])
  self.assertEqual(out['Genres'][0]['label'],'My Action');self.assertFalse(out['Genres'][0]['enabled']);self.assertEqual(out['Genres'][0]['custom_page'],'keep')
  for key in ('Saved','RatingSources','PreviewMode','custom'):self.assertEqual(out[key],cfg[key])
  self.assertEqual(cfg,before)
 def test_customized_groups_are_not_replaced_or_appended_to(self):
  cfg,cat=self.old_catalog();cfg['Movies'][0]['label']='Custom';cfg['Genres'][0]['rows'].append({'label':'Mine','path':'mine'})
  out=json.loads(self.m.upgrade(json.dumps(cfg),cat));self.assertEqual(out['Movies'],cfg['Movies']);self.assertEqual(out['Genres'],cfg['Genres'])
 def test_unknown_or_already_current_config_keeps_exact_raw_json(self):
  raw=' {"Saved":[], "custom": true}\n';self.assertEqual(self.m.upgrade(raw),raw)
  cfg,cat=self.old_catalog();first=self.m.upgrade(json.dumps(cfg),cat);self.assertEqual(self.m.upgrade(first,cat),first)
 def test_standard_pending_retry_is_repeatable_without_recapturing_new_defaults(self):
  fixture=fixtures.BuildPreferences();fixture.setUp();self.addCleanup(fixture.doCleanups)
  cfg,cat=self.old_catalog();path=fixture.home/'userdata'/fixture.m.CONTROLLER_CONFIG;path.parent.mkdir(parents=True);original=json.dumps(cfg);path.write_text(original)
  (fixture.home/'userdata/blacklanturn-build.json').write_text('{"discovery_patch":"discovery-first-page-1"}')
  ids=fixtures.IDS+['script.blacklanturn.preview'];accounts=fixture.m.prepare(fixture.home,fixture.accounts(),ids)
  self.assertEqual(accounts['build_preferences']['controller'],original)
  from unittest.mock import patch
  with patch.object(fixture.m,'discovery_upgrade',lambda raw:self.m.upgrade(raw,cat)):
   fixture.m.restore(fixture.home,accounts,ids);first=path.read_bytes();fixture.m.restore(fixture.home,json.loads(json.dumps(accounts)),ids)
  self.assertEqual(path.read_bytes(),first);self.assertEqual(json.loads(first)['Movies'],cat['defaults']['Movies']);self.assertEqual(accounts['build_preferences']['controller'],original)
 def test_real_recognized_previous_lineup_upgrades_to_tested_recipes(self):
  # Public repository's prior clean configuration is retained as a test fixture.
  raw=(ROOT/'tests/fixtures/discovery-legacy-defaults.json').read_text();cfg=json.loads(raw);cfg.update(Saved=[{'id':99}],PreviewMode='manual')
  out=json.loads(self.m.upgrade(json.dumps(cfg)));self.assertEqual(out['Movies'],CAT['defaults']['Movies']);self.assertEqual(out['Shows'],CAT['defaults']['Shows']);self.assertEqual(out['Saved'],[{'id':99}]);self.assertEqual(out['PreviewMode'],'manual')
if __name__=='__main__':unittest.main()

class OlderBuildRestoration(unittest.TestCase):
 def test_installer22_does_not_migrate_when_installing_an_older_build(self):
  fixture=fixtures.BuildPreferences();fixture.setUp();self.addCleanup(fixture.doCleanups)
  path=fixture.home/'userdata'/fixture.m.CONTROLLER_CONFIG;path.parent.mkdir(parents=True)
  original=(ROOT/'tests/fixtures/discovery-legacy-defaults.json').read_text();path.write_text(original)
  ids=fixtures.IDS+['script.blacklanturn.preview'];accounts=fixture.m.prepare(fixture.home,fixture.accounts(),ids)
  (fixture.home/'userdata/blacklanturn-build.json').write_text('{"build_version":"1.1.16"}')
  fixture.m.restore(fixture.home,accounts,ids);self.assertEqual(path.read_text(),original)
