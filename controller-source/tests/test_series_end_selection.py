"""The suggested show remains explicit when remote focus moves to its actions."""
import json,tempfile,unittest,xml.etree.ElementTree as E
from pathlib import Path
from types import SimpleNamespace,MethodType
from test_window_lifecycle import ROOT,extract
class Selection(unittest.TestCase):
 def window(self):
  props={};up={};controls={k:SimpleNamespace(controlUp=lambda target,k=k:up.__setitem__(k,target)) for k in range(7010,7015)}
  cards={7000:object(),7001:object(),7002:object()};controls.update(cards)
  w=SimpleNamespace(items=[{'title':s,'file':'plugin://x/?tmdb_type=tv&tmdb_id='+str(i),'type':'tvshow'} for i,s in enumerate(('First','Second','Third'))],selection=0,setProperty=props.__setitem__,getControl=controls.__getitem__)
  w.selected=MethodType(extract(ROOT/'series_end_ui.py','selected',{},'SeriesEndDialog'),w)
  w.select_suggestion=MethodType(extract(ROOT/'series_end_ui.py','select_suggestion',{},'SeriesEndDialog'),w)
  return w,props,up,cards
 def test_third_card_stays_named_and_actions_return_to_it(self):
  w,props,up,cards=self.window();w.select_suggestion(2)
  self.assertEqual(w.selection,2);self.assertIn('Third',props['status']);self.assertEqual(props['selectedCard'],'2')
  self.assertEqual(list(up),list(range(7010,7015)));self.assertTrue(all(v is cards[7002] for v in up.values()))
 def test_focus_selects_second_and_clicking_open_keeps_its_identity(self):
  w,props,_,_=self.window();w.selected=lambda:w.items[w.selection];w.finish=lambda:None
  extract(ROOT/'series_end_ui.py','onFocus',{},'SeriesEndDialog')(w,7001)
  extract(ROOT/'series_end_ui.py','onClick',{},'SeriesEndDialog')(w,7010)
  self.assertIn('Second',props['status']);self.assertEqual(w.result['item']['title'],'Second')
 def test_one_card_cannot_leave_an_action_pointing_at_missing_card(self):
  w,props,up,cards=self.window();w.items=w.items[:1];w.select_suggestion(2)
  self.assertEqual(w.selection,0);self.assertTrue(all(v is cards[7000] for v in up.values()))
 def test_selected_frame_remains_visible_while_buttons_have_focus(self):
  root=E.parse(ROOT/'resources/skins/Default/1080i/SeriesEnd.xml').getroot()
  for i in range(3):
   node=next(n for n in root.iter('control') if n.get('id')==str(7200+i))
   self.assertIn('selectedCard',node.findtext('visible'));self.assertNotIn('Control.HasFocus',node.findtext('visible'))
if __name__=='__main__':unittest.main()
