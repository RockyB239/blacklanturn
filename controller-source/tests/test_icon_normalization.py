import importlib.util
from pathlib import Path
import unittest
from PIL import Image, ImageDraw

class IconNormalization(unittest.TestCase):
 def test_small_and_large_artwork_share_visible_size_without_distortion(self):
  path=Path(__file__).parents[1]/'branding/icon-pack/build_pack.py'
  spec=importlib.util.spec_from_file_location('icon_pack',path)
  pack=importlib.util.module_from_spec(spec);spec.loader.exec_module(pack)
  self.assertTrue(hasattr(pack,'normalize_icon'),'Native exports need visible-bound normalization')
  for bounds in [(80,100,175,155),(25,25,230,230)]:
   source=Image.new('RGBA',(256,256));draw=ImageDraw.Draw(source)
   draw.rectangle(bounds,fill=(220,235,240,255))
   # A nearly invisible pixel must not make the small glyph appear smaller.
   source.putpixel((0,0),(220,235,240,1))
   result=pack.normalize_icon(source)
   bbox=result.getchannel('A').point(lambda a:255 if a>=40 else 0).getbbox()
   width,height=bbox[2]-bbox[0],bbox[3]-bbox[1]
   self.assertLessEqual(abs(max(width,height)-216),2)
   self.assertLessEqual(abs((bbox[0]+bbox[2])/2-128),1)
   self.assertLessEqual(abs((bbox[1]+bbox[3])/2-128),1)
   expected=(bounds[2]-bounds[0]+1)/(bounds[3]-bounds[1]+1)
   self.assertAlmostEqual(width/height,expected,delta=.04)
