"""The temporary manual override is visible only on its own show's episodes."""
import copy,json,unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
import autoplay_session as session
from types import SimpleNamespace
from test_window_lifecycle import extract,ROOT

class SessionPresentation(unittest.TestCase):
 def item(self,show='2316',season=1,episode=1):
  return {'file':f'plugin://plugin.video.themoviedb.helper/?info=play&tmdb_type=tv&tmdb_id={show}&season={season}&episode={episode}','art':{'thumb':'keep.jpg'},'resume':{'position':12},'playcount':0}
 def policy(self,**kw):return dict(dict(scope=['tmdb:2316','1'],episode=1,ceiling=.1233,debrid='TorBox',created=100,version=1),**kw)
 def test_current_and_later_season_show_indicator_without_mutating_title(self):
  for item in [self.item(),self.item(season=2)]:
   before=copy.deepcopy(item)
   self.assertEqual(session.label(item,json.dumps(self.policy()),101),'Following your selection: TorBox · up to 0.1233 GB')
   self.assertEqual(item,before)
 def test_unrelated_earlier_expired_invalid_and_movie_selections_hide_indicator(self):
  for item,raw,now in [(self.item('999'),json.dumps(self.policy()),101),(self.item(season=0),json.dumps(self.policy()),101),(self.item(),json.dumps(self.policy()),21701),(self.item(),'[]',101),({'file':'plugin://plugin.video.youtube/play/?video_id=123'},json.dumps(self.policy()),101),(self.item(),json.dumps(self.policy(ceiling=0)),101)]:
   self.assertEqual(session.label(item,raw,now),'')
 def test_reset_invalidates_runtime_choice_and_prepared_url_only(self):
  props={session.PROPERTY:'choice',session.PREPARED:'stamp',session.URL:'url','unrelated':'keep'}
  class Window:
   def clearProperty(self,key):props.pop(key,None)
  session.clear(Window());self.assertEqual(props,{'unrelated':'keep'})
 def test_scrolling_reuses_read_but_options_can_force_current_policy(self):
  reads=[];clock=[100.0];item=self.item();raw=json.dumps(self.policy())
  obj=SimpleNamespace()
  fn=extract(ROOT/'live_review.py','source_session_label',{'time':SimpleNamespace(monotonic=lambda:clock[0]),'autoplay_session':SimpleNamespace(PROPERTY=session.PROPERTY,label=lambda i,v:v),'gui_labels':lambda keys:reads.append(keys) or {keys[0]:raw}},'LiveReview')
  for _ in range(100):self.assertEqual(fn(obj,item),raw)
  self.assertEqual(len(reads),1)
  fn(obj,item,refresh=True);self.assertEqual(len(reads),2)
  clock[0]+=2;fn(obj,item);self.assertEqual(len(reads),3)
 def test_indicator_fits_above_playback_buttons_in_full_and_compact_hero(self):
  import xml.etree.ElementTree as E
  root=E.parse(ROOT/'resources/skins/Default/1080i/LiveReview.xml').getroot()
  label=next(x for x in root.findall('.//control') if x.findtext('label')=='$INFO[Window.Property(sourceSession)]')
  play=root.find('.//control[@id="101"]')
  self.assertLessEqual(int(label.findtext('top'))+int(label.findtext('height')),int(play.findtext('top')))
  self.assertEqual(label.find('animation').get('end'),'0,-180')
  self.assertIn('hasSelection',label.findtext('visible'))
