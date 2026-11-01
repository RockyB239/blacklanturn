"""Reproduce release54 from immutable public40 and frozen reviewed source inputs."""
import argparse,hashlib,importlib.util,json,shutil,sys,xml.etree.ElementTree as E,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PINS={'General':'378205105fc7e4cd2f630ef107e1e94ad5b0085b20c7d5e35062772cf02aebeb','Apple-TV-Mac':'3cb1d5fe950d14f5afb0f4532f22559befccd4c31103934228954ea31c2600cd'}
CP='addons/script.blacklanturn.preview/';IP='addons/plugin.program.blacklanturninstaller/';YP='addons/plugin.video.youtube/'
META={'userdata/blacklanturn-build.json','userdata/blacklanturn-releases.json'}
def sha(raw):return hashlib.sha256(raw).hexdigest()
def file_sha(path):
 h=hashlib.sha256()
 with path.open('rb') as stream:
  for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def inventory(root):return {p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo') and p.name!='.DS_Store'}
def validate_release_entry(entry):
 validator=load('release154_catalog_validation',ROOT/'controller-source/addon/release_updates.py')
 validator.validate_catalog({'schema':1,'releases':[entry]});return entry
def build(baselines,output):
 output.mkdir(parents=True,exist_ok=True);legacy=load('release154_legacy',ROOT/'tools/build_release.py')
 controller=inventory(ROOT/'controller-source/addon');cp_manifest=json.loads((ROOT/'controller-source/manifest118.json').read_bytes())
 if {n:sha(raw) for n,raw in controller.items()}!=cp_manifest['files'] or E.fromstring(controller['addon.xml']).get('version')!='0.1.118':raise ValueError('Controller118 source differs')
 sys.path.insert(0,str(ROOT/'installer-source/plugin.program.blacklanturninstaller'))
 installer=inventory(ROOT/'installer-source/plugin.program.blacklanturninstaller');ip_manifest=json.loads((ROOT/'compatibility/menus153/installer-manifest49.json').read_bytes())
 if {n:sha(raw) for n,raw in installer.items()}!=ip_manifest['files'] or E.fromstring(installer['addon.xml']).get('version')!='1.0.49':raise ValueError('Installer49 source differs')
 current=ROOT/'compatibility/addons151';manifest=json.loads((current/'manifest.json').read_bytes());addons={}
 for aid,record in manifest['addons'].items():
  path=current/record['archive']
  if file_sha(path)!=record['archive_sha256']:raise ValueError('Reviewed source archive differs: '+aid)
  with zipfile.ZipFile(path) as z:
   if z.testzip() or any(not n.startswith(aid+'/') for n in z.namelist()):raise ValueError('Reviewed source wrapper/CRC differs')
   files={n[len(aid)+1:]:z.read(n) for n in z.namelist() if not n.endswith('/')}
  if {n:sha(raw) for n,raw in files.items()}!=record['files']:raise ValueError('Reviewed complete tree differs: '+aid)
  addons[aid]=files
 coco_manifest=json.loads((ROOT/'compatibility/addons152/manifest.json').read_bytes())
 coco_path=ROOT/'compatibility/addons152'/coco_manifest['archive']
 if file_sha(coco_path)!=coco_manifest['archive_sha256']:raise ValueError('Coco archive differs')
 with zipfile.ZipFile(coco_path) as z:
  if z.testzip() or any(not n.startswith('script.module.cocoscrapers/') for n in z.namelist()):raise ValueError('Coco wrapper/CRC differs')
  coco={n.split('/',1)[1]:z.read(n) for n in z.namelist() if not n.endswith('/')}
 if {n:sha(raw) for n,raw in coco.items()}!=coco_manifest['files']:raise ValueError('Coco complete source differs')
 addons['script.module.cocoscrapers']=coco
 youtube={n:(current/'youtube-startup113'/n).read_bytes() for n in manifest['youtube_startup113']}
 if {n:sha(raw) for n,raw in youtube.items()}!=manifest['youtube_startup113']:raise ValueError('Accepted startup113 source differs')
 for aid,files in [("controller",controller),("installer",installer),*addons.items()]:
  for n,raw in files.items():
   if n.endswith('.py') and (aid!='installer' or n in ip_manifest['changed_runtime_files']):compile(raw,aid+'/'+n,'exec')
 published_installer=ROOT/'plugin.program.blacklanturninstaller/plugin.program.blacklanturninstaller-1.0.49.zip'
 if file_sha(published_installer)!='7a40166f2b59d519ddb77d3e36296dc42b7b3efd86401319e8334053407f28fb':raise ValueError('Published Installer49 SHA differs')
 with zipfile.ZipFile(published_installer) as z:
  if z.testzip() or {n:z.read(n) for n in z.namelist() if not n.endswith('/')}!={'plugin.program.blacklanturninstaller/'+n:raw for n,raw in installer.items()}:raise ValueError('Published Installer49 tree differs from unchanged source')
 shutil.copyfile(published_installer,output/published_installer.name)
 components=load('release154_components',ROOT/'installer-source/plugin.program.blacklanturninstaller/resources/libs/component_update.py')
 managed=load('release154_managed',ROOT/'installer-source/plugin.program.blacklanturninstaller/resources/libs/managed_addons.py')
 releases=load('release154_releases',ROOT/'controller-source/addon/release_updates.py');report={}
 for edition,baseline_pin in PINS.items():
  baseline=baselines/('BlackLanturn-'+edition+'-Kodi21-1.1.40.zip')
  if file_sha(baseline)!=baseline_pin:raise ValueError('Public40 archive pin differs: '+edition)
  with zipfile.ZipFile(baseline) as z:
   if z.testzip():raise ValueError('Public40 CRC differs')
   before={n:z.read(n) for n in z.namelist() if not n.endswith('/')}
  data={n:raw for n,raw in before.items() if not n.startswith((CP,IP,*('addons/'+aid+'/' for aid in addons)))}
  data.update({CP+n:raw for n,raw in controller.items()});data.update({IP+n:raw for n,raw in installer.items()});data.update({YP+n:raw for n,raw in youtube.items()})
  for aid,files in addons.items():data.update({'addons/'+aid+'/'+n:raw for n,raw in files.items()})
  skin=json.loads((ROOT/'compatibility/menus153/skin-manifest.json').read_bytes())
  for n,skin_pin in skin['files'].items():
   raw=(ROOT/'compatibility/menus153/skin'/n).read_bytes()
   if sha(raw)!=skin_pin:raise ValueError('Skin frozen source differs: '+n)
   data['addons/skin.blacklanturn.preview/'+n]=raw
  for n in skin['forbidden_skin_files']:
   if 'addons/skin.blacklanturn.preview/'+n in data:raise ValueError('Personal popup unexpectedly bundled: '+n)
  skin154=json.loads((ROOT/'compatibility/menus154/skin-manifest.json').read_bytes())
  if set(skin154['forbidden_skin_files'])!=set(skin['forbidden_skin_files']):raise ValueError('Personal popup exclusion policy differs')
  for n,skin_pin in skin154['files'].items():
   raw=(ROOT/'compatibility/menus154/skin'/n).read_bytes()
   if sha(raw)!=skin_pin:raise ValueError('Frozen154skin differs: '+n)
   data['addons/skin.blacklanturn.preview/'+n]=raw
  for n in skin154['forbidden_skin_files']:
   if 'addons/skin.blacklanturn.preview/'+n in data:raise ValueError('Personal popup unexpectedly bundled: '+n)
  marker=json.loads(before['userdata/blacklanturn-build.json']);marker.update(build_version='1.1.54',controller_version='0.1.118',release_id='blacklanturn-'+marker['edition']+'-1.1.54-r0',release_revision=0,installer_min_version='1.0.48',helper_sync_policy='providers-1',cocoscrapers_policy='parallel-airdate-1',umbrella_version='6.7.99')
  data['userdata/blacklanturn-build.json']=json.dumps(marker,indent=2).encode()
  entry=json.loads(before['userdata/blacklanturn-releases.json'])['releases'][0]
  notes=json.loads((ROOT/'hosted-files/release-notes-1.1.54.json').read_bytes())
  entry.update(id=marker['release_id'],version='1.1.54',revision=0,**notes)
  proof={n for n in entry['files'] if n in data}|{CP+n for n in controller}|{IP+n for n in installer if n.endswith('.json') or n.endswith('.py') and n in ip_manifest['changed_runtime_files']}|{IP+'addon.xml'}
  for aid,record in manifest['addons'].items():proof.update('addons/'+aid+'/'+n for n in set(record.get('patched_files',record.get('blacklanturn_modified_files',[])))|{'addon.xml'} if 'addons/'+aid+'/'+n in data)
  proof.update('addons/'+item['path'].split('/',1)[1] for item in coco_manifest['accepted_files'] if item['path'].startswith('addons/script.module.cocoscrapers/'))
  proof.add('addons/script.module.cocoscrapers/addon.xml')
  proof.update('addons/skin.blacklanturn.preview/'+n for n in skin['files'])
  proof.update('addons/skin.blacklanturn.preview/'+n for n in skin154['files'])
  entry['files']={n:sha(data[n]) for n in sorted(proof)};validate_release_entry(entry)
  data['userdata/blacklanturn-releases.json']=json.dumps({'schema':1,'releases':[entry]},indent=2).encode()
  if any(before.get(n)!=data.get(n) for n in set(before)|set(data) if n.startswith('userdata/') and n not in META):raise ValueError('Personal/default userdata differs')
  if any(n.startswith(('addons/plugin.video.blacklanturn.fights/','addons/script.module.slyguy/','addons/plugin.video.paramount.plus/','addons/slyguy.paramount.plus/','addons/script.module.slyguy.dependencies/','addons/repository.slyguy/','addons/inputstream.adaptive/','userdata/addon_data/plugin.video.blacklanturn.fights/')) for n in data):raise ValueError('Personal addon unexpectedly bundled')
  legacy.verify_dependency_closure(data)
  full=output/('BlackLanturn-'+edition+'-Kodi21-1.1.54.zip');legacy.zipwrite(full,data)
  with zipfile.ZipFile(full) as z:
   managed.verify_archive(z,umbrella=True,network=True,youtube=True)
   from resources.libs import cocoscrapers_policy
   cocoscrapers_policy.verify_archive(z)
   if managed._versions.prepare_policy(marker,z)!='1.0.48':raise ValueError('Provider group minimum differs')
  component=output/('BlackLanturn-'+edition+'-Update-1.1.40-to-1.1.54.zip');doc=components.build(baseline,full,component)
  changed={n for n in set(before)|set(data) if before.get(n)!=data.get(n)}
  record={'edition':marker['edition'],'build':'1.1.54','controller':'0.1.118','installer':'1.0.49','baseline_sha256':baseline_pin,'full':{'file':full.name,'bytes':full.stat().st_size,'sha256':file_sha(full)},'components':{'file':component.name,'bytes':component.stat().st_size,'sha256':file_sha(component),'base':'blacklanturn-'+marker['edition']+'-1.1.40-r0'},'changed_addons':sorted(set(doc['addons'])-set(doc['retained'])),'changed_files':sorted(changed),'proof_files':len(proof),'userdata_unchanged_except_release_metadata':True}
  report[marker['edition']]=record;(output/(edition+'-package.json')).write_text(json.dumps(record,indent=2)+'\n');print(edition,'full54 ready',full,flush=True)
 report['installer']={'file':'plugin.program.blacklanturninstaller-1.0.49.zip','sha256':file_sha(output/'plugin.program.blacklanturninstaller-1.0.49.zip')};(output/'candidate-packages.json').write_text(json.dumps(report,indent=2)+'\n')
 if sum(len(json.dumps(json.loads(zipfile.ZipFile(output/report[e]['full']['file']).read('userdata/blacklanturn-releases.json'))['releases'][0],indent=2).encode()) for e in ('general','apple'))>250000:raise ValueError('Combined release feed exceeds safe byte budget')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--baselines',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();build(a.baselines,a.output)
