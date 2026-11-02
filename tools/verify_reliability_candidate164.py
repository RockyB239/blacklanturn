"""Actual candidate artifacts, real installer, disposable synthetic profiles only."""
from pathlib import Path
import argparse,atexit,hashlib,importlib.util,json,shutil,sys,tempfile,zipfile,xml.etree.ElementTree as E
R=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--artifacts',type=Path,required=True);p.add_argument('--baselines',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
A=args.artifacts.resolve();scratch=tempfile.TemporaryDirectory();atexit.register(scratch.cleanup);I=Path(scratch.name)/'plugin.program.blacklanturninstaller'
with zipfile.ZipFile(A/'BlackLanturn-Installer-Reliability164-candidate.zip') as z:
 assert z.testzip() is None;assert all(n.startswith('plugin.program.blacklanturninstaller/') for n in z.namelist());z.extractall(I.parent)
LIB=I/'resources/libs';sys.path[:0]=[str(I),str(R/'tests')]
import test_compatibility as compat_fixture
import test_preferences_install_flow as prefs_fixture
compat_fixture.ROOT=LIB;prefs_fixture.LIB=LIB
# Test fixtures import the historical source tree; resolve runtime imports from
# the actual candidate installer, never from those fixture import side effects.
for name in list(sys.modules):
 if name=='resources' or name.startswith('resources.'):sys.modules.pop(name)
sys.path.insert(0,str(I))
from unittest.mock import patch

def load(name):
 s=importlib.util.spec_from_file_location('candidate_verification164_'+name,LIB/(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def kodi(label):
 k=compat_fixture.Kodi();k.getCondVisibility=lambda c:c in (('System.Platform.Android',) if label=='general' else ('System.Platform.OSX','System.Platform.Darwin'));return k

def digest(raw):return hashlib.sha256(raw).hexdigest()
report_path=A/'candidate-packages.json'
report=json.loads(report_path.read_text());checks=[]
artifact_pins={}
for row in report['editions'].values():
 for kind in ('full','components'):
  entry=row[kind];actual=digest((A/entry['file']).read_bytes());assert actual==entry['sha256'],entry['file'];artifact_pins[entry['file']]=actual
installer_name='BlackLanturn-Installer-Reliability164-candidate.zip'
artifact_pins[installer_name]=digest((A/installer_name).read_bytes())
for label,edition in [('general','General'),('apple','Apple-TV-Mac')]:
 full=A/report['editions'][label]['full']['file'];component=A/report['editions'][label]['components']['file'];baseline=args.baselines/('BlackLanturn-'+edition+'-Kodi21-1.1.57.zip')
 with zipfile.ZipFile(full) as z:
  assert z.testzip() is None;assert len(z.namelist())==len(set(z.namelist()));entry=json.loads(z.read('userdata/blacklanturn-releases.json'))['releases'][0]
  for n,pin in entry['files'].items():assert digest(z.read(n))==pin,n
  load('managed_addons').verify_archive(z,umbrella=True,network=True,youtube=True)
  assert not any(n.startswith(('addons/plugin.video.blacklanturn.fights/','addons/script.module.slyguy/','userdata/Database/')) for n in z.namelist())
 for kind,path in [('full',full),('components',component)]:
  with tempfile.TemporaryDirectory() as directory:
   h=Path(directory)
   with zipfile.ZipFile(baseline) as old:old.extractall(h)
   private={'userdata/favourites.xml':b'synthetic-favourites','userdata/Database/fixture.db':b'synthetic-history','userdata/addon_data/plugin.video.youtube/access_manager.json':b'synthetic-private-account','addons/plugin.video.fixture/addon.xml':b'<addon id="plugin.video.fixture" version="1.0"/>','addons/plugin.video.fixture/extra.py':b'private-extra-addon'}
   for n,raw in private.items():p=h/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
   def saved():return {p.relative_to(h/'userdata').as_posix():p.read_bytes() for p in (h/'userdata').rglob('*') if p.is_file() and p.name not in ('blacklanturn-build.json','blacklanturn-releases.json','blacklanturn-install-complete.json')}
   before=saved();updater=load('inplace_update');plan=updater.prepare(path,h,kodi(label));updater.apply(plan);assert saved()==before
   load('managed_addons').verify_installed(h,network=True,youtube=True)
   for n,raw in private.items():assert (h/n).read_bytes()==raw,n
   for n,pin in entry['files'].items():assert digest((h/n).read_bytes())==pin,n
   assert not (h/'addons/.blacklanturn-update').exists();checks.append(label+' in-place '+kind)
 for clean in (False,True):
  f=prefs_fixture.PreferenceInstallFlow();f.setUp()
  try:
   def packaged(change=None):
    assert change is None;target=f.root/'build.zip';shutil.copy2(full,target);shutil.copytree(I,f.root/'profile/addons/plugin.program.blacklanturninstaller',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.pyo'));return target
   f.packaged=packaged
   with patch.object(prefs_fixture,'Kodi',lambda:kodi(label)):home=f.run_install(auth_only=clean,youtube_choices={'kodion.video.quality':'2'})
   load('managed_addons').verify_installed(home,network=True,youtube=True)
   with zipfile.ZipFile(full) as z:
    for n,pin in entry['files'].items():assert digest((home/n).read_bytes())==pin,n
   y=home/'userdata/addon_data/plugin.video.youtube';values={n.get('id'):n.text for n in E.parse(y/'settings.xml').getroot()}
   assert values['youtube.api.key']=='private-youtube-key';assert json.loads((y/'access_manager.json').read_text())['access_manager']['users']['fixture']['refresh_token']=='private-refresh'
   vals={n.get('id'):n.text for n in E.parse(home/'userdata/addon_data/plugin.video.themoviedb.helper/settings.xml').getroot()};assert vals['trakt_token']=='private-token'
   if not clean:assert values['kodion.video.quality']=='2'
   checks.append(label+(' clean install' if clean else ' Standard install'))
  finally:f.tearDown()
result={'passed':True,'checks':checks,'artifacts_sha256':artifact_pins,'package_report_sha256':digest(report_path.read_bytes()),'source_sha256':report['source_sha256'],'playback_source_sha256':report['playback_source_sha256'],'scope':'Actual complete candidate artifacts through real installer/preflight/updater; synthetic disposable profiles and native Kodi interface fixtures, not physical-device installs','public_changed':False};args.output.write_text(json.dumps(result,indent=2));print(json.dumps(result))
