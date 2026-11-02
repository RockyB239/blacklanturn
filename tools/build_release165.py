"""Release58: promote the frozen, tested164 overlays onto immutable public57."""
import argparse,hashlib,importlib.util,json,sys,zipfile,xml.etree.ElementTree as E
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def sha(raw):return hashlib.sha256(raw).hexdigest()
def file_sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def inventory(root):return {p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo') and p.name!='.DS_Store'}
def build(baselines,out):
 candidate=load('candidate165',R/'tools/build_reliability_candidate164.py');legacy=load('legacy165',R/'tools/build_release.py');components=load('components165',R/'installer-source/plugin.program.blacklanturninstaller/resources/libs/component_update.py')
 patches=candidate.overlays();controller=inventory(R/'controller-source/addon');installer=inventory(R/'installer-source/plugin.program.blacklanturninstaller');CP='addons/script.blacklanturn.preview/';IP='addons/plugin.program.blacklanturninstaller/'
 for name,files,manifest,version in [('controller',controller,R/'controller-source/manifest122.json','0.1.122'),('installer',installer,R/'compatibility/reliability165/installer-manifest52.json','1.0.52')]:
  if {n:sha(v) for n,v in files.items()}!=json.loads(manifest.read_text())['files'] or E.fromstring(files['addon.xml']).get('version')!=version:raise ValueError(name+' frozen source differs')
 sys.path.insert(0,str(R/'installer-source/plugin.program.blacklanturninstaller'));managed=load('managed165',R/'installer-source/plugin.program.blacklanturninstaller/resources/libs/managed_addons.py');validator=load('releases165',R/'controller-source/addon/release_updates.py')
 out.mkdir(parents=True,exist_ok=True);notes=json.loads((R/'hosted-files/release-notes-1.1.58.json').read_text());report={}
 legacy.zipwrite(out/'plugin.program.blacklanturninstaller-1.0.52.zip',{'plugin.program.blacklanturninstaller/'+n:v for n,v in installer.items()})
 for edition,pin in candidate.PINS.items():
  base=baselines/('BlackLanturn-'+edition+'-Kodi21-1.1.57.zip')
  if file_sha(base)!=pin:raise ValueError('Public57 pin differs')
  with zipfile.ZipFile(base) as z:
   if z.testzip():raise ValueError('Public57 CRC differs')
   before={n:z.read(n) for n in z.namelist() if not n.endswith('/')}
  data=dict(before);data.update(patches);data.update({CP+n:v for n,v in controller.items()});data.update({IP+n:v for n,v in installer.items()})
  marker=json.loads(before['userdata/blacklanturn-build.json']);label=marker['edition'];marker.update(build_version='1.1.58',controller_version='0.1.122',installer_min_version='1.0.52',reliability_patch='navigation-focus-1',release_id='blacklanturn-'+label+'-1.1.58-r0',release_revision=0)
  data['userdata/blacklanturn-build.json']=json.dumps(marker,indent=2).encode();feed=json.loads(before['userdata/blacklanturn-releases.json']);entry=feed['releases'][0];entry.update(id=marker['release_id'],version='1.1.58',revision=0,**notes)
  proof=set(entry['files'])|set(patches)|{IP+'resources/managed-umbrella.json'};entry['files']={n:sha(data[n]) for n in sorted(proof)};validator.validate_catalog(feed);data['userdata/blacklanturn-releases.json']=json.dumps(feed,indent=2).encode()
  allowed=set(patches)|{IP+'resources/managed-umbrella.json',IP+'resources/libs/managed_versions.py',IP+'resources/libs/helper_providers.py',IP+'resources/libs/cocoscrapers_policy.py',CP+'addon.xml',IP+'addon.xml','userdata/blacklanturn-build.json','userdata/blacklanturn-releases.json'};changed={n for n in before.keys()|data.keys() if before.get(n)!=data.get(n)}
  if changed!=allowed:raise ValueError('Release scope differs: '+repr(changed^allowed))
  if len(proof)!=783:raise ValueError('Expected783 proofs')
  if any(n.startswith(('addons/plugin.video.blacklanturn.fights/','addons/script.module.slyguy/','addons/slyguy.paramount.plus/','userdata/Database/')) for n in data):raise ValueError('Private source bundled')
  legacy.verify_dependency_closure(data);full=out/('BlackLanturn-'+edition+'-Kodi21-1.1.58.zip');legacy.zipwrite(full,data)
  with zipfile.ZipFile(full) as z:managed.verify_archive(z,umbrella=True,network=True,youtube=True)
  component=out/('BlackLanturn-'+edition+'-Update-1.1.57-to-1.1.58.zip');doc=components.build(base,full,component)
  report[label]={'edition':label,'build':'1.1.58','controller':'0.1.122','installer':'1.0.52','baseline_sha256':pin,'full':{'file':full.name,'sha256':file_sha(full),'bytes':full.stat().st_size},'components':{'file':component.name,'sha256':file_sha(component),'bytes':component.stat().st_size,'base':'blacklanturn-'+label+'-1.1.57-r0'},'proof_files':len(proof),'changed_files':sorted(changed),'userdata_unchanged_except_release_metadata':True};print(edition+'58 ready',flush=True)
 report['installer']={'file':'plugin.program.blacklanturninstaller-1.0.52.zip','sha256':file_sha(out/'plugin.program.blacklanturninstaller-1.0.52.zip')};(out/'candidate-packages.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--baselines',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();build(a.baselines,a.output)
