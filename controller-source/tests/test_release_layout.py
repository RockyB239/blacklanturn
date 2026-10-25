import unittest,xml.etree.ElementTree as E
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'addon/resources/skins/Default/1080i'
class ReleaseLayoutTests(unittest.TestCase):
 def test_notice_is_compact_under_clock_and_has_update_later(self):
  tree=E.parse(ROOT/'UpdateNotice.xml');images=tree.findall('.//control[@type="image"]');panel=images[0]
  self.assertLessEqual(int(panel.findtext('width')),680)
  self.assertGreaterEqual(int(panel.findtext('left')),1180)
  self.assertLessEqual(int(panel.findtext('top'))+int(panel.findtext('height')),550)
  self.assertIsNotNone(tree.find('.//control[@id="103"]'))
 def test_notes_match_mockup_hierarchy_and_separate_sections(self):
  t=E.parse(ROOT/'UpdateNotes.xml')
  self.assertTrue(any(n.text=='What’s new' for n in t.findall('.//label')))
  self.assertEqual(t.find('.//control[@id="100"]').get('type'),'textbox')
  self.assertIsNotNone(t.find('.//control[@id="110"][@type="scrollbar"]'))
  self.assertNotIn('Installed add-on changes',(ROOT/'UpdateNotes.xml').read_text())
 def test_long_section_body_has_a_native_page_control(self):
  tree=E.parse(ROOT/'UpdateNotes.xml')
  box=tree.find('.//control[@id="100"]')
  self.assertEqual(box.findtext('pagecontrol'),'110')
  self.assertIsNone(box.find('autoscroll'),'Readers control the pace of long release notes')
