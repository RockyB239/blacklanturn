"""Current curated release acceptance; historical inventory notices are not a gate."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CASES=('available_notice','view_changes','later_button','update_opens_installer','completed_notice','dismiss_button','persistent_no_repeat','preference_persists','settings_preserved','authorizations_preserved')
def inventory(root):return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo')}
def verify(receipt,manifest,*,historical=False,reminder_receipt=None):
 assert receipt.get('schema')==1 and receipt.get('feature')=='curated-release-notices-1' and receipt.get('passed') is True
 assert receipt.get('controller')==manifest.get('controller')=='0.1.90' and receipt.get('installer')=='1.0.27'
 assert receipt.get('runtime')=='21.3' and receipt.get('native_devices') in (['mac'],['mac','fire'])
 assert receipt.get('files')==manifest['files'],'Recorded notice source differs from native acceptance'
 current=inventory(ROOT/'controller-source/addon');installer=inventory(ROOT/'installer-source/plugin.program.blacklanturninstaller')
 if historical:
  # Historical acceptance certifies unchanged state/notes engine only.
  # Release126 separately requires current source-bound Updates/notes UI proof.
  for name in ('release_updates.py','update_notes.py'):
   assert current[name]==manifest['files'][name],'Notice state/notes changed; fresh notice acceptance required'
  changed=('update_notes_ui.py','resources/skins/Default/1080i/UpdateNotice.xml')
  if any(current[n]!=manifest['files'][n] for n in changed):
   assert reminder_receipt and reminder_receipt.get('passed') is True,'Fresh reminder native acceptance required'
   assert reminder_receipt.get('native_kodi_launches')==2 and reminder_receipt.get('protected_settings_paths_compared',0)>=3,'Reminder restart/settings proof missing'
   assert reminder_receipt.get('files')=={n:current[n] for n in changed},'Reminder source differs from native acceptance'
   assert all(reminder_receipt.get('cases',{}).get(n) is True for n in ('later_repeats_next_session','same_session_once','never_only_this_release','future_release_not_suppressed','completed_once','button_visible','settings_preserved','legacy_later_not_suppressed')),'Incomplete native reminder acceptance'
  # Historical notice visuals/state do not certify the changed install core.
  # Current Wizard completion/preservation must pass fresh exact-artifact native
  # acceptance separately before publication (release123 install matrix).
  for name in ('resources/libs/release_notice_state.py','resources/libs/update_notes_state.py'):
   assert installer.get(name)==receipt['installer_files'].get(name),'Notice state implementation changed; fresh notice acceptance required'

 else:
  assert receipt['files']==current,'Current release source differs from native acceptance'
  assert receipt.get('installer_files')==installer,'Installer differs from accepted install-core tests'
 for device in receipt['native_devices']:
  assert all(receipt.get('native',{}).get(device,{}).get(case) is True for case in CASES),'Incomplete native release-notice acceptance: '+device
 assert all(receipt.get('automated',{}).get(case) is True for case in ('playback_deferral','monitor_error_isolation','no_inventory','failed_install_no_success'))
 return True
