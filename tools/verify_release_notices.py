"""Current curated release acceptance; historical inventory notices are not a gate."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CASES=('available_notice','view_changes','later_button','update_opens_installer','completed_notice','dismiss_button','persistent_no_repeat','preference_persists','settings_preserved','authorizations_preserved')
def inventory(root):return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo')}
def verify(receipt,manifest,*,historical=False):
 assert receipt.get('schema')==1 and receipt.get('feature')=='curated-release-notices-1' and receipt.get('passed') is True
 assert receipt.get('controller')==manifest.get('controller')=='0.1.90' and receipt.get('installer')=='1.0.27'
 assert receipt.get('runtime')=='21.3' and receipt.get('native_devices') in (['mac'],['mac','fire'])
 assert receipt.get('files')==manifest['files'],'Recorded notice source differs from native acceptance'
 current=inventory(ROOT/'controller-source/addon');installer=inventory(ROOT/'installer-source/plugin.program.blacklanturninstaller')
 if historical:
  for name in ('release_updates.py','update_notes_ui.py','resources/skins/Default/1080i/UpdateNotice.xml','resources/skins/Default/1080i/UpdateNotes.xml'):
   assert current[name]==manifest['files'][name],'Notice implementation changed; fresh notice acceptance required'
  assert {k:v for k,v in installer.items() if k!='addon.xml'}=={k:v for k,v in receipt['installer_files'].items() if k!='addon.xml'},'Installer behavior changed; fresh notice acceptance required'
 else:
  assert receipt['files']==current,'Current release source differs from native acceptance'
  assert receipt.get('installer_files')==installer,'Installer differs from accepted install-core tests'
 for device in receipt['native_devices']:
  assert all(receipt.get('native',{}).get(device,{}).get(case) is True for case in CASES),'Incomplete native release-notice acceptance: '+device
 assert all(receipt.get('automated',{}).get(case) is True for case in ('playback_deferral','monitor_error_isolation','no_inventory','failed_install_no_success'))
 return True
