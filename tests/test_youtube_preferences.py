"""YouTube clean defaults never replace explicit Standard-update playback choices."""
import copy,importlib.util,json,unittest
import test_build_preferences as prefs
import test_preferences_install_flow as flow
from test_compatibility import Kodi,ROOT as LIB
IDS=prefs.IDS

YT='addon_data/plugin.video.youtube/settings.xml'
CLEAN={'kodion.mpd.quality.selection':'6','kodion.mpd.stream.select':'1','kodion.mpd.stream.features':'avc1,mp4a,vtt,filter,alt_sort,vp9','kodion.video.quality.isa':'true','kodion.mpd.videos':'true','kodion.video.stream.select':'1'}

class YouTubePreferences(unittest.TestCase):
 setUp=prefs.BuildPreferences.setUp
 put=prefs.BuildPreferences.put
 get=prefs.BuildPreferences.get
 accounts=prefs.BuildPreferences.accounts
 def test_clean_account_only_applies_automatic_quality_without_old_overrides(self):
  self.put(YT,{'kodion.mpd.quality.selection':'3','kodion.mpd.stream.features':'avc1,hdr'})
  a=self.m.prepare(self.home,self.accounts(),IDS+['plugin.video.youtube'],True)
  self.put(YT,{})
  self.m.restore(self.home,a,IDS+['plugin.video.youtube'])
  self.assertEqual(self.get(YT),CLEAN)
 def test_standard_retains_playback_choices_even_when_marked_upstream_default(self):
  choices={'kodion.mpd.quality.selection':'3','kodion.mpd.stream.select':'4','kodion.mpd.stream.features':'avc1,hdr,hfr,filter','kodion.video.quality.isa':'false','kodion.mpd.videos':'false','kodion.video.stream.select':'2','kodion.video.quality':'2','kodion.video.quality.ask':'true','kodion.subtitle.languages.num':'2','kodion.subtitle.download':'false','kodion.audio_only':'true'}
  self.put(YT,dict(choices,**{'youtube.api.key':'private-key','unrelated.setting':'keep out'}),default=True)
  ids=IDS+['plugin.video.youtube'];a=self.m.prepare(self.home,self.accounts(),ids,False)
  self.assertNotIn('private-key',json.dumps(a));self.assertNotIn('unrelated.setting',json.dumps(a))
  self.put(YT,dict(CLEAN,**{'youtube.api.key':'restored-account-key'}));self.m.restore(self.home,a,ids)
  result=self.get(YT)
  for key,value in choices.items():self.assertEqual(result.get(key),value)
  self.assertEqual(result['youtube.api.key'],'restored-account-key')
 def test_long_valid_codec_feature_choice_survives_retry(self):
  features='avc1,vp9,av01,hdr,hfr,3d,vr,prefer_dub,prefer_auto_dub,vorbis,mp4a,ssa,ac-3,ec-3,dts,vtt,filter,alt_sort,no_hfr_max,no_frac_fr_hint,no_fr_hint'
  self.put(YT,{'kodion.mpd.stream.features':features});ids=IDS+['plugin.video.youtube']
  a=self.m.prepare(self.home,self.accounts(),ids,False);self.put(YT,CLEAN)
  again=self.m.prepare(self.home,copy.deepcopy(a),ids,False);self.m.restore(self.home,again,ids)
  self.assertEqual(self.get(YT)['kodion.mpd.stream.features'],features)
 def test_explicit_empty_codec_feature_list_is_preserved(self):
  self.put(YT,{'kodion.mpd.stream.features':''});ids=IDS+['plugin.video.youtube']
  a=self.m.prepare(self.home,self.accounts(),ids,False);self.put(YT,CLEAN);self.m.restore(self.home,a,ids)
  self.assertEqual(self.get(YT)['kodion.mpd.stream.features'],'')
 def test_capture_retains_history_privacy_but_excludes_actions_maintenance_servers(self):
  excluded={'kodion.video.quality.isa.configure':'RunScript','kodion.history.remote':'true','kodion.maintain.clear.playback_history':'true','kodion.http.listen':'0.0.0.0','youtube.api.key':'private-key'}
  self.put(YT,dict(excluded,**{'kodion.live_stream.selection.1':'3'}),default=True);ids=IDS+['plugin.video.youtube'];a=self.m.prepare(self.home,self.accounts(),ids,False)
  self.assertEqual(a['build_preferences']['values'].get(YT),{'kodion.history.remote':'true','kodion.live_stream.selection.1':'3'})

class YouTubePolicy(unittest.TestCase):
 setUp=flow.PreferenceInstallFlow.setUp
 tearDown=flow.PreferenceInstallFlow.tearDown
 archive=flow.PreferenceInstallFlow.archive
 packaged=flow.PreferenceInstallFlow.packaged
 module=flow.PreferenceInstallFlow.module
 def test_new_policy_installs_with_new_default_validation(self):
  p=self.packaged();self.rewrite_policy(p,'playback-trakt-youtube-1','1.0.17');k=Kodi()
  m=self.module()
  try:result=m.prepare(p,k)
  except m.CompatibilityError as exc:self.fail('New YouTube policy was rejected: '+str(exc))
  self.assertEqual(result['policy']['preferences_policy'],'playback-trakt-youtube-1')
 def rewrite_policy(self,path,policy,minimum,legacy=False):
  import zipfile
  with zipfile.ZipFile(path) as z:d={n:z.read(n) for n in z.namelist()}
  marker=json.loads(d['userdata/blacklanturn-build.json']);marker.update(preferences_policy=policy,installer_min_version=minimum);d['userdata/blacklanturn-build.json']=json.dumps(marker)
  if legacy:d.pop('userdata/'+YT,None)
  with zipfile.ZipFile(path,'w') as z:
   for n,v in d.items():z.writestr(n,v)
 def test_legacy_policy_does_not_require_new_youtube_defaults(self):
  p=self.packaged();self.rewrite_policy(p,'playback-trakt-1','1.0.13',legacy=True)
  self.assertEqual(self.module().prepare(p,Kodi())['policy']['preferences_policy'],'playback-trakt-1')
 def test_wrong_policy_minimum_pair_stops_before_native_setup(self):
  for policy,minimum in [('playback-trakt-youtube-1','1.0.13'),('playback-trakt-1','1.0.16')]:
   p=self.packaged();self.rewrite_policy(p,policy,minimum);k=Kodi();m=self.module()
   with self.assertRaises(m.CompatibilityError):m.prepare(p,k)
   self.assertEqual(k.requests,[])
 def test_old_installer_rejects_new_policy_before_native_setup(self):
  p=self.packaged();self.rewrite_policy(p,'playback-trakt-youtube-1','1.0.17');k=Kodi()
  # The published1.0.15 safeguard is retained directly from the prior Git revision.
  s=importlib.util.spec_from_file_location('published_guard',LIB.parents[3]/'tests/fixtures/platform_compatibility_1_0_15.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
  with self.assertRaises(m.CompatibilityError):m.prepare(p,k)
  self.assertEqual(k.requests,[])

if __name__=='__main__':unittest.main()
