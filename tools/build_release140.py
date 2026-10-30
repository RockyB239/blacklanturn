"""Build the reviewed current-addon release retaining platform variants and saved defaults."""
import argparse,hashlib,importlib.util,json,xml.etree.ElementTree as E,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PACKS='resources/icon-packs/'
PINS={'General': '8a30cd8f945662e11450f9ee92acb02dde2af72a4f4caf4b1a3e6027643ed145', 'Apple-TV-Mac': 'ffb151d26a09320781ff7076d338d35a2196a79d4a358cc38b9b7dc076158e15'}
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
legacy=load('icons_release_legacy',ROOT/'tools/build_release.py')
def validate_release_entry(entry):
 validator=load('personal_library_release_catalog',ROOT/'controller-source/addon/release_updates.py')
 validator.validate_catalog({'schema':1,'releases':[entry]})
 return entry
def inventory(root):return {p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo') and p.name!='.DS_Store'}
CURRENT=('plugin.video.umbrella','plugin.video.themoviedb.helper','service.upnext','script.module.tmdbhelper.sync.trakt','script.module.tmdbhelper.sync.mdblist')
def apply_current(data):
 """Replace complete reviewed trees, leaving userdata and unrelated code alone."""
 root=ROOT/'compatibility/addons134';manifest=json.loads((root/'manifest.json').read_bytes())['addons']
 staged={}
 for aid in CURRENT:
  source=ROOT/'compatibility/addons139' if aid in ('plugin.video.umbrella','plugin.video.themoviedb.helper') else root
  record=json.loads((source/'manifest.json').read_bytes())['addons'][aid];archive=source/record['archive']
  if legacy.sha(archive.read_bytes())!=record['archive_sha256']:raise ValueError('Changed current-source archive: '+aid)
  with zipfile.ZipFile(archive) as z:
   if z.testzip() is not None:raise ValueError('Current-source CRC failed')
   files={n[len(aid)+1:]:z.read(n) for n in z.namelist() if n.startswith(aid+'/') and not n.endswith('/')}
  if {n:legacy.sha(raw) for n,raw in files.items()}!=record['files']:raise ValueError('Current-source inventory differs: '+aid)
  staged.update({'addons/'+aid+'/'+n:raw for n,raw in files.items()})
 prefixes=tuple('addons/'+aid+'/' for aid in CURRENT)
 for n in list(data):
  if n.startswith(prefixes):del data[n]
 data.update(staged)
def build(baselines,output):
 output.mkdir(parents=True,exist_ok=True);controller=inventory(ROOT/'controller-source/addon');manifest=json.loads((ROOT/'controller-source/manifest104.json').read_bytes())
 if {n:legacy.sha(raw) for n,raw in controller.items()}!=manifest['files'] or manifest['controller']!='0.1.104':raise ValueError('Controller104 source differs')
 installer=inventory(ROOT/'installer-source/plugin.program.blacklanturninstaller')
 if E.fromstring(installer['addon.xml']).get('version')!='1.0.44':raise ValueError('Release40 requires its exact Installer44 source')
 legacy.zipwrite(output/'plugin.program.blacklanturninstaller-1.0.44.zip',{'plugin.program.blacklanturninstaller/'+n:raw for n,raw in installer.items()})
 components=load('icons_release_component',ROOT/'installer-source/plugin.program.blacklanturninstaller/resources/libs/component_update.py')
 for edition,pin in PINS.items():
  source=baselines/('BlackLanturn-'+edition+'-Kodi21-1.1.39.zip')
  if legacy.sha(source.read_bytes())!=pin:raise ValueError('Published39 baseline differs')
  with zipfile.ZipFile(source) as z:
   if z.testzip() is not None:raise ValueError('Baseline CRC failed')
   before={n:z.read(n) for n in z.namelist()}
  prefix='addons/plugin.program.blacklanturninstaller/'
  installer_prefix=prefix
  prefix='addons/script.blacklanturn.preview/'
  data={n:raw for n,raw in before.items() if not n.startswith((prefix,installer_prefix))};data.update({prefix+n:raw for n,raw in controller.items()});data.update({installer_prefix+n:raw for n,raw in installer.items()})
  apply_current(data)
  marker=json.loads(data['userdata/blacklanturn-build.json']);marker['umbrella_version']='6.7.98';marker['bundle_registration_policy']='new-bundles-1';marker['installer_min_version']='1.0.40';marker.update(build_version='1.1.40',controller_version='0.1.104',release_id='blacklanturn-'+marker['edition']+'-1.1.40-r0',release_revision=0)
  data['userdata/blacklanturn-build.json']=json.dumps(marker,indent=2).encode()
  proof=set(json.loads(before['userdata/blacklanturn-releases.json'])['releases'][0]['files'])
  proof.update('addons/script.blacklanturn.preview/'+PACKS+n for n in ('blacklanturn-icons.json','packs/sculpted-silver/home.png','packs/smoked-glass/home.png'))
  proof.update('addons/plugin.program.blacklanturninstaller/resources/libs/'+n for n in ('stream_io.py','update_activity.py','downloader.py'))
  proof.update('addons/script.blacklanturn.preview/'+n for n in ('update_activity.py','provider_work.py','row_feedback.py','public_rows.py','live_review.py'))
  proof.update('addons/script.blacklanturn.preview/'+n for n in ('live_core.py','backend_core.py','title_preferences.py','title_feedback_ui.py','resources/skins/Default/1080i/FeedbackUndo.xml','resources/skins/Default/1080i/LiveReview.xml'))
  proof.add('addons/plugin.program.blacklanturninstaller/resources/libs/build_preferences.py')
  proof.add('addons/script.blacklanturn.preview/release_updates.py')
  source_manifest=json.loads((ROOT/'compatibility/addons134/manifest.json').read_bytes())['addons']
  source_manifest.update(json.loads((ROOT/'compatibility/addons139/manifest.json').read_bytes())['addons'])
  for aid in CURRENT:
   names=set(source_manifest[aid].get('patched_files',()))|{'addon.xml'}
   if aid=='service.upnext':names=set(source_manifest[aid]['files'])
   proof.update('addons/'+aid+'/'+n for n in names)
  proof.update('addons/plugin.program.blacklanturninstaller/resources/'+n for n in ('managed-helper.json','managed-umbrella.json','managed-versions.json'))
  proof.add('addons/plugin.program.blacklanturninstaller/resources/libs/addon_registration.py')
  proof.update('addons/script.blacklanturn.preview/'+n for n in ('playback_core.py','row_layout.py','row_layout_ui.py','series_status.py','youtube_browser.py','youtube_rows.py','title_feedback_ui.py'))
  proof.update('addons/script.blacklanturn.preview/'+n for n in ('personal_library.py','library_ui.py','local_watch.py','movie_series.py','series_metadata.py','series_end_core.py','series_end.py','series_end_ui.py','resources/skins/Default/1080i/SeriesEnd.xml'))
  entry=validate_release_entry(dict(id=marker['release_id'],edition=marker['edition'],version='1.1.40',revision=0,**json.loads((ROOT/'hosted-files/release-notes-1.1.40.json').read_bytes()),files={n:legacy.sha(data[n]) for n in sorted(proof)}))
  data['userdata/blacklanturn-releases.json']=json.dumps({'schema':1,'releases':[entry]},indent=2).encode()
  data['userdata/BlackLanturn-README.txt']+=b'\nRelease1.1.40: Archived release notes are byte-bounded so future update notifications remain reliable. All next-series and browsing refinements from1.1.39 are retained. All prior reliability and compatibility fixes remain included. Existing settings, authorizations, icon choices and unrelated add-ons remain in place.\n'
  if any(n.startswith('addons/plugin.video.blacklanturn.fights/') for n in data):raise ValueError('Personal Fight Zone cannot be distributed')
  legacy.verify_dependency_closure(data)
  full=output/('BlackLanturn-'+edition+'-Kodi21-1.1.40.zip');legacy.zipwrite(full,data)
  component=output/('BlackLanturn-'+edition+'-Update-1.1.39-to-1.1.40.zip');components.build(source,full,component)
  report={'edition':marker['edition'],'build':'1.1.40','controller':'0.1.104','installer':'1.0.44','icons':'builtin99','full':{'file':full.name,'bytes':full.stat().st_size,'sha256':legacy.sha(full.read_bytes())},'components':{'file':component.name,'bytes':component.stat().st_size,'sha256':legacy.sha(component.read_bytes()),'base':'blacklanturn-'+marker['edition']+'-1.1.39-r0'}}
  (output/(edition+'-package.json')).write_text(json.dumps(report,indent=2)+'\n');print(edition,report['full']['bytes'],report['components']['bytes'],flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--baselines',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();build(a.baselines,a.output)
