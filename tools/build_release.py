"""Reproducible 1.1.2 release from verified clean baselines, never live profiles."""
import argparse,ast,hashlib,importlib.util,json,re,sys,xml.etree.ElementTree as ET,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'installer-source/plugin.program.blacklanturninstaller'
PATCH=ROOT/'compatibility/helper-empty-cache'
BASE_HASHES={'General':'8a327637ff44e629aa29ff40235719b0c28984e0a1fc44bda226f504f0fabf98','Apple-TV-Mac':'872ff68f64f2b89450480aa56d156b103e25cdcf47467e1395aedd51c567e407'}
def sha(data):return hashlib.sha256(data).hexdigest()
def zipwrite(path,data):
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for name,raw in sorted(data.items()):
   e=zipfile.ZipInfo(name,(2026,10,16,0,0,0));e.compress_type=zipfile.ZIP_DEFLATED;e.external_attr=0o100644<<16;z.writestr(e,raw)
 with zipfile.ZipFile(path) as z:assert z.testzip() is None

def build(baselines,output):
 output.mkdir(parents=True,exist_ok=True)
 installer={str(p.relative_to(SOURCE)):p.read_bytes() for p in SOURCE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and not p.name.endswith(('.pyc','.DS_Store'))}
 assert ET.fromstring(installer['addon.xml']).get('version')=='1.0.10'
 zipwrite(output/'plugin.program.blacklanturninstaller-1.0.10.zip',{'plugin.program.blacklanturninstaller/'+n:d for n,d in installer.items()})
 spec=importlib.util.spec_from_file_location('managed',SOURCE/'resources/libs/managed_addons.py');managed=importlib.util.module_from_spec(spec);spec.loader.exec_module(managed)
 for edition,expected in BASE_HASHES.items():
  source=baselines/f'BlackLanturn-{edition}-Kodi21-1.1.1.zip';assert sha(source.read_bytes())==expected,'Baseline changed'
  with zipfile.ZipFile(source) as z:
   assert z.testzip() is None;before={n:z.read(n) for n in z.namelist()}
  data=dict(before);prefix='addons/plugin.program.blacklanturninstaller/'
  data={n:d for n,d in data.items() if not n.startswith(prefix)}
  data.update({prefix+n:d for n,d in installer.items()})
  for name,rel in [('lists_default.py','lists_default.py'),('lists_trakt.py','trakt/lists_standard.py')]:
   target='addons/plugin.video.themoviedb.helper/resources/tmdbhelper/lib/items/directories/'+rel
   manifest=json.loads((PATCH/'manifest.json').read_text());assert sha(before[target])==manifest[name]['before'];data[target]=(PATCH/'candidate'/name).read_bytes();assert sha(data[target])==manifest[name]['after']
  marker=json.loads(data['userdata/blacklanturn-build.json']);marker.update(schema=2,build_version='1.1.2',helper_patch='empty-cache-1',installer_min_version='1.0.10')
  data['userdata/blacklanturn-build.json']=json.dumps(marker,indent=2).encode()
  data['userdata/BlackLanturn-README.txt']=(before['userdata/BlackLanturn-README.txt'].decode()+ '\n\nRelease 1.1.2: Helper failure-cache repair and managed updates. Requires BlackLanturn Installer 1.0.10. TMDb Helper automatic updates are disabled for this addon only; reviewed Helper updates arrive in BlackLanturn build updates. Leave this protection enabled. Manually reinstalling Helper or enabling its auto-update bypasses it. Other addons retain their update settings.\n').encode()
  allowed={prefix+n for n in installer}|{n for n in before if n.startswith(prefix)}|{'userdata/blacklanturn-build.json','userdata/BlackLanturn-README.txt'}|{'addons/plugin.video.themoviedb.helper/resources/tmdbhelper/lib/items/directories/'+n for n in ('lists_default.py','trakt/lists_standard.py')}
  changed={n for n in set(before)|set(data) if before.get(n)!=data.get(n)};assert changed<=allowed
  for n,raw in data.items():
   assert n.startswith(('addons/','userdata/')) and '..' not in n.split('/')
   assert not any(x in n.split('/') for x in ('__pycache__','.git','packages','__MACOSX'))
   assert not n.endswith(('.pyc','.pyo','.so','.dylib','.dll','.exe','.DS_Store'))
   assert not raw.startswith((b'\x7fELF',b'\xcf\xfa\xed\xfe',b'\xfe\xed\xfa\xcf',b'MZ'))
   if n.endswith('/addon.xml'):ET.fromstring(raw)
   if n.endswith('.py') and n!=prefix+'resources/libs/zipfile.py':ast.parse(raw,n)
   if n.startswith('userdata/') and n not in ('userdata/blacklanturn-build.json','userdata/BlackLanturn-README.txt'):assert raw==before[n],'Userdata changed'
  addons={n.split('/')[1]:ET.fromstring(raw) for n,raw in data.items() if n.startswith('addons/') and n.endswith('/addon.xml')}
  system={'xbmc.python','xbmc.gui','xbmc.json','xbmc.addon','kodi.resource','script.module.pil','script.module.pycryptodome','inputstream.adaptive'}
  for aid,addon in addons.items():
   for dep in addon.findall('./requires/import'):
    if dep.get('optional')=='true':continue
    assert dep.get('addon') in addons or dep.get('addon') in system,(aid,dep.get('addon'))
  out=output/f'BlackLanturn-{edition}-Kodi21-1.1.2.zip';zipwrite(out,data)
  with zipfile.ZipFile(out) as z:managed.verify_archive(z)
  files={n:sha(d) for n,d in sorted(data.items())}
  report={'file':out.name,'sha256':sha(out.read_bytes()),'bytes':out.stat().st_size,'files':len(data),'changed_paths':sorted(changed),'helper':'6.17.9 + empty-cache-1','installer':'1.0.10','schema':2,'settings_and_rows':'byte-identical to clean 1.1.1','native_binaries':0}
  (output/(edition+'-package.json')).write_text(json.dumps(report,indent=2));(output/(edition+'-manifest.json')).write_text(json.dumps(files,indent=2));print(json.dumps(report),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--baselines',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();build(a.baselines,a.output)
