"""Source-bound Mac acceptance; keep untested devices explicitly excluded."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CASES=('quiet_first_run','actual_install_notice','view_changes','back_dismiss','dismiss_persists','preference_persists','manual_installer_route','no_repeated_notice','settings_preserved','authorizations_preserved')
def verify(receipt,manifest):
 assert receipt.get('schema')==1 and receipt.get('feature')=='update-notes-1' and receipt.get('passed') is True
 assert receipt.get('controller')==manifest.get('controller')=='0.1.88' and receipt.get('installer')=='1.0.26'
 assert receipt.get('runtime')=='21.3'
 assert receipt.get('native_devices') in (['mac'],['mac','apple'])
 assert receipt.get('files')==manifest['files'],'Update notice acceptance source is stale'
 for device in receipt['native_devices']:
  assert all(receipt.get('native',{}).get(device,{}).get(case) is True for case in CASES),'Incomplete native update-notice acceptance: '+device
 assert receipt.get('automated',{}).get('playback_deferral') is True
 assert receipt.get('automated',{}).get('monitor_error_isolation') is True
 assert receipt.get('automated',{}).get('complete_inventory') is True
 root=ROOT/'controller-source/addon'
 actual={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo')}
 assert actual==manifest['files'],'Current update notice source changed'
 installer=ROOT/'installer-source/plugin.program.blacklanturninstaller'
 installed={p.relative_to(installer).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in installer.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo')}
 assert receipt.get('installer_files')==installed,'Installer update-notice acceptance source is stale'
 return True
