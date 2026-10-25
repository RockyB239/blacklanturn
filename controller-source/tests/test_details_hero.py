"""Details artwork/video share compact framing without moving metadata."""
import unittest,sys
from pathlib import Path
from xml.etree import ElementTree as E
ROOT=Path(__file__).resolve().parents[1]/'addon'
sys.path.insert(0,str(ROOT))
class DetailsHero(unittest.TestCase):
 def test_details_uses_compact_video_fit_even_with_large_metadata(self):
  from preview_geometry import preview_uses_compact_hero
  for compact in (True,False):self.assertTrue(preview_uses_compact_hero('details',compact))
  self.assertTrue(preview_uses_compact_hero('home',True));self.assertFalse(preview_uses_compact_hero('home',False))
  self.assertFalse(preview_uses_compact_hero('settings',True))
 def test_details_art_video_and_all_fades_use_the_same_compact_area(self):
  group=E.parse(ROOT/'resources/skins/Default/1080i/LiveReview.xml').find('./controls/control[@type="group"]')
  hero=group.findall('control')[:11]
  for c in hero:
   self.assertIn('String.IsEqual(Window.Property(page),details)',c.findtext('visible'))
  compact=[c for c in hero if c.findtext('left')=='320'and c.findtext('width')=='1530']
  self.assertTrue(any(c.get('type')=='videowindow'for c in compact))
  self.assertTrue(any(c.findtext('texture')=='$INFO[Window.Property(hero)]'for c in compact))
  self.assertEqual({c.findtext('texture')for c in hero if c.findtext('texture','').startswith('preview-edge-')},{'preview-edge-left.png','preview-edge-right.png','preview-edge-bottom.png'})
  # Metadata keeps its existing Details layout; only decorative framing changes.
  self.assertNotIn('String.IsEqual(Window.Property(page),details)',group.findall('control')[11].findtext('visible'))
