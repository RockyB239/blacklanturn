"""Require fresh native install-core evidence bound to the exact release bytes.

General Android identity is simulated in this isolated macOS acceptance. It is
not physical Fire Stick or tvOS playback evidence. UI transport is independently
covered by the exact-artifact Wizard matrix.
"""
import hashlib
INSTALLER='plugin.program.blacklanturninstaller-1.0.30.zip'
NAMES=(INSTALLER,'BlackLanturn-General-Kodi21-1.1.25.zip','BlackLanturn-Apple-TV-Mac-Kodi21-1.1.25.zip')
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
  assert c.get('payload_sha256')==actual['BlackLanturn-'+c['edition']+'-Kodi21-1.1.25.zip'] and c.get('installer_sha256')==actual[INSTALLER]
  if c['mode']!='clean':assert c.get('synthetic_playback_state_paths_preserved')==12
  else:assert c.get('clean_cleared_synthetic_playback_state') is True
  if c['mode']=='update': assert c.get('native_managed_versions_verified') is True and c.get('all_saved_data_unchanged') is True and c.get('unrelated_addon_unchanged') is True
 return True
