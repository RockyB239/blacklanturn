import json,tempfile,unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
class Extensions(unittest.TestCase):
 def test_inline_entry_requires_installed_owner_and_contained_python_file(self):
  from extensions import inline_request
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);(root/'window.py').write_text('pass')
   (root/'blacklanturn-extension.json').write_text(json.dumps({'schema':1,'inline':{'entry':'window.py'}}))
   route=inline_request('plugin://plugin.video.personal/',lambda aid:root)
   self.assertEqual(route,{'addon':'plugin.video.personal','entry':'window.py'})
   for entry in ('../window.py','/tmp/evil.py','window.py;bad','https://evil/x.py'):
    (root/'blacklanturn-extension.json').write_text(json.dumps({'schema':1,'inline':{'entry':entry}}))
    self.assertIsNone(inline_request('plugin://plugin.video.personal/',lambda aid:root))
 def test_does_not_intercept_actions_or_disabled_addons(self):
  from extensions import inline_request
  self.assertIsNone(inline_request('plugin://plugin.video.personal/?play=1',lambda aid:None))
  self.assertIsNone(inline_request('plugin://plugin.video.personal/',lambda aid:None))
 def test_malformed_or_linked_descriptor_falls_back_without_mutation(self):
  from extensions import inline_request
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);(root/'blacklanturn-extension.json').write_text('not json')
   self.assertIsNone(inline_request('plugin://plugin.video.personal/',lambda aid:root))
 def test_external_icons_survive_controller_tree_replacement(self):
  import icon_packs
  with tempfile.TemporaryDirectory() as t:
   host=Path(t)/'host';external=Path(t)/'icons';external.mkdir();(external/'silver').mkdir();(external/'silver/home.png').write_bytes(b'png')
   descriptor={'schema':1,'packs':[{'id':'silver','label':'Silver','directory':'silver'}],'icons':[['fighting-glove','Fighting glove']]}
   (external/'blacklanturn-icons.json').write_text(json.dumps(descriptor))
   icon_packs.configure([external])
   self.assertEqual(icon_packs.icon_path(host,'home','silver'),str((external/'silver/home.png').resolve()))
   self.assertIn(('fighting-glove','Fighting glove'),icon_packs.EXTRA_ICON_CHOICES)
   self.assertEqual(icon_packs.with_pack({'Saved':[1]},'silver')['Saved'],[1])
 def test_registered_assets_reuse_validated_paths_and_disabled_pack_is_removed(self):
  import icon_packs
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);pack=root/'silver';pack.mkdir();(pack/'home.png').write_bytes(b'png')
   outside=root/'outside.png';outside.write_bytes(b'outside');(pack/'escape.png').symlink_to(outside)
   (root/'blacklanturn-icons.json').write_text(json.dumps({'schema':1,'packs':[{'id':'silver','label':'Silver','directory':'silver'}],'icons':[]}))
   icon_packs.configure([root])
   with patch.object(icon_packs,'contained',side_effect=AssertionError('Repeated filesystem validation')):
    for _ in range(50):self.assertEqual(icon_packs.icon_path(root,'home','silver'),str((pack/'home.png').resolve()))
    self.assertNotEqual(icon_packs.icon_path(root,'escape','silver'),str(pack/'escape.png'))
   icon_packs.configure([]);self.assertNotEqual(icon_packs.icon_path(root,'home','silver'),str((pack/'home.png').resolve()))
 def test_icon_paths_cannot_escape_owner(self):
  import icon_packs
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);(root/'blacklanturn-icons.json').write_text(json.dumps({'schema':1,'packs':[{'id':'evil','label':'Bad','directory':'../outside'}],'icons':[]}))
   icon_packs.configure([root]);self.assertNotIn('evil',dict(icon_packs.PACK_CHOICES))

class DeclaredRoutes(unittest.TestCase):
 def test_existing_sidebar_open_action_is_declared_without_changing_saved_navigation(self):
  from extensions import inline_request
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);(root/'window.py').write_text('pass');(root/'blacklanturn-extension.json').write_text(json.dumps({'schema':1,'inline':{'entry':'window.py','query':{'open':'1'}}}))
   self.assertIsNotNone(inline_request('plugin://plugin.video.personal/?open=1',lambda aid:root))
   self.assertIsNone(inline_request('plugin://plugin.video.personal/?tracking=sync',lambda aid:root))
