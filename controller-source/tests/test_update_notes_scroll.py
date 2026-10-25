"""Long release notes render completely and expose a remote-scroll focus route."""
import unittest,xml.etree.ElementTree as E
from pathlib import Path
import test_update_notes_runtime as runtime_fixture
from release_updates import write_state
ROOT=Path(__file__).resolve().parents[1]/'addon'
class LongNotesTests(unittest.TestCase):
 setUp=runtime_fixture.HomeUpdatesRuntimeTests.setUp
 def test_complete_long_note_is_delivered_to_native_scrollable_textbox(self):
  bullets=['First complete bullet. '+('Long release detail. '*8),'Last bullet is still reachable.']
  self.state['available']['sections']=[{'heading':'Playback','bullets':bullets},{'heading':'Recovery','bullets':['Final section is reachable too.']}]
  write_state(self.path,self.state)
  class Textbox:
   def setText(self,text):self.text=text
   def scroll(self,line):self.line=line
  body=Textbox();dialog=self.ui.UpdateNotes();dialog.getControl=lambda cid:body
  try:dialog.onInit()
  except AttributeError as exc:self.fail('Release notes cannot use the native scrolling text box: '+str(exc))
  for part in ['Playback',*bullets,'Recovery','Final section is reachable too.']:self.assertIn(part,body.text)
  self.assertLess(body.text.index(bullets[0]),body.text.index(bullets[1]));self.assertEqual(body.line,0)
 def test_remote_focus_reaches_scrollbar_and_returns_to_done(self):
  root=E.parse(ROOT/'resources/skins/Default/1080i/UpdateNotes.xml').getroot()
  controls={n.get('id'):n for n in root.findall('.//control') if n.get('id')}
  body=controls['100'];self.assertEqual(body.get('type'),'textbox','Sections must not clip inside fixed-height list items')
  page=body.findtext('pagecontrol');self.assertIn(page,controls,'Long notes need a real page control')
  self.assertEqual(controls[page].get('type'),'scrollbar')
  self.assertEqual(controls['102'].findtext('onup'),page)
  self.assertEqual(controls[page].findtext('onright'),'102')
  self.assertEqual(root.findtext('defaultcontrol'),page)
