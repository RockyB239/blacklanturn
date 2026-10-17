"""Reproducible 1.1.3 release from verified clean baselines, never live profiles."""
import argparse,ast,hashlib,importlib.util,json,re,sys,xml.etree.ElementTree as ET,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'installer-source/plugin.program.blacklanturninstaller'
PATCH=ROOT/'compatibility/helper-empty-cache'
BASE_HASHES={'General':'49581a62dd63333ff9be861a698d758550e59e2a6091eddb9c3f6f4431eaf3e4','Apple-TV-Mac':'ab396fbbee0bdf726bc1a21e4101bd8ccda3935add041f5b7f005c43a998ca73'}
def sha(data):return hashlib.sha256(data).hexdigest()
def zipwrite(path,data):
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for name,raw in sorted(data.items()):
   e=zipfile.ZipInfo(name,(2026,10,16,0,0,0));e.compress_type=zipfile.ZIP_DEFLATED;e.external_attr=0o100644<<16;z.writestr(e,raw)
 with zipfile.ZipFile(path) as z:assert z.testzip() is None

def build(baselines,output):
 output.mkdir(parents=True,exist_ok=True)
 installer={str(p.relative_to(SOURCE)):p.read_bytes() for p in SOURCE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and not p.name.endswith(('.pyc','.DS_Store'))}
 assert ET.fromstring(installer['addon.xml']).get('version')=='1.0.11'
 zipwrite(output/'plugin.program.blacklanturninstaller-1.0.11.zip',{'plugin.program.blacklanturninstaller/'+n:d for n,d in installer.items()})
 spec=importlib.util.spec_from_file_location('managed',SOURCE/'resources/libs/managed_addons.py');managed=importlib.util.module_from_spec(spec);spec.loader.exec_module(managed)
 for edition,expected in BASE_HASHES.items():
  source=baselines/f'BlackLanturn-{edition}-Kodi21-1.1.2.zip';assert sha(source.read_bytes())==expected,'Baseline changed'
  with zipfile.ZipFile(source) as z:
   assert z.testzip() is None;before={n:z.read(n) for n in z.namelist()}
  data=dict(before);prefix='addons/plugin.program.blacklanturninstaller/'
  data={n:d for n,d in data.items() if not n.startswith(prefix)}
  data.update({prefix+n:d for n,d in installer.items()})
  controller_root=ROOT/'controller-source/addon'
  controller={str(p.relative_to(controller_root)):p.read_bytes() for p in controller_root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
  expected_controller=json.loads((ROOT/'controller-source/manifest67.json').read_text())['files']
  assert {n:sha(raw) for n,raw in controller.items()}==expected_controller,'Validated controller changed'
  cp='addons/script.blacklanturn.preview/'
  data={n:raw for n,raw in data.items() if not n.startswith(cp)}
  data.update({cp+n:raw for n,raw in controller.items()})
  target='addons/plugin.video.themoviedb.helper/resources/tmdbhelper/lib/items/directories/tmdb/lists_search.py'
  assert sha(before[target])=='27f4d284eab62bfdfb414c6945f84dcbf86affa3e58277ddb5a6d370b4330996'
  data[target]=(PATCH/'candidate/lists_search.py').read_bytes()
  assert sha(data[target])=='6c6708f7f04ceaf0959281b606824eed8fdd0c9cbfc35bcc95f4901ef22d2b82'
  gui=ET.fromstring(data['userdata/guisettings.xml'])
  for key,value in {'filecache.memorysize':'64','filecache.readfactor':'400','filecache.buffermode':'4','filecache.chunksize':'131072'}.items():
   node=next((n for n in gui if n.get('id')==key),None)
   if node is None:node=ET.SubElement(gui,'setting',id=key)
   node.attrib.pop('default',None);node.text=value
  data['userdata/guisettings.xml']=ET.tostring(gui,encoding='utf-8',xml_declaration=True)
  hp='userdata/addon_data/plugin.video.themoviedb.helper/settings.xml'
  helper_settings=ET.fromstring(data[hp]);quality=next(n for n in helper_settings if n.get('id')=='artwork_quality');quality.attrib.pop('default',None);quality.text='1'
  data[hp]=ET.tostring(helper_settings,encoding='utf-8',xml_declaration=True)
  marker=json.loads(data['userdata/blacklanturn-build.json']);marker.update(schema=2,build_version='1.1.3',helper_patch='empty-cache-1',installer_min_version='1.0.11',controller_version='0.1.67',helper_search_patch='search-empty-1')
  data['userdata/blacklanturn-build.json']=json.dumps(marker,indent=2).encode()
  data['userdata/BlackLanturn-README.txt']=(before['userdata/BlackLanturn-README.txt'].decode()+'\n\nRelease 1.1.3: validated controller 0.1.67 navigation/search/playback improvements, exact managed Helper search-empty repair, and Installer 1.0.11 authorization-only preservation. Requires Installer 1.0.11. Experimental controllers 0.1.69 and 0.1.70 are excluded. Includes the tested 64MB fixed4x video cache and High artwork defaults. For a clean account-only install, enable Clean install: keep only selected accounts and the desired Keep Trakt/Debrid/Login choices. Native playback components remain device-specific.\n').encode()
  allowed={n for n in set(before)|set(data) if n.startswith((prefix,cp))}|{'userdata/blacklanturn-build.json','userdata/BlackLanturn-README.txt','userdata/guisettings.xml',hp,target}
  changed={n for n in set(before)|set(data) if before.get(n)!=data.get(n)};assert changed<=allowed
  for n,raw in data.items():
   assert n.startswith(('addons/','userdata/')) and '..' not in n.split('/')
   assert not any(x in n.split('/') for x in ('__pycache__','.git','packages','__MACOSX'))
   assert not n.endswith(('.pyc','.pyo','.so','.dylib','.dll','.exe','.DS_Store'))
   assert not raw.startswith((b'\x7fELF',b'\xcf\xfa\xed\xfe',b'\xfe\xed\xfa\xcf',b'MZ'))
   if n.endswith('/addon.xml'):ET.fromstring(raw)
   if n.endswith('.py') and n!=prefix+'resources/libs/zipfile.py':ast.parse(raw,n)
   if n.startswith('userdata/') and n not in ('userdata/blacklanturn-build.json','userdata/BlackLanturn-README.txt','userdata/guisettings.xml',hp):assert raw==before[n],'Userdata changed'
  addons={n.split('/')[1]:ET.fromstring(raw) for n,raw in data.items() if n.startswith('addons/') and n.endswith('/addon.xml')}
  system={'xbmc.python','xbmc.gui','xbmc.json','xbmc.addon','kodi.resource','script.module.pil','script.module.pycryptodome','inputstream.adaptive'}
  for aid,addon in addons.items():
   for dep in addon.findall('./requires/import'):
    if dep.get('optional')=='true':continue
    assert dep.get('addon') in addons or dep.get('addon') in system,(aid,dep.get('addon'))
  out=output/f'BlackLanturn-{edition}-Kodi21-1.1.3.zip';zipwrite(out,data)
  with zipfile.ZipFile(out) as z:managed.verify_archive(z)
  files={n:sha(d) for n,d in sorted(data.items())}
  report={'file':out.name,'sha256':sha(out.read_bytes()),'bytes':out.stat().st_size,'files':len(data),'changed_paths':sorted(changed),'helper':'6.17.9 + empty-cache-1 + search-empty-1','installer':'1.0.11','schema':2,'settings_and_rows':'clean 1.1.2 plus exact 64MB/4x buffer and High artwork defaults','native_binaries':0}
  (output/(edition+'-package.json')).write_text(json.dumps(report,indent=2));(output/(edition+'-manifest.json')).write_text(json.dumps(files,indent=2));print(json.dumps(report),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--baselines',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();build(a.baselines,a.output)
