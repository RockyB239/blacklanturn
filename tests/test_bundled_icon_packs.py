"""Catch omission of approved artwork from public installs and updates."""
import hashlib,importlib.util,json,sys,tempfile,unittest,xml.etree.ElementTree as E,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ICONS=ROOT/'controller-source/addon/resources/icon-packs'
class PublicIconPacks(unittest.TestCase):
 def test_new_install_can_select_both_packs_and_keeps_explicit_original_choice(self):
  self.assertTrue((ICONS/'blacklanturn-icons.json').is_file(),'Approved branded packs are missing from public source')
  sys.path.insert(0,str(ROOT/'controller-source/addon'))
  import icon_packs
  try:
   icon_packs.configure([]);self.assertEqual(icon_packs.selected_pack({}),'sculpted-silver')
   for pack in ('sculpted-silver','smoked-glass'):
    self.assertIn(pack,dict(icon_packs.PACK_CHOICES))
    for icon in ('home','search','tv','movies','youtube','fighting-glove'):
     path=Path(icon_packs.icon_path(ROOT/'controller-source/addon',icon,pack))
     self.assertTrue(path.is_file(),(pack,icon));self.assertIn(str(ICONS),str(path))
   self.assertEqual(icon_packs.selected_pack({'IconPack':'original'}),'original')
   self.assertEqual(icon_packs.selected_pack({'IconPack':'smoked-glass'}),'smoked-glass')
  finally:icon_packs.configure([])
 def test_bundled_artwork_matches_the_controller_manifest(self):
  self.assertTrue((ICONS/'blacklanturn-icons.json').is_file(),'Builtin branded icons are missing')
  manifest=json.loads((ROOT/'controller-source/manifest102.json').read_text())['files']
  for path in ICONS.rglob('*'):
   if path.is_file():self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),manifest[path.relative_to(ROOT/'controller-source/addon').as_posix()])
  for pack in ('sculpted-silver','smoked-glass'):self.assertEqual(len(list((ICONS/'packs'/pack).glob('*.png'))),90)
 def test_both_release_editions_and_components_include_the_resource_without_fight_zone(self):
  builder=ROOT/'tools/build_release138.py';self.assertTrue(builder.is_file(),'Current release builder does not bundle the approved packs')
  baselines=ROOT/'baselines'
  if not (baselines/'BlackLanturn-General-Kodi21-1.1.37.zip').is_file():baselines=ROOT.parent.parent/'release137-options-2026-10-29/public-downloads'
  if not (baselines/'BlackLanturn-General-Kodi21-1.1.37.zip').is_file():self.skipTest('Pinned public30 artifacts required for build integration')
  spec=importlib.util.spec_from_file_location('test_public_icons_builder',builder);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  with tempfile.TemporaryDirectory() as t:
   out=Path(t);module.build(baselines,out)
   for edition in ('General','Apple-TV-Mac'):
    for name in ('BlackLanturn-'+edition+'-Kodi21-1.1.38.zip','BlackLanturn-'+edition+'-Update-1.1.37-to-1.1.38.zip'):
     with zipfile.ZipFile(out/name) as z:
      self.assertIn('addons/script.blacklanturn.preview/resources/icon-packs/packs/sculpted-silver/home.png',z.namelist())
      self.assertIn('addons/script.blacklanturn.preview/resources/icon-packs/packs/smoked-glass/home.png',z.namelist())
      self.assertFalse(any(n.startswith(('addons/plugin.video.blacklanturn.fights/','addons/resource.images.blacklanturn.personal/')) for n in z.namelist()))
      expected={p.relative_to(ICONS).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in ICONS.rglob('*') if p.is_file()};prefix='addons/script.blacklanturn.preview/resources/icon-packs/'
      self.assertEqual({n[len(prefix):]:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith(prefix)},expected)
