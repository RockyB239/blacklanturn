"""Fail the release gate if packaged Helper, installer, policy or native proof drift."""
import argparse,hashlib,importlib.util,io,json,zipfile,sys,xml.etree.ElementTree as ET
from math import isfinite
from statistics import median
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'installer-source/plugin.program.blacklanturninstaller'
sys.path.insert(0,str(SOURCE))

def verify_shared_network_acceptance(receipt, manifest):
 """Actual isolated Kodi RequestAPI evidence, not three-device playback proof."""
 assert receipt.get('passed') is True and receipt.get('personal_profile_accessed') is False
 assert str(receipt.get('runtime','')).startswith('21.3'), 'Request compatibility needs Kodi21.3 acceptance'
 assert set(receipt.get('editions',{}))=={'General','Apple-TV-Mac'}, 'Both packaged request sources need native acceptance'
 expected=manifest['files']['resources/modules/jurialmunkey/reqapi.py']
 for case in receipt['editions'].values():
  assert case.get('passed') is True and case.get('actual_module_loaded') is True
  assert case.get('source_sha256')==expected, 'Untested shared request source'
  assert case.get('server_cooldown_seconds')==120 and case.get('minimum_cooldown_seconds')==60
  assert case.get('ordinary_http_error_logs_redacted') is True
  assert case.get('successful_calls')==10000 and case.get('extra_transport_calls')==0
  assert case.get('new_background_thread') is False
  elapsed=case.get('successful_synthetic_calls_seconds')
  assert type(elapsed) in (int,float) and isfinite(elapsed) and 0<elapsed<5

def verify_umbrella_progress_acceptance(receipt, manifest):
 """Require real callbacks, settled provider results and clean device readbacks.

 This gate covers the Python progress repair. It makes no claim about the
 separately signed Apple TV application or its native image library.
 """
 def number(value): return type(value) in (int, float) and isfinite(value)
 def digest(value): return isinstance(value, str) and len(value)==64 and all(c in '0123456789abcdef' for c in value)
 def settled(case):
  assert case.get('cloud_reads_matched')==2, 'Immediate and settled cloud reads are required'
  error=case.get('cloud_error_seconds')
  assert number(error) and 0<=error<=2, 'Progress differs from the observed native destination'
 assert receipt.get('passed') is True and receipt.get('patch')==manifest.get('patch')=='event-progress-3'
 devices=receipt.get('devices', {})
 assert set(devices)=={'fire', 'mac', 'apple_tv'}, 'Progress acceptance is incomplete on the three devices'
 for name, device in devices.items():
  assert device.get('version')=='6.7.92', 'Both release editions package Umbrella 6.7.92; an older native variant cannot approve '+name
  variant=manifest['variants'].get(device.get('version'))
  assert variant and device.get('candidate_sha256')==variant['after_sha256'], 'Untested progress source on '+name
  trace=device.get('loaded_trace_sha256')
  assert digest(trace) and trace==device.get('expected_trace_sha256'), 'Native loaded source differs from guarded trace on '+name
  for key in ('diagnostics_removed', 'other_sources_preserved', 'settings_authorizations_preserved',
              'watched_history_unchanged', 'unrelated_progress_unchanged', 'ordinary_restart', 'quiet_home'):
   assert device.get(key) is True, 'Missing '+name+' acceptance: '+key
  cold=device['cold_seek_stop']
  assert cold.get('absolute_callback_ms')==750000 and cold.get('av_ready') is False, 'Cold absolute seek was not tested'
  elapsed=cold.get('seconds_after_player')
  assert number(elapsed) and 0<elapsed<=2, 'Cold test waited for warmed-up tracking'
  progress=cold.get('outgoing_progress')
  assert number(progress) and 0<progress<100, 'Cold seek did not send positive progress'
  settled(cold)
  resume=device['saved_resume']
  assert resume.get('native_duration_replaced_fallback') is True, 'Native duration refinement was not tested'
  settled(resume)
  pause=device['pause_stop']
  assert number(pause.get('paused_seconds')) and pause['paused_seconds']>=3, 'Pause duration is unproven'
  drift=pause.get('native_drift_seconds')
  assert number(drift) and 0<=drift<0.1, 'Paused playback advanced'
  settled(pause)
  zero=device['zero_seek_stop']
  assert zero.get('absolute_callback_ms')==0 and zero.get('selected_resume_id_matched') is True
  assert zero.get('delete_status')==204 and zero.get('absent_cloud_reads')==2, 'Selected resume was not cleared and settled'
  assert zero.get('invalid_zero_pause_sent') is False, 'Rejected zero-percent pause is still sent'

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

def verify_autoplay_acceptance(receipt, controller, umbrella):
 """Current Mac evidence; historical three-device tests cannot certify this delta."""
 assert receipt.get('passed') is True and receipt.get('device')=='Mac Kodi 21.3'
 assert receipt.get('tested_commit')=='0b674a3be14cb48ed2fa336e6121fbb597a5f7de'
 assert receipt.get('tested_controller')=='0.1.83' and controller.get('controller')=='0.1.84'
 old_files=receipt['controller_files']
 xml=(ROOT/'controller-source/historical-addon84.xml').read_bytes()
 assert hashlib.sha256(xml).hexdigest()==controller['files']['addon.xml'],'Historical controller metadata drift'
 assert hashlib.sha256(xml.replace(b'version="0.1.84"',b'version="0.1.83"')).hexdigest()==old_files['addon.xml'], 'Untested controller metadata change'
 expected=dict(old_files, **{'addon.xml':hashlib.sha256(xml).hexdigest()})
 assert controller['files']==expected, 'Controller implementation differs from naturally tested Mac'
 required={
  'addons/plugin.video.umbrella/'+n for n in ('resources/lib/modules/player.py','resources/lib/modules/sources.py','resources/lib/modules/source_preferences.py','umbrella.py','service.py')}
 required.update('addons/script.blacklanturn.preview/'+n for n in ('default.py','live_review.py','autoplay_session.py','resources/skins/Default/1080i/LiveReview.xml'))
 assert set(receipt['tested_files'])==required
 for path,digest in receipt['tested_files'].items():
  _,addon,relative=path.split('/',2)
  actual=umbrella['files'][relative] if addon=='plugin.video.umbrella' else controller['files'][relative]
  assert actual==digest, 'Packaged implementation differs from native evidence: '+path
 assert umbrella.get('autoplay_patch')=='same-show-source-1'
 assert receipt.get('natural_episodes_completed')==4 and receipt.get('native_eof_callbacks')==4
 assert receipt.get('prepared_source_matches')==4 and receipt.get('simulated_viewing_count') is False
 for field in ('sequence_without_seeking','season_transition','stillwatching_saved_preferences_unchanged',
               'stillwatching_pause_confirmed','manual_service_and_ceiling_retained','trakt_completed_watched_partial_unwatched'):
  assert receipt.get(field) is True, 'Missing natural Mac acceptance: '+field
 for key in ('stop_seconds','resume_seconds'):
  value=receipt.get(key);assert type(value) in (int,float) and isfinite(value) and value>=60
 assert abs(receipt['stop_seconds']-receipt['resume_seconds'])<2
 preservation=receipt['preservation']
 for key in ('passed','untargeted_progress_unchanged','installed_files_unchanged'):
  assert preservation.get(key) is True
 assert preservation.get('core_settings')==280 and preservation.get('addon_settings_files')==16 and preservation.get('history_databases')==4
 cleanup=receipt['test_cleanup'];assert cleanup.get('session_cleared') is True and cleanup.get('prepared_policy_cleared') is True and cleanup.get('queue_size')==0
 assert receipt.get('other_devices_accessed') is False, 'Deferred devices must remain untouched'

def verify_youtube_end_acceptance(receipt, manifest, historical=False):
 """Bind the new delta to actual Mac acceptance without inventing remote tests."""
 assert receipt.get('schema')==1 and receipt.get('feature')=='youtube-end-1' and receipt.get('passed') is True
 assert receipt.get('devices')==['mac'] and receipt.get('runtime')=='21.3','New native evidence is Mac only'
 assert receipt.get('tested_controller')=='0.1.84' and receipt.get('release_controller')==manifest.get('controller')=='0.1.85'
 if historical:
  xml=(ROOT/'controller-source/historical-addon85.xml').read_bytes();files=dict(manifest['files'])
  assert hashlib.sha256(xml).hexdigest()==files['addon.xml']
 else:
  xml=(ROOT/'controller-source/addon/addon.xml').read_bytes()
  files={p.relative_to(ROOT/'controller-source/addon').as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'controller-source/addon').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo')}
  assert files==manifest['files'],'Release controller differs from manifest'
 tested=dict(files);tested['addon.xml']=hashlib.sha256(xml.replace(b'version="0.1.85"',b'version="0.1.84"',1)).hexdigest()
 assert tested==receipt['files'],'Release source differs from native-tested candidate'
 assert receipt.get('skin_Home_sha256')==manifest['skin']['Home.xml']==hashlib.sha256((ROOT/'controller-source/skin-overrides/Home.xml').read_bytes()).hexdigest()
 for key in ('natural_end','autoplay_started','back_hides_and_cancels','second_back_restores_row','disabled_skips_request','pointer_cancels','details_save_channel','settings_authorizations_preserved'):
  assert receipt['acceptance'].get(key) is True,'Missing Mac end-screen acceptance: '+key
 delay=receipt.get('autoplay_delay_seconds');assert type(delay) in (int,float) and isfinite(delay) and 15<=delay<17
 assert receipt.get('account_request_recognized') is True and receipt.get('exact_youtube_com_ranking_claimed') is False
 preserved=receipt['preservation'];assert preserved.get('core_preferences')==280 and preserved.get('protected_files')==301 and preserved.get('healthy_history_databases')==4 and preserved.get('unrelated_history_preserved') is True

def verify_discovery_acceptance(receipt,manifest,historical=False):
 assert receipt.get('schema')==1 and receipt.get('feature')=='discovery-first-page-1' and receipt.get('passed') is True
 assert receipt.get('devices')==['mac'] and receipt.get('runtime')=='21.3' and receipt.get('other_devices_accessed') is False
 assert receipt.get('release_controller')==manifest.get('controller')=='0.1.86'
 root=ROOT/'controller-source/addon'
 actual={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo')}
 assert manifest['files']==receipt['files'],'Discovery receipt differs from historical source'
 if historical:actual=manifest['files']
 else:assert actual==manifest['files'],'Discovery release source differs from native-tested source'
 previous=json.loads((ROOT/'controller-source/manifest85.json').read_text())
 changed={n for n in set(previous['files'])|set(actual) if previous['files'].get(n)!=actual.get(n)}
 assert changed=={'addon.xml','live_review.py','discovery_order.py'},'Unreviewed unrelated controller delta'
 assert manifest['skin']==previous['skin'],'Unrelated skin change'
 for field in ('next_back_stable_order','vertical_focus','watch_refresh_stable_order_focus','restored_provider_zero_vs_fresh_start','settings_authorizations_preserved'):
  assert receipt['acceptance'].get(field) is True,'Missing Mac discovery acceptance: '+field
 assert receipt.get('native_cases')==16
 assert receipt.get('catalog_sha256')==hashlib.sha256((SOURCE/'resources/discovery-lineup.json').read_bytes()).hexdigest(),'Discovery recipe catalogue changed'
 assert receipt['preservation']=={'protected_files':301,'core_preferences':280,'history_databases':4,'favorites_preserved':True,'unchanged_controller_files':315}

def verify_youtube_refresh_acceptance(receipt, manifest):
 assert receipt.get('schema')==1 and receipt.get('feature')=='youtube-freshness-1' and receipt.get('passed') is True
 assert receipt.get('runtime')=='21.3' and receipt.get('native_devices')==['mac'], 'Do not expand historical Mac proof to untested devices'
 assert receipt.get('controller')==manifest.get('controller')=='0.1.87'
 root=ROOT/'controller-source/addon'
 actual={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo')}
 assert actual==manifest['files']==receipt['files'], 'Freshness proof differs from current packaged source'
 previous=json.loads((ROOT/'controller-source/manifest86.json').read_text())
 changed={n for n in set(previous['files'])|set(actual) if previous['files'].get(n)!=actual.get(n)}
 assert changed=={'addon.xml','live_review.py','live_runtime.py','youtube_core.py','youtube_rows.py','youtube_provider.py'}, 'Unreviewed controller delta'
 assert manifest['skin']==previous['skin']
 guard=receipt.get('configuration_guard',{})
 assert guard.get('passed') is True, 'Native configuration-integrity acceptance is required'
 devices=guard.get('devices',{})
 assert set(devices)=={'mac','fire','apple'}, 'Configuration repair requires all three native devices'
 for device,check in devices.items():
  assert check.get('passed') is True and check.get('device')==device
  assert all(check.get(key) is True for key in ('failed_read_cannot_save_fallback','normal_window_loads_original_preferences','concurrent_atomic_writes_complete','real_layout_untouched'))
  assert check.get('files')=={n:actual[n] for n in ('live_review.py','live_runtime.py')}, 'Native configuration proof is stale'
 cache=receipt['cache'];path=ROOT/'compatibility/youtube-refresh'
 assert hashlib.sha256((path/'candidate/function_cache.py').read_bytes()).hexdigest()==cache['candidate_sha256']=='7418d1ba8afa569d0b0f3ccef78748c75c6b6560e8d096b6bf6c1e83efa830cb'
 assert hashlib.sha256((path/'upstream/function_cache.py').read_bytes()).hexdigest()==cache['upstream_sha256']=='ed3a13323d20c3c8fae40051c0572ecf5158b9dc59ae565615456f4ae0a784f4'
 proof=receipt['acceptance'];assert proof['passed'] and proof['settings_preserved'] and proof['authorizations_preserved']
 behavior=proof['native_behavior'];assert behavior['passed'] and behavior['active_category_pinned'] and behavior['durable_watch_cancellation'] and behavior['normal_home_restored']
 assert behavior['real_continuation']=={'before':50,'after':100,'anchor_metadata_preserved':True}
 assert all(behavior['early_rows_late_failure'].values())
 assert 0<proof['after_recommendations_seconds']<proof['after_complete_seconds']
 history=receipt['history'];assert history['full_video_local_history_updated'] is True and history['full_video_remote_http_statuses']==[204]*4
 assert history['preview_local_history_unchanged'] is True and history['preview_remote_reports']==0
 assert history['preview_flags']=={'use_local_history':False,'use_remote_history':False,'refresh_only':True}

def verify_youtube_context_acceptance(receipt):
 root=ROOT/'compatibility/youtube-context';manifest=json.loads((root/'manifest.json').read_text())
 assert receipt.get('schema')==1 and receipt.get('feature')=='youtube-context-1' and receipt.get('passed') is True
 assert receipt.get('runtime')=='21.3' and receipt.get('controller')=='0.1.87'
 assert receipt.get('candidate_sha256')==manifest['candidate_sha256']==hashlib.sha256((root/'candidate/xbmc_context.py').read_bytes()).hexdigest()
 assert receipt.get('upstream_sha256')==manifest['upstream_sha256']==hashlib.sha256((root/'upstream/xbmc_context.py').read_bytes()).hexdigest()
 assert set(receipt.get('devices',{}))=={'mac','fire','apple'}
 for check in receipt['devices'].values():
  assert check.get('passed') is True and check.get('complete_refresh') is True and check.get('main_and_subscriptions_visible') is True
  assert check.get('context_sha256')==manifest['candidate_sha256'] and check.get('rows_focus_artwork_progress_preserved') is True
  assert check['continuation']['after']>check['continuation']['before']>=50 and check['continuation']['anchor_and_metadata_preserved'] is True

def verify(folder):
 verify_release112_acceptance(json.loads((ROOT/'controller-source/usability-release112-verification.json').read_text()),json.loads((ROOT/'controller-source/manifest83.json').read_text()),require_v2=True)
 verify_release111_acceptance(json.loads((ROOT/'controller-source/youtube-release111-verification.json').read_text()),json.loads((ROOT/'controller-source/manifest82.json').read_text()))
 verify_release110_acceptance(json.loads((ROOT/'controller-source/youtube-release110-verification.json').read_text()),json.loads((ROOT/'controller-source/manifest81.json').read_text()))
 verify_youtube_acceptance(json.loads((ROOT/'controller-source/youtube-native-verification.json').read_text()),json.loads((ROOT/'controller-source/manifest75.json').read_text()))
 verify_stall_acceptance(json.loads((ROOT/'controller-source/youtube-stall-mac-verification.json').read_text()),json.loads((ROOT/'controller-source/youtube-stall-native-verification.json').read_text()),json.loads((ROOT/'controller-source/manifest76.json').read_text()))
 receipt=json.loads((ROOT/'compatibility/helper-progress/native-verification.json').read_text())
 approved=json.loads((SOURCE/'resources/managed-helper.json').read_text())
 verify_helper_progress_acceptance(receipt,approved)
 verify_umbrella_progress_acceptance(
  json.loads((ROOT/'compatibility/umbrella-progress/native-verification.json').read_text()),
  json.loads((ROOT/'compatibility/umbrella-progress/manifest-duration.json').read_text()))
 verify_shared_network_acceptance(
  json.loads((ROOT/'compatibility/shared-requests/native-verification.json').read_text()),
  json.loads((SOURCE/'resources/managed-network.json').read_text()))
 verify_autoplay_acceptance(
  json.loads((ROOT/'compatibility/autoplay-size/natural-verification.json').read_text()),
  json.loads((ROOT/'controller-source/manifest84.json').read_text()),
  json.loads((SOURCE/'resources/managed-umbrella.json').read_text()))
 verify_youtube_end_acceptance(json.loads((ROOT/'controller-source/youtube-end-native-verification.json').read_text()),json.loads((ROOT/'controller-source/manifest85.json').read_text()),historical=True)
 verify_discovery_acceptance(json.loads((ROOT/"controller-source/discovery-native-verification.json").read_text()),json.loads((ROOT/"controller-source/manifest86.json").read_text()),historical=True)
 verify_youtube_refresh_acceptance(json.loads((ROOT/"controller-source/youtube-refresh-native-verification.json").read_text()),json.loads((ROOT/"controller-source/manifest87.json").read_text()))
 verify_youtube_context_acceptance(json.loads((ROOT/'compatibility/youtube-context/native-verification.json').read_text()))
 spec=importlib.util.spec_from_file_location('managed',SOURCE/'resources/libs/managed_addons.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 with zipfile.ZipFile(folder/'plugin.program.blacklanturninstaller-1.0.24.zip') as z:
  assert z.testzip() is None
  installer={n:z.read(n) for n in z.namelist()}
  assert all(n.startswith('plugin.program.blacklanturninstaller/') for n in installer)
  expected_installer={'plugin.program.blacklanturninstaller/'+str(p.relative_to(SOURCE)):p.read_bytes() for p in SOURCE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and not p.name.endswith(('.pyc','.DS_Store'))}
  assert installer==expected_installer,'Installer ZIP differs from reviewed source'
 for ed in ('General','Apple-TV-Mac'):
  with zipfile.ZipFile(folder/f'BlackLanturn-{ed}-Kodi21-1.1.19.zip') as z:
   assert z.testzip() is None;m.verify_archive(z,umbrella=True,network=True,youtube=True);verify_playback_defaults(z);verify_display_defaults(z)
   p=json.loads(z.read('userdata/blacklanturn-build.json'))
   assert p['schema']==3 and p['preferences_policy']=='playback-trakt-youtube-umbrella-network-autoplay-1' and p['helper_patch']=='empty-cache-1' and p['installer_min_version']=='1.0.24'
   assert p['build_version']=='1.1.19' and p['network_patch']=='request-reliability-privacy-1' and p['umbrella_version']=='6.7.92' and p['umbrella_patch']=='event-progress-3'
   assert p['controller_version']=='0.1.87' and p['helper_search_patch']=='search-batch-1' and p['helper_playback_patch']=='sampled-progress-1'
   gui={n.get('id'):n.text for n in ET.fromstring(z.read('userdata/guisettings.xml'))}
   assert {k:gui[k] for k in ('filecache.memorysize','filecache.readfactor','filecache.buffermode','filecache.chunksize')}=={'filecache.memorysize':'64','filecache.readfactor':'400','filecache.buffermode':'4','filecache.chunksize':'131072'}
   assert next(n.text for n in ET.fromstring(z.read('userdata/addon_data/plugin.video.themoviedb.helper/settings.xml')) if n.get('id')=='artwork_quality')=='1'
   assert p['youtube_refresh_patch']=='youtube-freshness-2'
   assert hashlib.sha256(z.read('addons/plugin.video.youtube/resources/lib/youtube_plugin/kodion/context/xbmc/xbmc_context.py')).hexdigest()==json.loads((ROOT/'compatibility/youtube-context/manifest.json').read_text())['candidate_sha256']
   assert p['autoplay_patch']=='same-show-source-1'
   expected=json.loads((ROOT/'controller-source/manifest87.json').read_text())['files']
   actual={n[len('addons/script.blacklanturn.preview/'):]:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith('addons/script.blacklanturn.preview/')}
   assert actual==expected
   skin=json.loads((ROOT/'controller-source/manifest85.json').read_text())['skin']
   assert hashlib.sha256(z.read('addons/skin.blacklanturn.preview/xml/Home.xml')).hexdigest()==skin['Home.xml']
   assert ET.fromstring(z.read('addons/skin.blacklanturn.preview/addon.xml')).get('version')==skin['version']
   assert p['discovery_patch']=='discovery-first-page-1'
   from resources.libs import discovery_defaults
   discovery_defaults.verify_archive(z)
   assert p['youtube_end_patch']=='youtube-end-1' and p['skin_version']==skin['version']
   config=json.loads(z.read('userdata/addon_data/script.blacklanturn.preview/rows.json'))
   assert config.get('YouTubeEndSuggestions') is True and config.get('YouTubeEndAutoplay') is False
   for n,d in installer.items():assert z.read('addons/'+n)==d,'Installer mismatch'
   assert z.read('addons/plugin.program.blacklanturninstaller/resources/libs/managed_addons.py')==(SOURCE/'resources/libs/managed_addons.py').read_bytes()
 print('PASS: both packages, protected schema, exact installer, full managed Helper/Umbrella manifests historical progress evidence and historical natural Mac autoplay acceptance and retained historical YouTube end-screen acceptance plus historical Mac first-page discovery and exact-source Mac YouTube freshness acceptance; remote acceptance recorded separately')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('artifacts',type=Path);verify(p.parse_args().artifacts)
