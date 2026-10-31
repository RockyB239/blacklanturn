"""New provider group contracts; fixtures contain synthetic data only."""
import importlib.util,json,sys,tempfile,unittest,types,zipfile,sqlite3,xml.etree.ElementTree as E
from pathlib import Path
from unittest.mock import patch
R=Path(__file__).resolve().parents[1];I=R/'installer-source/plugin.program.blacklanturninstaller';LIB=I/'resources/libs'
sys.path.insert(0,str(I));sys.path.insert(0,str(R/'tests'))
def load(name):
 s=importlib.util.spec_from_file_location('_provider123_'+name,LIB/(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
class ProviderPolicy(unittest.TestCase):
 def test_new_group_minimum_is47_and_legacy_minimum_remains40(self):
  m=load('managed_versions');marker={'managed_update_policy':'kodi-version-epoch-1','inplace_update_policy':'bundled-code-1','bundle_registration_policy':'new-bundles-1','youtube_refresh_patch':'youtube-freshness-2','installer_min_version':'1.0.47','helper_sync_policy':'providers-1'}
  with patch.object(m,'verify_archive_metadata'):
   try:actual=m.prepare_policy(marker,None)
   except ValueError:actual='rejected supported new group'
   self.assertEqual(actual,'1.0.47')
   for value in ('unknown',''):
    with self.assertRaises(ValueError):m.prepare_policy(dict(marker,helper_sync_policy=value),None)
   with self.assertRaises(ValueError):m.prepare_policy(dict(marker,installer_min_version='1.0.40'),None)
   old=dict(marker,installer_min_version='1.0.40');old.pop('helper_sync_policy');self.assertEqual(m.prepare_policy(old,None),'1.0.40')
 def test_distinct_provider_key_and_completed_logout_marker_survive_selected_login(self):
  m=load('authorizations');aid='script.module.tmdbhelper.sync.mdblist'
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'userdata/addon_data'/aid/'settings.xml';path.parent.mkdir(parents=True);path.write_text('<settings><setting id="apikey">synthetic-distinct-key</setting><setting id="blacklanturn_legacy_key_migrated">true</setting><setting id="unrelated">fixture</setting></settings>')
   saved=m.capture(directory,[aid],{'login'});self.assertEqual(saved['settings'].get(aid),{'apikey':'synthetic-distinct-key','blacklanturn_legacy_key_migrated':'true'})
   path.unlink();m.restore(directory,saved,[aid]);self.assertIn(b'synthetic-distinct-key',path.read_bytes());self.assertNotIn(b'unrelated',path.read_bytes())
 def test_new_helper_provider_choices_survive_standard_snapshot(self):
  m=load('build_preferences');auth=load('authorizations');aid='plugin.video.themoviedb.helper';ids=[aid];value='["script.module.tmdbhelper.sync.trakt", "script.module.tmdbhelper.sync.kodi"]'
  with tempfile.TemporaryDirectory() as directory:
   p=Path(directory)/'userdata/addon_data'/aid/'settings.xml';p.parent.mkdir(parents=True);p.write_text('<settings><setting id="sync_provider_scrobbling">'+value+'</setting><setting id="sync_provider_watched">never</setting></settings>')
   result=m.prepare(directory,auth.capture(directory,ids,{'login'}),ids,auth_only=False)
   self.assertEqual(result['build_preferences']['values'].get('addon_data/'+aid+'/settings.xml',{}).get('sync_provider_scrobbling'),value)
   self.assertEqual(result['build_preferences']['values'].get('addon_data/'+aid+'/settings.xml',{}).get('sync_provider_watched'),'never')
 def test_floppy_rotating_oauth_client_and_server_identity_are_selected_login(self):
  m=load('authorizations');aid='plugin.video.umbrella';values={'floppy.token':'synthetic-access-marker','floppy.oauth':json.dumps({'access_token':'synthetic-access','refresh_token':'synthetic-rotating-refresh'}),'floppy.oauth.client':json.dumps({'client_id':'synthetic-client','client_secret':'synthetic-secret'}),'floppy.baseurl':'https://floppy.fixture.invalid','floppy.isauthed':'true'}
  with tempfile.TemporaryDirectory() as directory:
   p=Path(directory)/'userdata/addon_data'/aid/'settings.xml';p.parent.mkdir(parents=True);root=E.Element('settings')
   for key,value in values.items():E.SubElement(root,'setting',id=key).text=value
   p.write_bytes(E.tostring(root));snapshot=m.capture(directory,[aid],{'login'});self.assertEqual(snapshot['settings'].get(aid),values)
   p.unlink();m.restore(directory,snapshot,[aid]);self.assertEqual({x.get('id'):x.text for x in E.parse(p).getroot()},values)
 def test_source_verifier_and_registry_protection_are_present(self):
  path=LIB/'helper_providers.py';self.assertTrue(path.is_file(),'Required exact provider-group source verifier is absent')
  m=load('helper_providers');self.assertEqual(len(m.IDS),3)
  with tempfile.TemporaryDirectory() as directory:
   p=Path(directory)/'Addons33.db'
   with sqlite3.connect(p) as db:db.execute('CREATE TABLE update_rules(id integer primary key,addonID text,updateRule integer)');db.execute('INSERT INTO update_rules(addonID,updateRule) VALUES("unrelated",7)')
   m.protect(p)
   with sqlite3.connect(p) as db:
    rows=set(db.execute('SELECT addonID,updateRule FROM update_rules'))
   self.assertTrue({(aid,1) for aid in m.IDS}<=rows);self.assertIn(('unrelated',7),rows)
if __name__=='__main__':unittest.main()
