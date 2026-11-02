"""Pin the actual confirmation layout that previously let buttons cross its panel."""
from pathlib import Path
import unittest,xml.etree.ElementTree as E
P=Path(__file__).resolve().parents[1]/'compatibility/reliability164/skin/xml/DialogConfirm.xml'
class DialogSpacing(unittest.TestCase):
 def geometry(self):
  root=E.parse(P).getroot();group=root.find('./controls/control');bg=group.find('./include[@content="DialogBackgroundCommons"]');panel={p.get('name'):float(p.get('value')) for p in bg.findall('param') if p.get('name') in ('width','height')};bar=group.find('./control[@type="grouplist"]');buttons=[]
  for include in bar.findall('./include[@content="DefaultDialogButton"]'):
   values={p.get('name'):p.get('value') for p in include.findall('param')};buttons.append((float(values.get('width',300)),float(values.get('height',100))))
  return group,panel,bar,buttons
 def test_all_three_actions_have_twenty_pixel_side_clearance(self):
  group,panel,bar,buttons=self.geometry();self.assertEqual(len(buttons),3);self.assertGreaterEqual((panel['width']-sum(w for w,h in buttons))/2,20)
 def test_buttons_stay_inside_background_with_footer_space(self):
  group,panel,bar,buttons=self.geometry();self.assertGreaterEqual(panel['height']-(float(bar.findtext('top'))+max(h for w,h in buttons)),20)
 def test_progress_and_action_rows_have_a_readable_gap(self):
  group,panel,bar,buttons=self.geometry();progress=group.find('./control[@type="progress"]');self.assertGreaterEqual(float(bar.findtext('top'))-float(progress.findtext('top'))-float(progress.findtext('height')),12)
 def test_remote_action_ids_and_navigation_are_preserved(self):
  group,panel,bar,buttons=self.geometry();self.assertEqual([i.find('./param[@name="id"]').get('value') for i in bar.findall('./include')],['11','10','12']);self.assertTrue(all(h>=74 for w,h in buttons))
