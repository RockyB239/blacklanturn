"""Routine YouTube access renewal must not invalidate unchanged Home identity."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
from light_home_model import display_scope
class ScopeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name);self.store=root/'script.blacklanturn.preview';self.store.mkdir()
        self.youtube=root/'plugin.video.youtube';self.youtube.mkdir();self.account=self.youtube/'access_manager.json'
        self.api=self.youtube/'api_keys.json';self.api.write_text('{"keys":{"user":{"api_key":"fixture-key"}}}')
        self.fields={'youtube.api.key':'fixture-key','youtube.api.id':'fixture-id','youtube.api.secret':'fixture-secret'}
        self.addons=[{'addonid':'plugin.video.youtube','enabled':True,'path':'/addons/plugin.video.youtube'},
                     {'addonid':'resource.images.fixture','enabled':True,'path':'/addons/resource.images.fixture'}]
        modules={'xbmc':SimpleNamespace(executeJSONRPC=lambda request:json.dumps({'result':{'addons':self.addons}})),
                 'xbmcaddon':SimpleNamespace(Addon=lambda _:SimpleNamespace(getSetting=lambda key:self.fields.get(key,'')))}
        self.patcher=patch.dict(sys.modules,modules);self.patcher.start();self.addCleanup(self.patcher.stop)
        self.value={'access_manager':{'current_user':'0','users':{'0':{'id':'a'*32,'refresh_token':'fixture-refresh','access_token':'old-access','expires':1}}}}
        self.write(self.value)
    def write(self,value):self.account.write_text(json.dumps(value))
    def scope(self):return display_scope(self.store,'current-native-trakt-scope')
    def test_access_token_and_expiry_renewal_keep_same_connected_identity(self):
        before=self.scope();self.assertIsNotNone(before)
        changed=copy.deepcopy(self.value);user=changed['access_manager']['users']['0']
        user.update(access_token='renewed-access',expires=9999999999,access_token_expiry=123456789)
        self.write(changed)
        self.assertEqual(before,self.scope())
    def test_account_switch_refresh_identity_and_logout_invalidate(self):
        before=self.scope()
        variants=[]
        changed=copy.deepcopy(self.value);changed['access_manager']['users']['0']['id']='b'*32;variants.append(changed)
        changed=copy.deepcopy(self.value);changed['access_manager']['users']['0']['refresh_token']='different-refresh';variants.append(changed)
        changed=copy.deepcopy(self.value);changed['access_manager']['users']['1']=changed['access_manager']['users'].pop('0');changed['access_manager']['current_user']='1';variants.append(changed)
        variants.extend(({'access_manager':{'current_user':'0','users':{}}},{'access_manager':{}},{}))
        for value in variants:
            self.write(value);current=self.scope();self.assertIsNotNone(current);self.assertNotEqual(before,current)
        self.account.unlink();self.assertNotEqual(before,self.scope())
    def test_malformed_and_oversized_account_records_fail_closed(self):
        malformed=[[], {'access_manager':[]}, {'access_manager':{'users':[]}}, {'access_manager':{'current_user':'0','users':{'0':[]}}}]
        for raw in ['{broken', '', ' '*(1024*1024+1)]+[json.dumps(value) for value in malformed]:
            self.account.write_text(raw);self.assertIsNone(self.scope())
    def test_api_settings_integration_and_policy_changes_still_invalidate(self):
        before=self.scope()
        self.api.write_text('{"keys":{"user":{"api_key":"changed"}}}')
        self.assertNotEqual(before,self.scope());before=self.scope()
        self.fields['youtube.api.secret']='changed-secret';self.assertNotEqual(before,self.scope());before=self.scope()
        self.addons[0]['enabled']=False;self.assertNotEqual(before,self.scope());before=self.scope()
        (self.store/'title-preferences.json').write_text('{"version":1,"titles":{}}')
        self.assertNotEqual(before,self.scope())
