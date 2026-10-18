"""Fail the release gate if packaged Helper, installer, policy or native proof drift."""
import argparse,hashlib,importlib.util,io,json,zipfile,sys,xml.etree.ElementTree as ET
from math import isfinite
from statistics import median
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

def verify_fire_browsing_v2(speed, manifest):
 """Validate local GUI load-to-native-readiness evidence, separate from v1 UI timing."""
 protocol='cached-native-first-usable-row-v2'
 sections=('Home','Shows','Movies','YouTube','My Stuff')
 def number(value):return type(value) in (int,float) and isfinite(value)
 def digest(value):return isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value)
 def same_number(actual, expected):
  assert number(actual) and abs(actual-expected)<=1e-9,'Native timing or observation-gap summary differs'
 def sanitized(value):
  if isinstance(value,dict):
   assert not {'native_path','data_path','native_label'} & set(value),'Public native proof contains personalized media values'
   for item in value.values():sanitized(item)
  elif isinstance(value,list):
   for item in value:sanitized(item)
  elif isinstance(value,str):
   assert not any(s in value for s in ('plugin://','https://','http://','/storage/','/Users/')),'Public native proof contains an unhashed personal path'
 def ready(state, section, generation):
  counts=state.get('data_counts',[])
  if not (isinstance(counts,list) and len(counts)==2 and all(type(n) is int and n>=0 for n in counts)):return False
  slot=next((i for i,n in enumerate(counts) if n),None)
  if slot is None:return False
  flags=state.get('window_ready',[]);row_states=state.get('row_states',[])
  path=state.get('native_path_sha256');data_path=state.get('data_path_sha256');position=state.get('position')
  return (state.get('section')==section and state.get('eyebrow')==('YOUTUBE / HOME' if section=='YouTube' else section.upper())
          and state.get('generation')==generation and state.get('focus')==900+slot
          and all(state.get(k) is False for k in ('loading','nav','startup_idle'))
          and isinstance(flags,list) and len(flags)==2 and flags[slot] is True
          and isinstance(row_states,list) and len(row_states)==2 and row_states[slot]=='ready'
          and type(state.get('native_count')) is int and state['native_count']==counts[slot]
          and state.get('native_visible') is True and type(position) is int and 0<=position<counts[slot]
          and digest(path) and path!=hashlib.sha256(b'').hexdigest() and path==data_path)
 assert speed.get('protocol')==protocol,'Unidentified Fire v2 browsing measurement protocol'
 assert speed.get('metric')=='gui_load_invocation_to_native_control_readiness','V2 must identify the local GUI load/readiness metric'
 assert speed.get('before_controller')=='0.1.82' and speed.get('after_controller')=='0.1.83'
 current=json.loads((ROOT/'controller-source/manifest83.json').read_text())
 baseline=json.loads((ROOT/'controller-source/manifest82.json').read_text())
 assert manifest==current and current.get('controller')=='0.1.83' and baseline.get('controller')=='0.1.82'
 assert len(current.get('files',{}))==len(baseline.get('files',{}))==311,'Full historical/current controller inventories required'
 helper=json.loads((ROOT/'installer-source/plugin.program.blacklanturninstaller/resources/managed-helper.json').read_text())
 assert len(helper.get('files',{}))==471 and helper.get('playback_patch')=='sampled-progress-1','Full current sampled-progress Helper inventory required'
 refs=speed.get('native_receipts',{});assert set(refs)=={'before','after'},'Both exact public native receipts required'
 assert set(speed.get('max_observation_gap_seconds',{}))=={'before','after'},'Both observed timing gaps must be reported'
 runs={};gaps={};order=[(c,s) for c in (1,2,3) for s in sections]
 for role,version,source in (('before',82,baseline),('after',83,current)):
  ref=refs[role];relative=f'controller-source/native-performance-v2-{version}.json'
  assert ref.get('path')==relative and digest(ref.get('sha256')),'Unexpected public native receipt reference'
  raw=(ROOT/relative).read_bytes()
  assert hashlib.sha256(raw).hexdigest()==ref['sha256'],'Public native receipt SHA differs from overall acceptance'
  run=json.loads(raw);sanitized(run);runs[role]=run
  assert run.get('protocol')==protocol and run.get('metric')==speed['metric']
  assert run.get('controller')==run.get('loaded_version')==source['controller'],'Loaded native controller version differs'
  assert run.get('source_files')==source['files'],'Native controller source inventory differs'
  assert run.get('helper_files')==helper['files'],'Native Helper inventory differs from full current source'
  for key in ('completed','measurement_valid','source_exact','helper_source_exact','settings_preserved','save_method_restored'):
   assert run.get(key) is True,'Incomplete native v2 acceptance: '+key
  assert run.get('preview_suppression')=='in-memory manual movie / YouTube disabled','V2 preview measurement conditions differ'
  assert run.get('preservation_scope')=='controller rows.json exact original bytes and save method during this benchmark only','Native performance preservation must not claim global device or history acceptance'
  assert run.get('loaded_method_origins')=={'load_section':'live_review.py','load_youtube_section':'youtube_browser.py','set_rows':'live_review.py','apply_row':'live_review.py'},'Loaded native method origins differ'
  redaction=run.get('sanitization',{})
  assert redaction.get('schema')==1 and redaction.get('native_paths')=='sha256-utf8' and redaction.get('personalized_labels')=='omitted' and redaction.get('loaded_method_origins')=='addon-relative' and digest(redaction.get('private_native_receipt_sha256')),'Unidentified native receipt sanitization'
  events=run.get('dispatch_log',[]);assert isinstance(events,list) and events,'GUI dispatch provenance required'
  threads={}
  for event in events:
   values=[event.get(k) for k in ('queued_at','started_at','finished_at')]
   assert all(number(t) and t>0 for t in values) and values==sorted(values),'Invalid GUI dispatch timestamps'
   thread=event.get('thread');assert type(thread) is int and thread>0
   threads[thread]=True
  assert len(threads)==1,'Native observations must dispatch on one GUI thread'
  def dispatch(event, label):
   assert isinstance(event,dict) and event.get('label')==label and event in events,'Missing exact GUI dispatch event'
   return event['started_at'],event['finished_at']
  visits=run.get('visits',[])
  assert isinstance(visits,list) and [(v.get('cycle'),v.get('section')) for v in visits]==order,'All fifteen ordered native visits required'
  previous_arrival=0;run_gap=0
  for visit in visits:
   name=visit['section'];assert visit.get('passed') is True,'Failed native first-usable visit: '+name
   start=visit.get('load_started_at');returned=visit.get('load_returned_at');before=visit.get('before',{})
   assert all(number(t) and t>0 for t in (start,returned,before.get('observed_at'))),'Invalid native load timestamps'
   begin,end=dispatch(visit.get('dispatch'),'actual GUI load '+name)
   assert previous_arrival<=begin<=before['observed_at']<=start<=returned<=end,'Native load invocation is outside its GUI event'
   generation=visit.get('generation_after_load');old=before.get('generation')
   assert type(generation) is int and type(old) is int and generation>old,'Native readiness must follow a fresh load generation'
   samples=visit.get('samples',[])
   assert isinstance(samples,list) and samples and type(visit.get('sample_count')) is int and visit['sample_count']==len(samples),'Native samples missing or dropped'
   assert visit.get('arrival')==samples[-1],'Arrival must be the actual final native observation'
   times=[]
   for index,sample in enumerate(samples):
    observed=sample.get('observed_at');assert number(observed) and observed>=returned,'Native observation precedes actual load'
    lo,hi=dispatch(sample.get('dispatch'),'native first-usable probe')
    assert lo<=observed<=hi and sample['dispatch']['queued_at']>=returned,'Native readiness was not read inside a GUI dispatch'
    assert type(sample.get('generation')) is int and sample['generation']==generation,'Native sample belongs to a stale load generation'
    assert not times or observed>times[-1],'Native observations must remain ordered'
    times.append(observed)
    assert ready(sample,name,generation)==(index==len(samples)-1),'Missing native readiness or an earlier ready sample was skipped'
   elapsed=times[-1]-start;assert elapsed>0
   same_number(visit.get('first_usable_seconds'),elapsed)
   gap=max((b-a for a,b in zip(times,times[1:])),default=0)
   same_number(visit.get('max_observation_gap_seconds'),gap);run_gap=max(run_gap,gap);previous_arrival=times[-1]
  observation=run.get('observation',{})
  assert observation.get('precision')=='actual-gui-observations-with-reported-gaps','Probe target interval must not be presented as measurement precision'
  same_number(observation.get('max_observation_gap_seconds'),run_gap)
  same_number(speed['max_observation_gap_seconds'][role],run_gap);gaps[role]=run_gap
 assert runs['before']['helper_files']==runs['after']['helper_files'],'Helper changed across v2 measurements'
 claimed=speed.get('sections',{});assert set(claimed)==set(sections),'Missing Fire v2 section summary'
 result={}
 for name in sections:
  a=[v['first_usable_seconds'] for v in runs['before']['visits'] if v['section']==name]
  b=[v['first_usable_seconds'] for v in runs['after']['visits'] if v['section']==name]
  summary=claimed[name]
  for key,expected in (('before_seconds',a),('after_seconds',b)):
   values=summary.get(key);assert isinstance(values,list) and len(values)==3 and all(number(v) and v>0 for v in values) and values==expected,'Aggregate speed samples differ from native receipts'
  base=median(a);now=median(b);limit=max(base*.20,.35);passed=now-base<=limit+1e-9
  for key,value in (('before_median',base),('after_median',now),('allowed_increase_seconds',limit)):same_number(summary.get(key),value)
  assert summary.get('within_tolerance') is passed,'Aggregate threshold result differs from native evidence'
  assert passed,'Fire browsing slowed beyond tolerance: '+name
  result[name]={'before_seconds':a,'after_seconds':b,'before_median':base,'after_median':now,'allowed_increase_seconds':limit,'within_tolerance':passed}
 return {'protocol':protocol,'metric':speed['metric'],'sections':result,'max_observation_gap_seconds':gaps}

def verify_release112_acceptance(receipt,manifest,*,require_v2=False):
 """Require current UI/playback proof; candidates use v2, historical fixtures retain v1."""
 assert receipt.get('controller')==manifest.get('controller')=='0.1.83'
 assert receipt.get('files')==manifest['files'],'Release 1.1.12 source differs from native-tested controller'
 assert receipt.get('passed') is True,'Release 1.1.12 native acceptance incomplete'
 devices=receipt.get('devices',{})
 assert set(devices)=={'mac','fire','apple_tv'},'Fresh release 1.1.12 acceptance required on all three devices'
 for name,d in devices.items():
  for key in ('source_exact','ordinary_restart','authorization_grants_preserved','settings_preserved',
              'youtube_history_preserved','youtube_details_supported_content','youtube_details_movie_sections_hidden',
              'youtube_details_back_retains_captions','independent_preview_focus_verified','preview_policy_unchanged','help_current'):
   assert d.get(key) is True,'Missing '+name+' release 1.1.12 acceptance: '+key
 def number(value):return type(value) in (int,float) and isfinite(value)
 fire=devices['fire'];speed=fire.get('browsing_speed',{})
 assert not require_v2 or speed.get('protocol')=='cached-native-first-usable-row-v2','New release 1.1.12 candidate requires native performance v2'
 if speed.get('protocol')=='cached-native-first-usable-row-v2':
  verify_fire_browsing_v2(speed,manifest)
 else:
  assert speed.get('protocol')=='cached-native-first-usable-row-v1','Unidentified Fire browsing measurement protocol'
  assert speed.get('before_controller')=='0.1.82' and speed.get('after_controller')=='0.1.83','Fire speed evidence must compare 82 with 83'
  sections=speed.get('sections',{})
  assert set(sections)=={'Home','Shows','Movies','YouTube','My Stuff'},'Missing Fire browsing speed section'
  for name,d in sections.items():
   before=d.get('before_seconds',[]);after=d.get('after_seconds',[])
   for samples in (before,after):
    assert isinstance(samples,list) and len(samples)>=3 and all(number(v) and v>0 for v in samples),'Invalid or insufficient Fire speed samples: '+name
   baseline=median(before);current=median(after)
   assert current-baseline<=max(baseline*.20,.35)+1e-9,'Fire browsing slowed beyond tolerance: '+name
 stop=fire.get('paused_stop',{})
 for key in ('actual_outgoing_writer_verified','helper_source_exact','stopped_while_paused'):
  assert stop.get(key) is True,'Missing actual Fire paused-stop proof: '+key
 assert number(stop.get('pause_seconds')) and stop['pause_seconds']>=5,'Fire pause duration not exercised'
 position=stop.get('kodi_position_seconds');duration=stop.get('duration_seconds')
 assert number(position) and number(duration) and 0<position<duration,'Invalid actual Fire playback position'
 for key in ('helper_stop_progress','settled_trakt_progress'):
  progress=stop.get(key)
  assert number(progress) and 0<=progress<80,'Invalid partial-playback Fire progress: '+key
  assert abs(progress*duration/100-position)<=1,'Fire paused-stop position differs from '+key

def verify_helper_progress_acceptance(receipt,approved):
 """Historical empty-cache proof cannot authorize the newly sampled Helper source."""
 assert receipt.get('source_version')==approved.get('upstream_version')=='6.17.9'
 assert receipt.get('playback_patch')==approved.get('playback_patch')=='sampled-progress-1'
 assert len(approved.get('files',{}))==471,'Full current Helper source inventory required'
 assert receipt.get('source_files')==approved['files'],'Current Helper requires fresh exact-source native cache evidence'
 assert receipt.get('source_origin_verified') is True and receipt.get('passed') is True
 assert receipt.get('mode')=='packaged' and receipt.get('device')=='Fire Stick Kodi21.3','Native Fire packaged Helper cache evidence required'
 assert receipt.get('tests')==12 and receipt.get('failures')==receipt.get('errors')==0,'All 12 native cache regressions must pass'

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

def verify_display_defaults(z):
 config=json.loads(z.read('userdata/addon_data/script.blacklanturn.preview/rows.json'))
 assert config.get('RatingSources')==['rottentomatoes','metacritic','imdb','popcorn'],'Clean builds must default to four ratings with TMDb hidden'

def verify(folder):
 verify_release112_acceptance(json.loads((ROOT/'controller-source/usability-release112-verification.json').read_text()),json.loads((ROOT/'controller-source/manifest83.json').read_text()),require_v2=True)
 verify_release111_acceptance(json.loads((ROOT/'controller-source/youtube-release111-verification.json').read_text()),json.loads((ROOT/'controller-source/manifest82.json').read_text()))
 verify_release110_acceptance(json.loads((ROOT/'controller-source/youtube-release110-verification.json').read_text()),json.loads((ROOT/'controller-source/manifest81.json').read_text()))
 verify_youtube_acceptance(json.loads((ROOT/'controller-source/youtube-native-verification.json').read_text()),json.loads((ROOT/'controller-source/manifest75.json').read_text()))
 verify_stall_acceptance(json.loads((ROOT/'controller-source/youtube-stall-mac-verification.json').read_text()),json.loads((ROOT/'controller-source/youtube-stall-native-verification.json').read_text()),json.loads((ROOT/'controller-source/manifest76.json').read_text()))
 receipt=json.loads((ROOT/'compatibility/helper-progress/native-verification.json').read_text())
 approved=json.loads((SOURCE/'resources/managed-helper.json').read_text())
 verify_helper_progress_acceptance(receipt,approved)
 spec=importlib.util.spec_from_file_location('managed',SOURCE/'resources/libs/managed_addons.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 with zipfile.ZipFile(folder/'plugin.program.blacklanturninstaller-1.0.17.zip') as z:
  assert z.testzip() is None
  installer={n:z.read(n) for n in z.namelist()}
  assert all(n.startswith('plugin.program.blacklanturninstaller/') for n in installer)
  expected_installer={'plugin.program.blacklanturninstaller/'+str(p.relative_to(SOURCE)):p.read_bytes() for p in SOURCE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and not p.name.endswith(('.pyc','.DS_Store'))}
  assert installer==expected_installer,'Installer ZIP differs from reviewed source'
 for ed in ('General','Apple-TV-Mac'):
  with zipfile.ZipFile(folder/f'BlackLanturn-{ed}-Kodi21-1.1.12.zip') as z:
   assert z.testzip() is None;m.verify_archive(z);verify_playback_defaults(z);verify_display_defaults(z)
   p=json.loads(z.read('userdata/blacklanturn-build.json'))
   assert p['schema']==3 and p['preferences_policy']=='playback-trakt-youtube-1' and p['helper_patch']=='empty-cache-1' and p['installer_min_version']=='1.0.17'
   assert p['build_version']=='1.1.12'
   assert p['controller_version']=='0.1.83' and p['helper_search_patch']=='search-batch-1' and p['helper_playback_patch']=='sampled-progress-1'
   gui={n.get('id'):n.text for n in ET.fromstring(z.read('userdata/guisettings.xml'))}
   assert {k:gui[k] for k in ('filecache.memorysize','filecache.readfactor','filecache.buffermode','filecache.chunksize')}=={'filecache.memorysize':'64','filecache.readfactor':'400','filecache.buffermode':'4','filecache.chunksize':'131072'}
   assert next(n.text for n in ET.fromstring(z.read('userdata/addon_data/plugin.video.themoviedb.helper/settings.xml')) if n.get('id')=='artwork_quality')=='1'
   expected=json.loads((ROOT/'controller-source/manifest83.json').read_text())['files']
   actual={n[len('addons/script.blacklanturn.preview/'):]:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith('addons/script.blacklanturn.preview/')}
   assert actual==expected
   for n,d in installer.items():assert z.read('addons/'+n)==d,'Installer mismatch'
   assert z.read('addons/plugin.program.blacklanturninstaller/resources/libs/managed_addons.py')==(SOURCE/'resources/libs/managed_addons.py').read_bytes()
 print('PASS: both packages, protected schema, exact installer, full Helper manifest and native regression evidence')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('artifacts',type=Path);verify(p.parse_args().artifacts)
