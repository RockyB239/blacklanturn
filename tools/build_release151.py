"""Reproduce release51 from immutable public40 and frozen reviewed source inputs."""
import argparse,hashlib,importlib.util,json,xml.etree.ElementTree as E,zipfile
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
 validator=load('release151_catalog_validation',ROOT/'controller-source/addon/release_updates.py')
 validator.validate_catalog({'schema':1,'releases':[entry]});return entry
def build(baselines,output):
 output.mkdir(parents=True,exist_ok=True);legacy=load('release151_legacy',ROOT/'tools/build_release.py')
 controller=inventory(ROOT/'controller-source/addon');cp_manifest=json.loads((ROOT/'controller-source/manifest115.json').read_bytes())
 if {n:sha(raw) for n,raw in controller.items()}!=cp_manifest['files'] or E.fromstring(controller['addon.xml']).get('version')!='0.1.115':raise ValueError('Controller115 source differs')
 installer=inventory(ROOT/'installer-source/plugin.program.blacklanturninstaller');ip_manifest=json.loads((ROOT/'compatibility/addons151/installer-manifest47.json').read_bytes())
 if {n:sha(raw) for n,raw in installer.items()}!=ip_manifest['files'] or E.fromstring(installer['addon.xml']).get('version')!='1.0.47':raise ValueError('Installer47 source differs')
 current=ROOT/'compatibility/addons151';manifest=json.loads((current/'manifest.json').read_bytes());addons={}
 for aid,record in manifest['addons'].items():
  path=current/record['archive']
  if file_sha(path)!=record['archive_sha256']:raise ValueError('Reviewed source archive differs: '+aid)
  with zipfile.ZipFile(path) as z:
   if z.testzip() or any(not n.startswith(aid+'/') for n in z.namelist()):raise ValueError('Reviewed source wrapper/CRC differs')
   files={n[len(aid)+1:]:z.read(n) for n in z.namelist() if not n.endswith('/')}
  if {n:sha(raw) for n,raw in files.items()}!=record['files']:raise ValueError('Reviewed complete tree differs: '+aid)
  addons[aid]=files
 youtube={n:(current/'youtube-startup113'/n).read_bytes() for n in manifest['youtube_startup113']}
 if {n:sha(raw) for n,raw in youtube.items()}!=manifest['youtube_startup113']:raise ValueError('Accepted startup113 source differs')
 for aid,files in [("controller",controller),("installer",installer),*addons.items()]:
  for n,raw in files.items():
   if n.endswith('.py') and (aid!='installer' or n in ip_manifest['changed_runtime_files']):compile(raw,aid+'/'+n,'exec')
 legacy.zipwrite(output/'plugin.program.blacklanturninstaller-1.0.47.zip',{'plugin.program.blacklanturninstaller/'+n:raw for n,raw in installer.items()})
 components=load('release151_components',ROOT/'installer-source/plugin.program.blacklanturninstaller/resources/libs/component_update.py')
 managed=load('release151_managed',ROOT/'installer-source/plugin.program.blacklanturninstaller/resources/libs/managed_addons.py')
 releases=load('release151_releases',ROOT/'controller-source/addon/release_updates.py');report={}
 for edition,pin in PINS.items():
  baseline=baselines/('BlackLanturn-'+edition+'-Kodi21-1.1.40.zip')
  if file_sha(baseline)!=pin:raise ValueError('Public40 archive pin differs: '+edition)
  with zipfile.ZipFile(baseline) as z:
   if z.testzip():raise ValueError('Public40 CRC differs')
   before={n:z.read(n) for n in z.namelist() if not n.endswith('/')}
  data={n:raw for n,raw in before.items() if not n.startswith((CP,IP,*('addons/'+aid+'/' for aid in addons)))}
  data.update({CP+n:raw for n,raw in controller.items()});data.update({IP+n:raw for n,raw in installer.items()});data.update({YP+n:raw for n,raw in youtube.items()})
  for aid,files in addons.items():data.update({'addons/'+aid+'/'+n:raw for n,raw in files.items()})
  marker=json.loads(before['userdata/blacklanturn-build.json']);marker.update(build_version='1.1.51',controller_version='0.1.115',release_id='blacklanturn-'+marker['edition']+'-1.1.51-r0',release_revision=0,installer_min_version='1.0.47',helper_sync_policy='providers-1',umbrella_version='6.7.99')
  data['userdata/blacklanturn-build.json']=json.dumps(marker,indent=2).encode()
  entry=json.loads(before['userdata/blacklanturn-releases.json'])['releases'][0]
  notes=json.loads((ROOT/'hosted-files/release-notes-1.1.51.json').read_bytes())
  entry.update(id=marker['release_id'],version='1.1.51',revision=0,**notes)
  proof={n for n in entry['files'] if n in data}|{CP+n for n in controller}|{IP+n for n in installer if n.endswith('.json') or n.endswith('.py') and n in ip_manifest['changed_runtime_files']}|{IP+'addon.xml'}
  for aid,record in manifest['addons'].items():proof.update('addons/'+aid+'/'+n for n in set(record.get('patched_files',record.get('blacklanturn_modified_files',[])))|{'addon.xml'} if 'addons/'+aid+'/'+n in data)
  entry['files']={n:sha(data[n]) for n in sorted(proof)};validate_release_entry(entry)
  data['userdata/blacklanturn-releases.json']=json.dumps({'schema':1,'releases':[entry]},indent=2).encode()
  if any(before.get(n)!=data.get(n) for n in set(before)|set(data) if n.startswith('userdata/') and n not in META):raise ValueError('Personal/default userdata differs')
  if any(n.startswith(('addons/plugin.video.blacklanturn.fights/','addons/script.module.slyguy/','userdata/addon_data/plugin.video.blacklanturn.fights/')) for n in data):raise ValueError('Personal addon unexpectedly bundled')
  legacy.verify_dependency_closure(data)
  full=output/('BlackLanturn-'+edition+'-Kodi21-1.1.51.zip');legacy.zipwrite(full,data)
  with zipfile.ZipFile(full) as z:
   managed.verify_archive(z,umbrella=True,network=True,youtube=True)
   if managed._versions.prepare_policy(marker,z)!='1.0.47':raise ValueError('Provider group minimum differs')
  component=output/('BlackLanturn-'+edition+'-Update-1.1.40-to-1.1.51.zip');doc=components.build(baseline,full,component)
  changed={n for n in set(before)|set(data) if before.get(n)!=data.get(n)}
  record={'edition':marker['edition'],'build':'1.1.51','controller':'0.1.115','installer':'1.0.47','baseline_sha256':pin,'full':{'file':full.name,'bytes':full.stat().st_size,'sha256':file_sha(full)},'components':{'file':component.name,'bytes':component.stat().st_size,'sha256':file_sha(component),'base':'blacklanturn-'+marker['edition']+'-1.1.40-r0'},'changed_addons':sorted(set(doc['addons'])-set(doc['retained'])),'changed_files':sorted(changed),'proof_files':len(proof),'userdata_unchanged_except_release_metadata':True}
  report[marker['edition']]=record;(output/(edition+'-package.json')).write_text(json.dumps(record,indent=2)+'\n');print(edition,'full51 ready',full,flush=True)
 report['installer']={'file':'plugin.program.blacklanturninstaller-1.0.47.zip','sha256':file_sha(output/'plugin.program.blacklanturninstaller-1.0.47.zip')};(output/'candidate-packages.json').write_text(json.dumps(report,indent=2)+'\n')
 if sum(len(json.dumps(json.loads(zipfile.ZipFile(output/report[e]['full']['file']).read('userdata/blacklanturn-releases.json'))['releases'][0],indent=2).encode()) for e in ('general','apple'))>250000:raise ValueError('Combined release feed exceeds safe byte budget')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--baselines',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();build(a.baselines,a.output)
