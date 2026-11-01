import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
from menu_style import publish_native_icons
import icon_packs
class NativeStyle(unittest.TestCase):
 def test_both_styles_publish_every_native_settings_icon_without_preference_writes(self):
  icon_packs.configure([])
  for pack in ('sculpted-silver','smoked-glass'):
   props={};publish_native_icons({'IconPack':pack},lambda: type('Window',(),{'setProperty':lambda self,k,v:props.update({k:v})})())
   self.assertGreaterEqual(len(props),13)
   self.assertTrue(all('/'+pack+'/' in v and Path(v).is_file() for v in props.values()))
