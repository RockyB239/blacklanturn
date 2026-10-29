"""Source-only packaging contract; never a release/native acceptance receipt."""
import hashlib,importlib.util,json,shutil,subprocess,sys,tempfile,unittest,xml.etree.ElementTree as E,zipfile
from unittest.mock import patch
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];SOURCE=ROOT/'installer-source/plugin.program.blacklanturninstaller'
spec=importlib.util.spec_from_file_location('umbrella_build',ROOT/'tools/build_release.py');BUILD=importlib.util.module_from_spec(spec);spec.loader.exec_module(BUILD)
P='addons/plugin.video.umbrella/';PROGRESS=ROOT/'compatibility/current-addons'
class UmbrellaBuildContract(unittest.TestCase):
 def test_latest_installer_release_metadata_is35(self):
  self.assertEqual(E.parse(SOURCE/'addon.xml').getroot().get('version'),'1.0.41')
 def test_official_full_tree_overlay_preserves_nonprovider_data(self):
  apply=getattr(BUILD,'apply_umbrella',None);self.assertTrue(callable(apply),'Missing pinned current Umbrella overlay')
  data={P+'obsolete.py':b'obsolete90','userdata/addon_data/plugin.video.umbrella/settings.xml':b'private preferences','addons/other/code.py':b'untouched'}
  apply(data)
  record=BUILD.current_addon_manifest()['plugin.video.umbrella']
  expected={P+n:raw for n,raw in BUILD.current_addon_files('plugin.video.umbrella',record).items()}
  self.assertEqual({n:b for n,b in data.items()if n.startswith(P)},expected)
  self.assertEqual(data['userdata/addon_data/plugin.video.umbrella/settings.xml'],b'private preferences')
  self.assertEqual(data['addons/other/code.py'],b'untouched')
 def test_unknown_archive_pin_fails_before_payload_mutation(self):
  with tempfile.TemporaryDirectory()as folder:
   root=Path(folder);p=root/'compatibility/current-addons';p.mkdir(parents=True)
   shutil.copyfile(PROGRESS/'manifest.json',p/'manifest.json')
   record=BUILD.current_addon_manifest()['plugin.video.umbrella']
   (p/record['archive']).write_bytes(b'foreign source archive')
   data={'userdata/keep':b'original'}
   with patch.object(BUILD,'ROOT',root),self.assertRaisesRegex(ValueError,'Current add-on archive changed'):BUILD.apply_umbrella(data)
   self.assertEqual(data,{'userdata/keep':b'original'})
 def test_both_actual_builds_keep_controller85_defaults_and_only_reviewed_provider_changes(self):
  baselines=ROOT/'baselines'
  if not baselines.is_dir():baselines=ROOT.parents[1]/'release136-customization-2026-10-28/public-downloads'
  self.assertTrue(baselines.is_dir(),'Pinned clean build baselines unavailable')
  with tempfile.TemporaryDirectory()as folder:
   from tools import build_release137
   build_release137.build(baselines,Path(folder))
   self.assertTrue((Path(folder)/'plugin.program.blacklanturninstaller-1.0.41.zip').is_file())
   with zipfile.ZipFile(Path(folder)/'plugin.program.blacklanturninstaller-1.0.41.zip') as installer:self.assertEqual(installer.read('plugin.program.blacklanturninstaller/resources/libs/discovery_defaults.py'),(SOURCE/'resources/libs/discovery_defaults.py').read_bytes())
   replay=Path(folder)/'replay'
   result=subprocess.run([sys.executable,'-I','-B',str(ROOT/'tools/build_release137.py'),'--baselines',str(baselines),'--output',str(replay)],capture_output=True,text=True)
   self.assertEqual(result.returncode,0,result.stderr)
   first={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in Path(folder).glob('*.zip')}
   second={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in replay.glob('*.zip')}
   self.assertEqual(first,second,'Build outputs are not reproducible')
   from test_managed_helper import current_data
   current=current_data('plugin.video.umbrella',normalize=False)
   for edition in ('Apple-TV-Mac','General'):
    with self.subTest(edition=edition),zipfile.ZipFile(Path(folder)/('BlackLanturn-'+edition+'-Kodi21-1.1.37.zip'))as z:
     target={n[len(P):]:z.read(n)for n in z.namelist()if n.startswith(P)}
     self.assertEqual(set(target),set(current))
     self.assertEqual(E.fromstring(target['addon.xml']).get('version'),'1:6.7.98+blacklanturn.1')
     self.assertEqual(target,current)
     marker=json.loads(z.read('userdata/blacklanturn-build.json'))
     self.assertEqual(marker['preferences_policy'],'playback-trakt-youtube-umbrella-network-autoplay-1');self.assertEqual(marker['installer_min_version'],'1.0.40')
     self.assertEqual(marker['build_version'],'1.1.37');self.assertEqual(marker['umbrella_patch'],'event-progress-3');self.assertEqual(marker['controller_version'],'0.1.101')
     controller=json.loads((ROOT/'controller-source/manifest101.json').read_text())['files']
     actual={n[len('addons/script.blacklanturn.preview/'):]:hashlib.sha256(z.read(n)).hexdigest()for n in z.namelist()if n.startswith('addons/script.blacklanturn.preview/')}
     self.assertEqual(actual,controller)
     with zipfile.ZipFile(ROOT/'repository.blacklanturn.zip') as repo:self.assertEqual({n:z.read('addons/'+n) for n in repo.namelist()},{n:repo.read(n) for n in repo.namelist()})
     defaults=json.loads((SOURCE/'resources/playback-defaults.json').read_text())
     for name,values in defaults.items():
      raw={n.get('id'):n.text for n in E.fromstring(z.read('userdata/'+name))}
      for key,value in values.items():self.assertEqual(raw[key],value)
     self.assertFalse(any(n.endswith(('.so','.dylib','.dll'))or n.startswith(('addons/inputstream.adaptive/','addons/script.module.pil/'))for n in z.namelist()))
if __name__=='__main__':unittest.main()
