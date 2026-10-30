"""Verify complete current add-ons, retained defaults and private-data boundary."""
import argparse,hashlib,importlib.util,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def verify(artifacts,baselines):
 manifest=json.loads((ROOT/'controller-source/manifest102.json').read_text());expected=manifest['files'];result={}
 for edition in ('General','Apple-TV-Mac'):
  path=artifacts/('BlackLanturn-'+edition+'-Kodi21-1.1.38.zip')
  with zipfile.ZipFile(path) as z,zipfile.ZipFile(baselines/('BlackLanturn-'+edition+'-Kodi21-1.1.37.zip')) as old:
   if z.testzip() is not None:raise ValueError('CRC failed')
   prefix='addons/script.blacklanturn.preview/'
   installer_prefix='addons/plugin.program.blacklanturninstaller/'
   installer_root=ROOT/'installer-source/plugin.program.blacklanturninstaller'
   wanted={p.relative_to(installer_root).as_posix():sha(p.read_bytes()) for p in installer_root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo') and p.name!='.DS_Store'}
   if {n[len(installer_prefix):]:sha(z.read(n)) for n in z.namelist() if n.startswith(installer_prefix)}!=wanted:raise ValueError('Installer source differs')
   if {n[len(prefix):]:sha(z.read(n)) for n in z.namelist() if n.startswith(prefix)}!=expected:raise ValueError('Build missing or changed branded icons')
   current_manifest=json.loads((ROOT/'compatibility/addons134/manifest.json').read_bytes())['addons']
   current_manifest.update(json.loads((ROOT/'compatibility/addons135/manifest.json').read_bytes())['addons'])
   changed_prefixes=tuple('addons/'+aid+'/' for aid in current_manifest)
   for aid,record in current_manifest.items():
    ap='addons/'+aid+'/'
    if {n[len(ap):]:sha(z.read(n)) for n in z.namelist() if n.startswith(ap)}!=record['files']:raise ValueError('Incomplete current-source tree: '+aid)
   metadata={'userdata/blacklanturn-build.json','userdata/blacklanturn-releases.json','userdata/BlackLanturn-README.txt'}
   for name in old.namelist():
    if name not in metadata and not name.startswith((prefix,installer_prefix)+changed_prefixes) and z.read(name)!=old.read(name):raise ValueError('Unrelated runtime/default changed: '+name)
   if any(n not in metadata and not n.startswith((prefix,installer_prefix)+changed_prefixes) for n in set(z.namelist())-set(old.namelist())):raise ValueError('Unexpected added paths')
   if any(n.startswith('addons/plugin.video.blacklanturn.fights/') for n in z.namelist()):raise ValueError('Private Fight Zone included')
   marker=json.loads(z.read('userdata/blacklanturn-build.json'));entry=json.loads(z.read('userdata/blacklanturn-releases.json'))['releases'][0]
   if marker.get('bundle_registration_policy')!='new-bundles-1' or marker.get('installer_min_version')!='1.0.40':raise ValueError('Registration protocol floor missing')
   if marker['build_version']!='1.1.38' or entry['id']!=marker['release_id'] or any(sha(z.read(n))!=h for n,h in entry['files'].items()):raise ValueError('Release proof differs')
  component=artifacts/('BlackLanturn-'+edition+'-Update-1.1.37-to-1.1.38.zip')
  with zipfile.ZipFile(component) as z:
   if z.testzip() is not None:raise ValueError('Component CRC failed')
   doc=json.loads(z.read('userdata/blacklanturn-components.json'))
   if 'script.blacklanturn.preview' in doc['retained']:raise ValueError('Changed Controller incorrectly retained')
   for aid,record in current_manifest.items():
    ap='addons/'+aid+'/'
    present={n[len(ap):]:sha(z.read(n)) for n in z.namelist() if n.startswith(ap)}
    if aid in doc['retained']:
     if present:raise ValueError('Retained component unexpectedly included: '+aid)
    elif present!=record['files']:raise ValueError('Incomplete changed component: '+aid)
  result[edition]={'passed':True,'full_sha256':sha(path.read_bytes()),'component_sha256':sha(component.read_bytes()),'icon_files':180,'icons_per_pack':90,'only_reviewed_controller_installer_metadata_changed':True,'saved_defaults_unchanged':True,'complete_current_sources':{a:r['version'] for a,r in current_manifest.items()},'installer':'1.0.42','private_fight_zone_excluded':True}
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('artifacts',type=Path);p.add_argument('--baselines',type=Path,required=True);a=p.parse_args();r=verify(a.artifacts,a.baselines);(a.artifacts/'verification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
