"""Build the reviewed lower-memory updater and bounded deep-row reuse release."""
import argparse,hashlib,importlib.util,json,xml.etree.ElementTree as E,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PACKS='resources/icon-packs/'
PINS={'General':'3cdbbb7a6241a6cc2a3c092531b4453b4f587ae0e86b634e1b424d755bbd8300','Apple-TV-Mac':'b1433d28a053e2c56560412ddf2caf951887fc88321668c3f6e652b1b263ad9a'}
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
legacy=load('icons_release_legacy',ROOT/'tools/build_release.py')
def inventory(root):return {p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo') and p.name!='.DS_Store'}
def build(baselines,output):
 output.mkdir(parents=True,exist_ok=True);controller=inventory(ROOT/'controller-source/addon');manifest=json.loads((ROOT/'controller-source/manifest98.json').read_bytes())
 if {n:legacy.sha(raw) for n,raw in controller.items()}!=manifest['files'] or manifest['controller']!='0.1.98':raise ValueError('Controller98 source differs')
 installer=inventory(ROOT/'installer-source/plugin.program.blacklanturninstaller')
 legacy.zipwrite(output/'plugin.program.blacklanturninstaller-1.0.36.zip',{'plugin.program.blacklanturninstaller/'+n:raw for n,raw in installer.items()})
 components=load('icons_release_component',ROOT/'installer-source/plugin.program.blacklanturninstaller/resources/libs/component_update.py')
 for edition,pin in PINS.items():
  source=baselines/('BlackLanturn-'+edition+'-Kodi21-1.1.31.zip')
  if legacy.sha(source.read_bytes())!=pin:raise ValueError('Published31 baseline differs')
  with zipfile.ZipFile(source) as z:
   if z.testzip() is not None:raise ValueError('Baseline CRC failed')
   before={n:z.read(n) for n in z.namelist()}
  prefix='addons/plugin.program.blacklanturninstaller/'
  installer_prefix=prefix
  prefix='addons/script.blacklanturn.preview/'
  data={n:raw for n,raw in before.items() if not n.startswith((prefix,installer_prefix))};data.update({prefix+n:raw for n,raw in controller.items()});data.update({installer_prefix+n:raw for n,raw in installer.items()})
  marker=json.loads(data['userdata/blacklanturn-build.json']);marker.update(build_version='1.1.32',controller_version='0.1.98',release_id='blacklanturn-'+marker['edition']+'-1.1.32-r0',release_revision=0)
  data['userdata/blacklanturn-build.json']=json.dumps(marker,indent=2).encode()
  proof=set(json.loads(before['userdata/blacklanturn-releases.json'])['releases'][0]['files'])
  proof.update('addons/script.blacklanturn.preview/'+PACKS+n for n in ('blacklanturn-icons.json','packs/sculpted-silver/home.png','packs/smoked-glass/home.png'))
  proof.update('addons/plugin.program.blacklanturninstaller/resources/libs/'+n for n in ('stream_io.py','update_activity.py','downloader.py'))
  proof.update('addons/script.blacklanturn.preview/'+n for n in ('update_activity.py','provider_work.py','row_feedback.py','public_rows.py','live_review.py'))
  entry=dict(id=marker['release_id'],edition=marker['edition'],version='1.1.32',revision=0,**json.loads((ROOT/'hosted-files/release-notes-1.1.32.json').read_bytes()),files={n:legacy.sha(data[n]) for n in sorted(proof)})
  data['userdata/blacklanturn-releases.json']=json.dumps({'schema':1,'releases':[entry]},indent=2).encode()
  data['userdata/BlackLanturn-README.txt']+=b'\nRelease1.1.32: Lower-memory update staging, temporary background-work pause and bounded deep-row reuse. Existing settings, authorizations, icon choices and unrelated add-ons remain in place.\n'
  if any(n.startswith('addons/plugin.video.blacklanturn.fights/') for n in data):raise ValueError('Personal Fight Zone cannot be distributed')
  legacy.verify_dependency_closure(data)
  full=output/('BlackLanturn-'+edition+'-Kodi21-1.1.32.zip');legacy.zipwrite(full,data)
  component=output/('BlackLanturn-'+edition+'-Update-1.1.31-to-1.1.32.zip');components.build(source,full,component)
  report={'edition':marker['edition'],'build':'1.1.32','controller':'0.1.98','installer':'1.0.36','icons':'builtin98','full':{'file':full.name,'bytes':full.stat().st_size,'sha256':legacy.sha(full.read_bytes())},'components':{'file':component.name,'bytes':component.stat().st_size,'sha256':legacy.sha(component.read_bytes()),'base':'blacklanturn-'+marker['edition']+'-1.1.31-r0'}}
  (output/(edition+'-package.json')).write_text(json.dumps(report,indent=2)+'\n');print(edition,report['full']['bytes'],report['components']['bytes'],flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--baselines',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();build(a.baselines,a.output)
