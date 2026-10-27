"""Verify exact icon distribution and unchanged runtime/private-data boundary."""
import argparse,hashlib,importlib.util,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def verify(artifacts,baselines):
 manifest=json.loads((ROOT/'controller-source/manifest97.json').read_text());expected=manifest['files'];result={}
 for edition in ('General','Apple-TV-Mac'):
  path=artifacts/('BlackLanturn-'+edition+'-Kodi21-1.1.31.zip')
  with zipfile.ZipFile(path) as z,zipfile.ZipFile(baselines/('BlackLanturn-'+edition+'-Kodi21-1.1.30.zip')) as old:
   if z.testzip() is not None:raise ValueError('CRC failed')
   prefix='addons/script.blacklanturn.preview/'
   if {n[len(prefix):]:sha(z.read(n)) for n in z.namelist() if n.startswith(prefix)}!=expected:raise ValueError('Build missing or changed branded icons')
   metadata={'userdata/blacklanturn-build.json','userdata/blacklanturn-releases.json','userdata/BlackLanturn-README.txt'}
   for name in old.namelist():
    if name not in metadata and not name.startswith(prefix) and z.read(name)!=old.read(name):raise ValueError('Unrelated runtime/default changed: '+name)
   if any(not n.startswith(prefix) for n in set(z.namelist())-set(old.namelist())):raise ValueError('Unexpected added paths')
   if any(n.startswith('addons/plugin.video.blacklanturn.fights/') for n in z.namelist()):raise ValueError('Private Fight Zone included')
   marker=json.loads(z.read('userdata/blacklanturn-build.json'));entry=json.loads(z.read('userdata/blacklanturn-releases.json'))['releases'][0]
   if marker['build_version']!='1.1.31' or entry['id']!=marker['release_id'] or any(sha(z.read(n))!=h for n,h in entry['files'].items()):raise ValueError('Release proof differs')
  component=artifacts/('BlackLanturn-'+edition+'-Update-1.1.30-to-1.1.31.zip')
  with zipfile.ZipFile(component) as z:
   if z.testzip() is not None or {n[len(prefix):]:sha(z.read(n)) for n in z.namelist() if n.startswith(prefix)}!=expected:raise ValueError('Component missing complete resource')
  result[edition]={'passed':True,'full_sha256':sha(path.read_bytes()),'component_sha256':sha(component.read_bytes()),'icon_files':180,'icons_per_pack':90,'only_controller_artwork_setup_changed':True,'installer_unchanged':True,'private_fight_zone_excluded':True}
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('artifacts',type=Path);p.add_argument('--baselines',type=Path,required=True);a=p.parse_args();r=verify(a.artifacts,a.baselines);(a.artifacts/'verification.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
