"""Reproducible optimization release from the exact published129 editions."""
import argparse,hashlib,importlib.util,json,sys,xml.etree.ElementTree as E,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PINS={'General': 'be148f6e483a6209a07325d62a1fa1399d6b9b816b01ba3b5d749def31441841', 'Apple-TV-Mac': 'eeb03c86c151dca077121bdc7951c70e90187434010f731d616739bca3e6a0e3'}
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
legacy=load('blacklanturn_prior_builder',ROOT/'tools/build_release.py')
def inventory(root):return {p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo') and p.name!='.DS_Store'}
def build(baselines,output):
 output.mkdir(parents=True,exist_ok=True)
 controller=inventory(ROOT/'controller-source/addon');manifest=json.loads((ROOT/'controller-source/manifest96.json').read_bytes())
 if manifest['controller']!='0.1.96' or {n:legacy.sha(raw) for n,raw in controller.items()}!=manifest['files']:raise ValueError('Controller96 source differs from reviewed manifest')
 installer=inventory(ROOT/'installer-source/plugin.program.blacklanturninstaller')
 if E.fromstring(installer['addon.xml']).get('version')!='1.0.35':raise ValueError('Installer35 metadata differs')
 legacy.zipwrite(output/'plugin.program.blacklanturninstaller-1.0.35.zip',{'plugin.program.blacklanturninstaller/'+n:raw for n,raw in installer.items()})
 proof=set(legacy.RELEASE_PROOFS)
 proof.update('addons/script.blacklanturn.preview/'+n for n in ('extensions.py','icon_packs.py','watch_metadata.py','provider_work.py','public_rows.py','navigation_core.py','backend_core.py','backend_ui.py','icon_picker.py','browse_controls.py','row_feedback.py'))
 proof.update('addons/plugin.program.blacklanturninstaller/resources/libs/'+n for n in ('component_update.py','portable_lock.py','check.py'))
 components=load('blacklanturn_component_builder',ROOT/'installer-source/plugin.program.blacklanturninstaller/resources/libs/component_update.py')
 for edition,pin in PINS.items():
  source=baselines/('BlackLanturn-'+edition+'-Kodi21-1.1.29.zip')
  if legacy.sha(source.read_bytes())!=pin:raise ValueError('Published129 baseline changed')
  with zipfile.ZipFile(source) as archive:
   if archive.testzip() is not None:raise ValueError('Baseline CRC failed')
   before={n:archive.read(n) for n in archive.namelist()}
  data=dict(before)
  for aid,files in (('script.blacklanturn.preview',controller),('plugin.program.blacklanturninstaller',installer)):
   prefix='addons/'+aid+'/';data={n:raw for n,raw in data.items() if not n.startswith(prefix)};data.update({prefix+n:raw for n,raw in files.items()})
  marker=json.loads(data['userdata/blacklanturn-build.json']);marker.update(build_version='1.1.30',controller_version='0.1.96',release_id='blacklanturn-'+marker['edition']+'-1.1.30-r0',release_revision=0)
  data['userdata/blacklanturn-build.json']=json.dumps(marker,indent=2).encode()
  notes=json.loads((ROOT/'hosted-files/release-notes-1.1.30.json').read_bytes())
  entry=dict(id=marker['release_id'],edition=marker['edition'],version='1.1.30',revision=0,**notes,files={n:legacy.sha(data[n]) for n in sorted(proof)})
  data['userdata/blacklanturn-releases.json']=json.dumps({'schema':1,'releases':[entry]},indent=2).encode()
  data['userdata/BlackLanturn-README.txt']+=b'\nRelease1.1.30: update-safe extension descriptors and external icon resources, request-owned YouTube settings reuse, latest-only row scheduling, batched disposable snapshots, corrected episode genre scope, optional verified component downloads and portable update locking. Saved preferences and authorizations remain in place. Personal providers are not distributed.\n'
  allowed=('addons/script.blacklanturn.preview/','addons/plugin.program.blacklanturninstaller/')
  metadata={'userdata/blacklanturn-build.json','userdata/blacklanturn-releases.json','userdata/BlackLanturn-README.txt'}
  changed={n for n in set(before)|set(data) if before.get(n)!=data.get(n)}
  if any(n not in metadata and not n.startswith(allowed) for n in changed):raise ValueError('Unexpected payload change')
  if any(n.startswith(('addons/plugin.video.blacklanturn.fights/','addons/resource.images.blacklanturn.personal/')) for n in data):raise ValueError('Personal resources must remain private')
  legacy.verify_dependency_closure(data)
  destination=output/('BlackLanturn-'+edition+'-Kodi21-1.1.30.zip');legacy.zipwrite(destination,data)
  component=output/('BlackLanturn-'+edition+'-Update-1.1.29-to-1.1.30.zip');components.build(source,destination,component)
  report={'edition':marker['edition'],'build':'1.1.30','controller':'0.1.96','installer':'1.0.35','full':{'file':destination.name,'bytes':destination.stat().st_size,'sha256':legacy.sha(destination.read_bytes())},'components':{'file':component.name,'bytes':component.stat().st_size,'sha256':legacy.sha(component.read_bytes()),'base':'blacklanturn-'+marker['edition']+'-1.1.29-r0'},'changed_paths':sorted(changed),'source_manifest':'manifest96.json'}
  (output/(edition+'-package.json')).write_text(json.dumps(report,indent=2)+'\n');print(edition,report['full']['bytes'],report['components']['bytes'],flush=True)
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--baselines',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();build(args.baselines,args.output)
