"""Mac feature acceptance; exact artifact install/startup proof is a separate gate.

The feature run loaded local4/local3 through normal wrapped add-on ZIP updates.
Only addon.xml's version and one terminal newline are normalized; this does not claim a build transaction
or physical Fire/tvOS acceptance. Historical component receipts remain immutable.
"""
import hashlib,json,re,xml.etree.ElementTree as ET,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FEATURES=('updates_page_and_distinct_icons','curated_notes_scroll_and_back','recommendations_and_paging','correct_secondary_preview_played','cached_preview_without_provider_lookup')
def inventory(root):
 return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo') and p.name!='.DS_Store'}
def evidence(receipt,key):
 ref=receipt['evidence'][key];path=Path(ref['path'])
 assert path.parts[:2]==('controller-source','release126-evidence') and '..' not in path.parts,'Evidence outside public acceptance folder'
 raw=(ROOT/path).read_bytes()
 assert hashlib.sha256(raw).hexdigest()==ref.get('sha256'),'Native evidence changed: '+key
 return json.loads(raw)
def verify(receipt,manifest,*,historical=False):
 assert receipt.get('schema')==1 and receipt.get('feature')=='approved-polish-126' and receipt.get('passed') is True
 assert receipt.get('controller')==manifest.get('controller')=='0.1.93' and receipt.get('installer')=='1.0.31'
 assert receipt.get('runtime')=='21.3' and receipt.get('native_devices')==['mac'] and receipt.get('other_devices_accessed') is False
 assert receipt.get('build_transactions_claimed') is False,'Feature add-on update is not a build install matrix'
 assert all(receipt.get('native',{}).get(k) is True for k in FEATURES),'Incomplete feature acceptance'
 assert receipt.get('files')==manifest['files'],'Historical feature controller identity differs'
 if not historical:
  assert receipt['files']==inventory(ROOT/'controller-source/addon'),'Feature controller source differs'
  assert receipt.get('installer_files')==inventory(ROOT/'installer-source/plugin.program.blacklanturninstaller'),'Feature installer source differs'
 # Historical mode revalidates this immutable run only. Current-source linkage
 # is enforced separately by verify_release127's unchanged-file/method checks.
 binding=evidence(receipt,'installed_source')
 accepted_installer=None
 if historical:
  with zipfile.ZipFile(ROOT/'plugin.program.blacklanturninstaller/plugin.program.blacklanturninstaller-1.0.31.zip')as z:
   prefix='plugin.program.blacklanturninstaller/'
   assert z.testzip() is None and all(n.startswith(prefix)for n in z.namelist())
   accepted_installer={n[len(prefix):]:z.read(n)for n in z.namelist()if not n.endswith('/')}
  assert {n:hashlib.sha256(v).hexdigest()for n,v in accepted_installer.items()}==receipt['installer_files'],'Historical Installer31 differs from complete126 acceptance'
 for component,aid,root,files,tested,final in (
  ('controller','script.blacklanturn.preview',ROOT/'controller-source/addon',receipt['files'],'0.1.93~local4','0.1.93'),
  ('installer','plugin.program.blacklanturninstaller',ROOT/'installer-source/plugin.program.blacklanturninstaller',receipt['installer_files'],'1.0.31~local3','1.0.31')):
  n=receipt['normalization'][component]
  assert n.get('kind')=='addon.xml version and terminal newline only' and n.get('tested_version')==tested and n.get('release_version')==final
  xml=accepted_installer['addon.xml'] if historical and component=='installer' else (root/'addon.xml').read_bytes();loaded=ET.fromstring(xml).get('version')
  if historical:xml=xml.replace(('version="'+loaded+'"').encode(),('version="'+final+'"').encode(),1)
  assert ET.fromstring(xml).get('version')==final and hashlib.sha256(xml).hexdigest()==files['addon.xml'],'Historical metadata changed beyond version'
  needle=('version="'+final+'"').encode();assert xml.count(needle)==1
  normalized=xml.replace(needle,('version="'+tested+'"').encode(),1)
  assert n.get('release_terminal_newline_added') is True and normalized.endswith(b'\n') and not normalized.endswith(b'\n\n')
  normalized=normalized[:-1]
  expected=dict(files,**{'addon.xml':hashlib.sha256(normalized).hexdigest()})
  assert n.get('tested_files')==binding[aid]['files']==expected,'Native implementation changed beyond metadata normalization'
  assert binding[aid]['version']==tested and binding[aid]['ordinary_zip_install'] is True
 d=evidence(receipt,'discovery');p=evidence(receipt,'preview');u=evidence(receipt,'updates');h=evidence(receipt,'preservation')
 assert d.get('passed') is True and d.get('native_window') is True and d.get('temporary_acceptance_subclass') is True
 assert d.get('paging_passed') is True and 'info=recommendations' in d.get('related_path','')
 assert d.get('playing') is True and d.get('preview_stopped') is True and d.get('cached_lookup_requests')==0
 assert p.get('passed') is True and p.get('source_request_count')==1 and len(p.get('title_checks',{}))<=6
 assert d.get('preview_id') in p.get('approved_ids',[]) and p.get('wrong_series_id') not in p.get('approved_ids',[])
 assert u.get('heading')=='Updates' and u.get('notes_window')==13003 and u.get('check',{}).get('ok') is True and u['check'].get('notes_ok') is True
 assert u.get('notes_scrolled_and_back_observed') is True and u.get('icons_distinct_observed') is True
 assert h.get('passed') is True and h.get('core_preferences_checked')==280 and h.get('setting_values_checked',0)>=3433
 assert h.get('unrelated_addon_source_checked',0)>=22612 and h.get('package_source_differences')==[]
 assert h.get('core_differences')==h.get('unrelated_source_differences')==[] and h.get('settings_differences')=={}
 assert h.get('history_preserved') is True and receipt.get('preservation')=={'history_preserved':True,'notice_preferences_and_history_preserved':True}
 state=h.get('notice_state_files',{});assert set(state)=={'userdata/addon_data/script.blacklanturn.preview/release-notices.json','userdata/blacklanturn-install-complete.json'}
 assert all(v.get('before')==v.get('after') and re.fullmatch('[0-9a-f]{64}',v.get('before','')) for v in state.values()),'Notice preference/history bytes changed'
 return True
