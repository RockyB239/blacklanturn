"""Require fresh native install-core evidence bound to the exact release bytes.

General Android identity is simulated in this isolated macOS acceptance. It is
not physical Fire Stick or tvOS playback evidence. UI transport is independently
covered by the exact-artifact Wizard matrix.
"""
import hashlib,json,re,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
INSTALLER='plugin.program.blacklanturninstaller-1.0.34.zip'
NAMES=(INSTALLER,'BlackLanturn-General-Kodi21-1.1.29.zip','BlackLanturn-Apple-TV-Mac-Kodi21-1.1.29.zip')
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
  assert c.get('payload_sha256')==actual['BlackLanturn-'+c['edition']+'-Kodi21-1.1.29.zip'] and c.get('installer_sha256')==actual[INSTALLER]
  if c['mode']!='clean':assert c.get('synthetic_playback_state_paths_preserved')==12
  else:assert c.get('clean_cleared_synthetic_playback_state') is True
  if c['mode']=='update': assert c.get('native_managed_versions_verified') is True and c.get('all_saved_data_unchanged') is True and c.get('unrelated_addon_unchanged') is True
 return True

def verify_presentation(receipt,artifacts,installer):
 assert receipt.get('passed') is True and receipt.get('personal_profile_accessed') is False
 assert receipt.get('runtime','').startswith('21.3') and receipt.get('network_blocked') is True and receipt.get('personal_profile_denied') is True
 assert receipt.get('artifacts')==artifacts and receipt.get('installer_files')==installer
 for key in ('stale_status_overridden','initial_update_focused','return_focus_preserved','new_entry_update_focused','no_page_network','saved_data_unchanged','real_native_window'):
  assert receipt.get(key) is True,'Missing native presentation evidence: '+key
 return True

def verify_inherited(controller,installer):
 """Only unchanged paths inherit128 self-recovery/notice/Details evidence."""
 def load(name):
  spec=importlib.util.spec_from_file_location(name,ROOT/('tools/'+name+'.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
 source=load('verify_release129');old=load('verify_current_install128')
 previous=json.loads((ROOT/'compatibility/current-addons/native-install-acceptance-1.1.28.json').read_text())
 baseline=source.baseline_installer()
 assert all(installer[n]==v for n,v in baseline.items() if n not in source.CHANGED)
 old.verify_startup_notice(previous['startup_notice'],previous['artifacts'],controller,baseline)
 old.verify_self_update(previous['self_update'],previous['artifacts'],controller,baseline)
 old.verify_details_hero(previous['details_hero'],previous['artifacts'],controller)
 return True
