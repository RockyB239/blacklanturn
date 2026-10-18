"""Fail the release gate if packaged Helper, installer, policy or native proof drift."""
import argparse,hashlib,importlib.util,io,json,zipfile,sys,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'installer-source/plugin.program.blacklanturninstaller'
sys.path.insert(0,str(SOURCE))
def verify_youtube_acceptance(receipt,manifest,version='0.1.75'):
 assert receipt['controller']==manifest['controller']==version
 assert receipt['files']==manifest['files'],'YouTube source differs from native-tested controller'
 a=receipt['acceptance'];assert a['passed']
 for key in ('connected_sidebar_visible','youtube_sidebar_after_movies_before_my_stuff','transient_failure_retains_sidebar','disconnected_sidebar_hidden_with_simulated_account_state','reconnected_sidebar_visible','disconnected_playback_return_rejects_private_snapshot','subscriptions_tab_loaded','library_tab_loaded','channels_tab_loaded','youtube_search_loaded','independent_preview_toggle_disabled_playback','preview_navigation_cancels_playback','local_watch_history_unchanged','in_memory_preferences_unchanged'):
  assert a.get(key) is True,'Missing Mac acceptance: '+key
 for feed in ('recommendations','subscriptions'):
  assert a['feeds'][feed]['same_as_signed_in_addon'] and a['feeds'][feed]['video_ids_matched']>0
 adaptive=a['adaptive_home']
 assert adaptive['groups']>0 and adaptive['labels_match_provider'] and adaptive['normal_full_play_urls']
 assert adaptive['exact_youtube_com_home'] is False
 assert a.get('youtube_watch_refresh_preserves_category_art_and_order') is True
 cards=a['youtube_cards'];assert cards['forced_missing_primary_tested'] and cards['layout']=='16:9'
 visual=receipt['visual_verification']
 assert visual['forced_missing_primary_thumbnail_visible'] and visual['independent_selection_outline_visible'] and visual['other_visible_video_thumbnails_loaded']
 assert visual['youtube_title_unclipped'] and visual['description_initial_visible_lines']>=4 and visual['description_scroll_delay_ms']==7000
 assert visual['navigation_folder_cards_fitted'] and visual['navigation_focus_matches_background'] and visual['navigation_no_stretched_hero']
 tiles=a['youtube_navigation_tiles'];assert tiles['tested']==2 and tiles['separate_folder_art'] and tiles['no_stretched_hero'] and tiles['no_preview_playback']
 preview=a['automatic_preview']
 assert preview['exact_selected_video'] and preview['windowed'] and preview['local_history_reporting'] is False and preview['remote_history_reporting'] is False and preview['end_seconds']==30
 p=receipt['settings_and_authorizations']
 assert p['passed'] and p['authorization_grants_and_selected_accounts_preserved'] and p['playback_and_addon_setting_values_preserved']

def verify_stall_acceptance(mac,fire,manifest):
 assert manifest['controller']=='0.1.76'
 verify_youtube_acceptance(mac,manifest,'0.1.76')
 restart=mac['ordinary_restart'];assert restart['passed'] and restart['source_exact'] and restart['home_ready'] and restart['active_players']==[]
 baseline=json.loads((ROOT/'controller-source/manifest75.json').read_text())
 prior=json.loads((ROOT/'controller-source/youtube-native-verification.json').read_text())
 assert mac['visual_basis']=={'controller':'0.1.75','files':baseline['files']},'Unidentified prior visual evidence'
 assert mac['visual_verification']==prior['visual_verification'],'Visual evidence changed'
 changed={n for n in set(baseline['files'])|set(manifest['files']) if baseline['files'].get(n)!=manifest['files'].get(n)}
 assert changed=={'addon.xml','live_review.py','preview_geometry.py','youtube_provider.py'},'Visual/layout changes require fresh visual acceptance'
 assert fire['completed'] and fire['controller']=='0.1.76' and fire['source']==manifest,'Fire proof source differs'
 assert fire['unit_tests']>=569
 native=fire['native'];moments=native['cancel_moments']
 assert [m['moment'] for m in moments]==['queued','opening','playing'],'Missing cancellation stage'
 assert all(m['normal_core_restored'] is True for m in moments),'Decoder settings were not restored'
 assert native['preview_decoder']=='ff-h264' and native['normal_clip_decoder']=='amc-h264','Normal hardware decoding not verified'
 assert native['youtube_history_preserved'] and native['protected_files_preserved']>0
 assert native['normal_restart'] and native['source_exact'] and native['task_staging_removed']
 assert len(native['youtube_trials'])==2 and all(t['available'] and t['adaptive_groups']>0 and all(t['main_row_counts']) for t in native['youtube_trials'])
 assert fire['apple_tv_accessed'] is False

def verify_release110_acceptance(receipt,manifest):
 """Fresh controller 81 proof; historical 75/76 receipts are provenance only."""
 assert receipt.get('controller')==manifest.get('controller')=='0.1.81'
 assert receipt.get('files')==manifest['files'],'Release 1.1.10 source differs from native-tested controller'
 assert receipt.get('passed') is True,'Release 1.1.10 native acceptance incomplete'
 devices=receipt.get('devices',{})
 assert set(devices)=={'mac','fire','apple_tv'},'Fresh native acceptance required on all three devices'
 for name,d in devices.items():
  for key in ('source_exact','ordinary_restart','authorization_grants_preserved','settings_preserved','youtube_history_preserved'):
   assert d.get(key) is True,'Missing '+name+' acceptance: '+key
  assert d.get('continuation_rows',0)>=3 and d.get('continuation_batches',0)>=3,'Continuation rows not exercised on '+name
  preview=d.get('inline_preview',{})
  assert 42<=preview.get('media_seconds',0)<=47,'45-second preview not verified on '+name
  assert 0<preview.get('max_height',0)<=720 and preview.get('codec')=='h264','Preview stream not capped at 720p H264 on '+name
  assert preview.get('fade') is True and preview.get('same_hover_no_restart') is True,'Preview fade or same-hover completion missing on '+name
  assert 0<=preview.get('max_probe_gap_seconds',float('inf'))<5,'Preview continuity not verified on '+name
  full=d.get('fullscreen',{})
  assert full.get('automatic') is True and full.get('ceiling')==2160 and 720<full.get('selected_height',0)<=2160,'Automatic full playback quality not verified on '+name
  category=d.get('category_relevance',{})
  assert category.get('music_rows_checked',0)>=1 and category.get('nonmusic_in_added_music_choices')==0,'Music relevance not verified on '+name
 fire=devices['fire'];moments=fire.get('cancel_moments',[])
 assert [m.get('moment') for m in moments]==['queued','opening','playing'],'Missing Fire cancellation stage'
 assert all(m.get('no_late_play') is True and m.get('normal_core_restored') is True for m in moments),'Fire cancellation leaves late playback or decoder override'
 assert fire.get('normal_clip_decoder')=='amc-h264','Normal Fire hardware decoding not verified'

def verify_release111_acceptance(receipt,manifest):
 """Fresh 82 subject-row proof; unchanged 81 playback evidence stays labeled 81."""
 assert receipt.get('controller')==manifest.get('controller')=='0.1.82'
 assert receipt.get('files')==manifest['files'],'Release 1.1.11 source differs from native-tested controller'
 assert receipt.get('passed') is True,'Release 1.1.11 native acceptance incomplete'
 baseline=json.loads((ROOT/'controller-source/manifest81.json').read_text())
 prior_path='controller-source/youtube-release110-verification.json'
 prior=json.loads((ROOT/prior_path).read_text())
 verify_release110_acceptance(prior,baseline)
 assert receipt.get('prior_playback_basis')=={'controller':'0.1.81','files':baseline['files'],'receipt':prior_path},'Unidentified prior playback evidence'
 changed={name for name in set(baseline['files'])|set(manifest['files']) if baseline['files'].get(name)!=manifest['files'].get(name)}
 assert changed=={'addon.xml','youtube_home.py','youtube_provider.py','youtube_relevance.py'},'Playback inheritance requires exactly the reviewed subject-row source delta'
 assert set(manifest['files'])==set(baseline['files']),'Playback inheritance cannot add or remove controller files'
 devices=receipt.get('devices',{})
 assert set(devices)=={'mac','fire','apple_tv'},'Fresh native acceptance required on all three devices'
 for name,d in devices.items():
  for key in ('source_exact','ordinary_restart','authorization_grants_preserved','settings_preserved','youtube_history_preserved','refresh_recommendations_verified','continuation_preserves_existing_cards'):
   assert d.get(key) is True,'Missing '+name+' release 1.1.11 acceptance: '+key
  category=d.get('category_relevance',{})
  assert category.get('subject_rows_checked',0)>=1,'New subject row not exercised on '+name
  assert category.get('continued_new_choices',0)>=1,'New subject row continuation not exercised on '+name
  assert category.get('row_mismatches')==0,'Subject-row mismatches on '+name

def verify_playback_defaults(z):
 gui={n.get('id'):n.text or '' for n in ET.fromstring(z.read('userdata/guisettings.xml'))}
 assert gui.get('locale.audiolanguage')=='default','Build audio language must follow the interface language'
 assert gui.get('locale.subtitlelanguage')=='forced_only','Build subtitle preference must be forced only'
 def settings(aid):
  return {n.get('id'):n.text or '' for n in ET.fromstring(z.read('userdata/addon_data/'+aid+'/settings.xml'))}
 umbrella=settings('plugin.video.umbrella');youtube=settings('plugin.video.youtube');helper=settings('plugin.video.themoviedb.helper')
 assert umbrella.get('provider.external.enabled')=='true','Playback has no configured external provider'
 assert umbrella.get('external_provider.module')=='script.module.cocoscrapers','Playback provider module missing'
 assert umbrella.get('external_provider.name')=='cocoscrapers','Playback provider name missing'
 for key,value in {'kodion.mpd.quality.selection':'6','kodion.mpd.stream.select':'1','kodion.mpd.stream.features':'avc1,mp4a,vtt,filter,alt_sort,vp9','kodion.video.quality.isa':'true','kodion.mpd.videos':'true','kodion.video.stream.select':'1'}.items():
  assert youtube.get(key)==value,'Incorrect clean YouTube playback default: '+key
 assert helper.get('trakt_watchedindicators')=='true','Build must enable authenticated watch metadata'
 spec=importlib.util.spec_from_file_location('prefs',SOURCE/'resources/libs/build_preferences.py');prefs=importlib.util.module_from_spec(spec);spec.loader.exec_module(prefs)
 try:prefs.verify_archive(z)
 except prefs.PreferenceError as exc:raise AssertionError(str(exc)) from exc

def verify(folder):
 verify_release111_acceptance(json.loads((ROOT/'controller-source/youtube-release111-verification.json').read_text()),json.loads((ROOT/'controller-source/manifest82.json').read_text()))
 verify_release110_acceptance(json.loads((ROOT/'controller-source/youtube-release110-verification.json').read_text()),json.loads((ROOT/'controller-source/manifest81.json').read_text()))
 verify_youtube_acceptance(json.loads((ROOT/'controller-source/youtube-native-verification.json').read_text()),json.loads((ROOT/'controller-source/manifest75.json').read_text()))
 verify_stall_acceptance(json.loads((ROOT/'controller-source/youtube-stall-mac-verification.json').read_text()),json.loads((ROOT/'controller-source/youtube-stall-native-verification.json').read_text()),json.loads((ROOT/'controller-source/manifest76.json').read_text()))
 receipt=json.loads((ROOT/'compatibility/helper-empty-cache/native-verification.json').read_text())
 approved=json.loads((SOURCE/'resources/managed-helper.json').read_text())
 assert receipt.get('source_origin_verified') is True
 assert receipt['passed'] and receipt['tests']==12 and receipt['failures']==receipt['errors']==0
 assert receipt['source_version']==approved['upstream_version'] and receipt['source_files']==approved['files'],'New Helper requires fresh native regression evidence'
 spec=importlib.util.spec_from_file_location('managed',SOURCE/'resources/libs/managed_addons.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 with zipfile.ZipFile(folder/'plugin.program.blacklanturninstaller-1.0.16.zip') as z:
  assert z.testzip() is None
  installer={n:z.read(n) for n in z.namelist()}
  assert all(n.startswith('plugin.program.blacklanturninstaller/') for n in installer)
  expected_installer={'plugin.program.blacklanturninstaller/'+str(p.relative_to(SOURCE)):p.read_bytes() for p in SOURCE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and not p.name.endswith(('.pyc','.DS_Store'))}
  assert installer==expected_installer,'Installer ZIP differs from reviewed source'
 for ed in ('General','Apple-TV-Mac'):
  with zipfile.ZipFile(folder/f'BlackLanturn-{ed}-Kodi21-1.1.11.zip') as z:
   assert z.testzip() is None;m.verify_archive(z);verify_playback_defaults(z)
   p=json.loads(z.read('userdata/blacklanturn-build.json'))
   assert p['schema']==3 and p['preferences_policy']=='playback-trakt-youtube-1' and p['helper_patch']=='empty-cache-1' and p['installer_min_version']=='1.0.16'
   assert p['build_version']=='1.1.11'
   assert p['controller_version']=='0.1.82' and p['helper_search_patch']=='search-batch-1'
   gui={n.get('id'):n.text for n in ET.fromstring(z.read('userdata/guisettings.xml'))}
   assert {k:gui[k] for k in ('filecache.memorysize','filecache.readfactor','filecache.buffermode','filecache.chunksize')}=={'filecache.memorysize':'64','filecache.readfactor':'400','filecache.buffermode':'4','filecache.chunksize':'131072'}
   assert next(n.text for n in ET.fromstring(z.read('userdata/addon_data/plugin.video.themoviedb.helper/settings.xml')) if n.get('id')=='artwork_quality')=='1'
   expected=json.loads((ROOT/'controller-source/manifest82.json').read_text())['files']
   actual={n[len('addons/script.blacklanturn.preview/'):]:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith('addons/script.blacklanturn.preview/')}
   assert actual==expected
   for n,d in installer.items():assert z.read('addons/'+n)==d,'Installer mismatch'
   assert z.read('addons/plugin.program.blacklanturninstaller/resources/libs/managed_addons.py')==(SOURCE/'resources/libs/managed_addons.py').read_bytes()
 print('PASS: both packages, protected schema, exact installer, full Helper manifest and native regression evidence')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('artifacts',type=Path);verify(p.parse_args().artifacts)
