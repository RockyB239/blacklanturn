"""Native category icons follow the selected installed pack, fully offline."""
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'addon';sys.path.insert(0,str(ROOT))
from menu_style import publish_native_icons
import icon_packs
class CategoryIcons(unittest.TestCase):
 def test_all_backend_category_keys_use_the_chosen_existing_pack_assets(self):
  icon_packs.configure([])
  expected={'updates':'updates','downloads':'downloads','search':'search'}
  for pack in ('sculpted-silver','smoked-glass'):
   props={};window=type('Window',(),{'setProperty':lambda self,k,v:props.update({k:v})})()
   publish_native_icons({'IconPack':pack},lambda:window)
   for key,slug in expected.items():
    with self.subTest(pack=pack,key=key):
     value=props.get('BlackLanturn.Icon.'+key,'')
     self.assertTrue(value.endswith('/'+pack+'/'+slug+'.png'))
     self.assertTrue(Path(value).is_file())
if __name__=='__main__':unittest.main()
