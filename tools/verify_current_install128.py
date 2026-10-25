"""Require fresh native install-core evidence bound to the exact release bytes.

General Android identity is simulated in this isolated macOS acceptance. It is
not physical Fire Stick or tvOS playback evidence. UI transport is independently
covered by the exact-artifact Wizard matrix.
"""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
INSTALLER='plugin.program.blacklanturninstaller-1.0.33.zip'
NAMES=(INSTALLER,'BlackLanturn-General-Kodi21-1.1.28.zip','BlackLanturn-Apple-TV-Mac-Kodi21-1.1.28.zip')
def verify(receipt,folder):
 assert receipt.get('passed') is True and receipt.get('network_blocked') is True and receipt.get('personal_profile_denied') is True
 assert receipt.get('personal_profile_accessed') is False,'Personal profile isolation was not proved'
 actual={n:hashlib.sha256((folder/n).read_bytes()).hexdigest() for n in NAMES}
 assert receipt.get('artifacts')==actual,'Current install-core receipt does not match these release artifacts'
 cases=receipt.get('cases');assert isinstance(cases,list) and len(cases)==6
 assert {(c.get('edition'),c.get('mode')) for c in cases}=={(e,m) for e in ('General','Apple-TV-Mac') for m in ('clean','standard','update')}
 for c in cases:
  assert c.get('passed') is True and type(c.get('source_files_exact')) is int and c['source_files_exact']>3000
  assert all(c.get(k) is True for k in ('release_state_verified','native_registry_preserved','synthetic_history_choice_preserved'))
  assert c.get('payload_sha256')==actual['BlackLanturn-'+c['edition']+'-Kodi21-1.1.28.zip'] and c.get('installer_sha256')==actual[INSTALLER]
  if c['mode']!='clean':assert c.get('synthetic_playback_state_paths_preserved')==12
  else:assert c.get('clean_cleared_synthetic_playback_state') is True
  if c['mode']=='update': assert c.get('native_managed_versions_verified') is True and c.get('all_saved_data_unchanged') is True and c.get('unrelated_addon_unchanged') is True
 return True

def verify_startup_notice(receipt,artifacts,controller_files,installer_files):
 """Normal startup in an isolated old-build profile; no personal acknowledgement."""
 assert receipt.get('passed') is True and receipt.get('runtime')=='21.3'
 assert receipt.get('personal_profile_accessed') is False and receipt.get('build_version')=='1.1.28'
 assert all(receipt.get(n) is True for n in ('normal_startup','available_notice','update_dispatches_inplace','offline_update_message','preferences_history_preserved')),'Normal startup/available notice acceptance missing'
 assert receipt.get('artifacts')==artifacts,'Startup notice artifacts differ'
 assert receipt.get('controller_files')==controller_files and receipt.get('installer_files')==installer_files,'Startup notice source differs'
 return True

def verify_self_update(receipt,artifacts,controller_files,installer_files):
 """Fresh32 capability proof; never imply the old31 core could self-replace."""
 assert receipt.get('passed') is True and receipt.get('native_kodi')=='21.3'
 assert receipt.get('personal_profile_accessed') is False
 assert all(receipt.get(k) is True for k in ('upgraded','registered','close_later_exits','settings_preserved','cold_recovery_missing_installer','normal_startup_recovery','restart_required','fixture_metadata_only')),'Incomplete native SELF swap/recovery acceptance'
 assert receipt.get('controller_files')==controller_files and receipt.get('installer_files')==installer_files,'SELF recovery source differs'
 assert receipt.get('artifacts')==artifacts,'SELF recovery artifact set differs'
 assert receipt.get('fixture_version')=='1.0.34' and receipt.get('final_restored_installer')=='1.0.33'
 assert receipt.get('initial_capability')=='Installer33 installed first by wrapped addon package + native local-addon registry refresh; no old31 SELF capability claimed','Native fixture must not claim old31 self-update capability'
 evidence=receipt.get('evidence',{});assert set(evidence)=={'native_self_update','cold_recovery'},'Missing retained native SELF/recovery evidence'
 native=_native_evidence(evidence['native_self_update']);cold=_native_evidence(evidence['cold_recovery'])
 assert native.get('passed') is True and native.get('native_kodi')=='21.3' and native.get('personal_profile_accessed') is False
 assert all(native.get(k) is True for k in ('upgraded','registered','close_later_exits','settings_preserved','cold_recovery_missing_installer','fixture_metadata_only','exact_final_artifact_restored')),'Native SELF body does not establish capability'
 assert native.get('controller_files')==controller_files and native.get('installer_files')==installer_files and native.get('artifacts')==artifacts,'Native SELF body source/artifacts differ'
 assert native.get('fixture_version')=='1.0.34' and native.get('final_restored_installer')=='1.0.33' and native.get('initial_capability')==receipt['initial_capability']
 dialogs=native.get('native_dialogs',[])
 assert any(x.get('label')=='Update' and x.get('answer') is True for x in dialogs) and any(x.get('label')=='Close later' and x.get('answer') is False for x in dialogs),'Real native Update/Close later choices missing'
 assert native.get('completion_default_close_kodi') is True,'Native completion did not focus Close Kodi'
 assert native.get('navigation_open_count')==1 and native.get('intentional_process_exit')==127,'Native handoff or actual process loss missing'
 assert native.get('cold_backup_files')==installer_files,'Cold process-loss backup source differs'
 journal=native.get('journal_at_process_loss',{});assert journal.get('schema')==1 and journal.get('status')=='applying'
 entry=journal.get('addons',{}).get('plugin.program.blacklanturninstaller',{})
 assert entry.get('before')==installer_files and entry.get('started') is True and entry.get('enabled_before') is True,'Missing durable SELF intent at process loss'
 after=entry.get('after',{});assert set(after)==set(installer_files) and after.get('addon.xml')!=installer_files.get('addon.xml') and all(after[n]==digest for n,digest in installer_files.items()if n!='addon.xml'),'SELF fixture changed implementation beyond metadata'
 assert cold.get('passed') is True and cold.get('native_kodi')=='21.3' and str(cold.get('runtime','')).startswith('21.3')
 assert cold.get('personal_profile_accessed') is False and all(cold.get(k) is True for k in ('network_blocked','personal_profile_denied','normal_startup_recovery','restart_required','settings_preserved')),'Cold normal startup recovery incomplete'
 assert cold.get('restored_installer')=='1.0.33' and cold.get('installer_files')==installer_files and cold.get('controller_files')==controller_files and cold.get('artifacts')==artifacts,'Cold recovery exact source/artifacts differ'
 assert cold.get('installer_enabled') is True and cold.get('addon_constructor_usable') is True and cold.get('native_installer_version')=='1.0.33','Cold recovery did not restore a usable enabled native Installer'
 assert cold.get('native_dialog_heading')=='BlackLanturn update recovered' and all(word in cold.get('native_dialog_body','').lower()for word in ('close','reopen')),'Native restart requirement was not observed'
 assert type(cold.get('protected_paths_compared')) is int and cold['protected_paths_compared']>=12,'Cold recovery preservation proof missing'
 return True

def _native_evidence(ref):
 path=Path(ref.get('path',''));relative=Path('compatibility/current-addons/release128-evidence')
 assert not path.is_absolute() and path.parts[:3]==relative.parts and '..'not in path.parts,'Native evidence must be retained in the public128 evidence folder'
 target=ROOT/path;assert target.is_file() and target.resolve().is_relative_to((ROOT/relative).resolve()),'Native evidence missing or outside accepted folder'
 raw=target.read_bytes();assert hashlib.sha256(raw).hexdigest()==ref.get('sha256'),'Native evidence bytes differ from receipt'
 body=json.loads(raw);assert isinstance(body,dict),'Native evidence body is not an object'
 return body


def verify_details_hero(receipt,artifacts,controller_files):
 assert receipt.get('passed')is True and receipt.get('synthetic_local_media')is True
 assert receipt.get('personal_profile_accessed')is False and receipt.get('provider_overrides')is False
 assert receipt.get('artwork_captured')is True and receipt.get('preview_played')is True and receipt.get('compact')is True
 assert receipt.get('controller_files')==controller_files and receipt.get('artifacts')==artifacts,'Details framing acceptance source differs'
 assert receipt.get('visual_review')=={'artwork_compact':True,'preview_compact':True,'left_fade':True,'right_fade':True,'bottom_fade':True,'metadata_retained':True},'Details hero visuals require review'
 return True
