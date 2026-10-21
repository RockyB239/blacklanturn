"""Source-only packaging contract; never a release/native acceptance receipt."""
import hashlib,importlib.util,json,shutil,subprocess,sys,tempfile,unittest,xml.etree.ElementTree as E,zipfile
from unittest.mock import patch
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];SOURCE=ROOT/'installer-source/plugin.program.blacklanturninstaller'
spec=importlib.util.spec_from_file_location('umbrella_build',ROOT/'tools/build_release.py');BUILD=importlib.util.module_from_spec(spec);spec.loader.exec_module(BUILD)
P='addons/plugin.video.umbrella/';PROGRESS=ROOT/'compatibility/umbrella-progress'
class UmbrellaBuildContract(unittest.TestCase):
 def test_installer18_source_metadata_is_local_only(self):
  self.assertEqual(E.parse(SOURCE/'addon.xml').getroot().get('version'),'1.0.21')
 def test_official_full_tree_overlay_preserves_nonprovider_data(self):
  apply=getattr(BUILD,'apply_umbrella',None);self.assertTrue(callable(apply),'Missing pinned official92 overlay')
  data={P+'obsolete.py':b'obsolete90','userdata/addon_data/plugin.video.umbrella/settings.xml':b'private preferences','addons/other/code.py':b'untouched'}
  apply(data)
  with zipfile.ZipFile(PROGRESS/'upstream-6.7.92.zip')as z:expected={P+n.split('/',1)[1]:z.read(n)for n in z.namelist()if not n.endswith('/')}
  for p in (ROOT/'compatibility/autoplay-size/candidate').rglob('*.py'):
   expected[P+p.relative_to(ROOT/'compatibility/autoplay-size/candidate').as_posix()]=p.read_bytes()
  self.assertEqual({n:b for n,b in data.items()if n.startswith(P)},expected)
  self.assertEqual(data['userdata/addon_data/plugin.video.umbrella/settings.xml'],b'private preferences')
  self.assertEqual(data['addons/other/code.py'],b'untouched')
 def test_unknown_archive_or_player_pin_fails_before_payload_mutation(self):
  with tempfile.TemporaryDirectory()as folder:
   root=Path(folder);p=root/'compatibility/umbrella-progress';p.mkdir(parents=True)
   (p/'upstream-6.7.92.zip').write_bytes(b'foreign source archive')
   data={'userdata/keep':b'original'}
   with patch.object(BUILD,'ROOT',root),self.assertRaisesRegex(AssertionError,'Official Umbrella archive changed'):BUILD.apply_umbrella(data)
   self.assertEqual(data,{'userdata/keep':b'original'})
   shutil.copyfile(PROGRESS/'upstream-6.7.92.zip',p/'upstream-6.7.92.zip')
   shutil.copyfile(PROGRESS/'upstream-6.7.92-manifest.json',p/'upstream-6.7.92-manifest.json')
   candidate=p/'duration-candidate/6.7.92/player.py';candidate.parent.mkdir(parents=True);candidate.write_bytes(b'foreign candidate player')
   with patch.object(BUILD,'ROOT',root),self.assertRaisesRegex(AssertionError,'Reviewed Umbrella player changed'):BUILD.apply_umbrella(data)
   self.assertEqual(data,{'userdata/keep':b'original'})
 def test_both_actual_builds_keep_controller85_defaults_and_only_reviewed_provider_changes(self):
  baselines=ROOT/'baselines'
  if not baselines.is_dir():baselines=ROOT.parents[1]/'helper-managed-release-1.1.2/artifacts'
  self.assertTrue(baselines.is_dir(),'Pinned clean build baselines unavailable')
  with tempfile.TemporaryDirectory()as folder:
   BUILD.build(baselines,Path(folder))
   self.assertTrue((Path(folder)/'plugin.program.blacklanturninstaller-1.0.21.zip').is_file())
   self.assertEqual((Path(folder)/'plugin.program.blacklanturninstaller-1.0.21.zip').read_bytes(),(ROOT/'plugin.program.blacklanturninstaller/plugin.program.blacklanturninstaller-1.0.21.zip').read_bytes())
   replay=Path(folder)/'replay'
   result=subprocess.run([sys.executable,'-I','-B',str(ROOT/'tools/build_release.py'),'--baselines',str(baselines),'--output',str(replay)],capture_output=True,text=True)
   self.assertEqual(result.returncode,0,result.stderr)
   first={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in Path(folder).glob('*.zip')}
   second={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in replay.glob('*.zip')}
   self.assertEqual(first,second,'Build outputs are not reproducible')
   with zipfile.ZipFile(PROGRESS/'upstream-6.7.92.zip')as z:upstream={n.split('/',1)[1]:z.read(n)for n in z.namelist()if not n.endswith('/')}
   for edition in ('Apple-TV-Mac','General'):
    with self.subTest(edition=edition),zipfile.ZipFile(Path(folder)/('BlackLanturn-'+edition+'-Kodi21-1.1.16.zip'))as z:
     target={n[len(P):]:z.read(n)for n in z.namelist()if n.startswith(P)}
     self.assertEqual(set(target),set(upstream))
     self.assertEqual({n for n in upstream if target[n]!=upstream[n]}, {'resources/lib/modules/'+n for n in ('player.py','sources.py','source_preferences.py')})
     self.assertEqual(hashlib.sha256(target['resources/lib/modules/player.py']).hexdigest(),'5766e60fe02858d5cd5b4d38c03cf8f8f3de9d5e8dbb1b3d85a468f922f2be0b')
     marker=json.loads(z.read('userdata/blacklanturn-build.json'))
     self.assertEqual(marker['preferences_policy'],'playback-trakt-youtube-umbrella-network-autoplay-1');self.assertEqual(marker['installer_min_version'],'1.0.20')
     self.assertEqual(marker['build_version'],'1.1.16');self.assertEqual(marker['umbrella_patch'],'event-progress-3');self.assertEqual(marker['controller_version'],'0.1.85')
     controller=json.loads((ROOT/'controller-source/manifest85.json').read_text())['files']
     actual={n[len('addons/script.blacklanturn.preview/'):]:hashlib.sha256(z.read(n)).hexdigest()for n in z.namelist()if n.startswith('addons/script.blacklanturn.preview/')}
     self.assertEqual(actual,controller)
     defaults=json.loads((SOURCE/'resources/playback-defaults.json').read_text())
     for name,values in defaults.items():
      raw={n.get('id'):n.text for n in E.fromstring(z.read('userdata/'+name))}
      for key,value in values.items():self.assertEqual(raw[key],value)
     self.assertFalse(any(n.endswith(('.so','.dylib','.dll'))or n.startswith(('addons/inputstream.adaptive/','addons/script.module.pil/'))for n in z.namelist()))
if __name__=='__main__':unittest.main()
