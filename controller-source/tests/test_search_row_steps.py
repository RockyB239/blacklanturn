"""Search traversal retains usable rows across empty/error provider categories."""
import unittest
from types import MethodType,SimpleNamespace
import test_discovery_controller as fixture
from test_window_lifecycle import extract,ROOT

class SearchRowSteps(unittest.TestCase):
 def state(self,provider=None):
  queue=[]
  class Queued(fixture.SyncThread):
   def start(self):queue.append(self.target)
  w,calls,controls=fixture.DiscoveryController().state(thread=Queued,provider=provider)
  w.search_state={'query':'A24','kind':'all'};w.adaptive_browsing=True;w.input_generation=0;w.focus=900
  w.getFocusId=lambda:w.focus;w.setFocusId=lambda cid:setattr(w,'focus',cid)
  return w,calls,controls,queue
 def drain(self,q):
  for _ in range(30):
   if not q:return
   q.pop(0)()
  self.fail('Unbounded row transition')
 def test_skips_empty_middle_and_never_enters_empty_tail(self):
  def provider(p):
   if p=='error':raise RuntimeError('unavailable')
   return [] if p=='empty' else [{'file':p+'/title'}]
  w,_,c,q=self.state(provider)
  w.set_rows([{'label':p,'path':p} for p in ('first','empty','second','error')]);self.drain(q);w.focus=900
  w.shift_rows(1,0);self.drain(q)
  self.assertEqual(w.row_offset,2);self.assertEqual(w.rows[0][0]['file'],'second/title');self.assertEqual(w.focus,900)
  w.shift_rows(1,0);self.drain(q)
  self.assertEqual(w.row_offset,2);self.assertEqual(w.focus,900)
  w.shift_rows(-1,0);self.drain(q)
  self.assertEqual(w.row_offset,0);self.assertEqual(w.focus,900)
 def test_keeps_current_row_while_unknown_next_row_loads(self):
  w,_,c,q=self.state(lambda p:[] if p=='empty' else [{'file':p+'/title'}])
  w.set_rows([{'label':p,'path':p} for p in ('first','empty','next')]);self.drain(q);w.focus=900
  w.shift_rows(1,0)
  self.assertEqual(w.row_offset,0);self.assertEqual(w.rows[0][0]['file'],'first/title');self.assertEqual(w.focus,900)
  self.drain(q);self.assertEqual(w.row_offset,2)
 def test_navigation_away_cancels_pending_step(self):
  w,_,c,q=self.state(lambda p:[] if p=='empty' else [{'file':p+'/title'}])
  w.set_rows([{'label':p,'path':p} for p in ('first','empty','next')]);self.drain(q);w.focus=900
  w.shift_rows(1,0);w.input_generation+=1;w.focus=600;self.drain(q)
  self.assertEqual(w.row_offset,0);self.assertEqual(w.focus,600)
 def test_down_from_category_enters_row_without_skipping_from_stale_monitor_focus(self):
  w,_,c,q=self.state();w.set_rows([{'label':str(i),'path':str(i)} for i in range(3)]);self.drain(q)
  w.focus=600;w.focus_key=(900,0)
  action=extract(ROOT/'live_review.py','onAction',{},'LiveReview')
  action(w,SimpleNamespace(getId=lambda:4));self.drain(q)
  self.assertEqual(w.row_offset,0);self.assertEqual(w.focus,900)
 def test_rapid_down_steps_do_not_depend_on_monitor_focus_key(self):
  w,_,c,q=self.state();w.set_rows([{'label':str(i),'path':str(i)} for i in range(3)]);self.drain(q)
  w.focus=900;w.focus_key=(600,0)
  action=extract(ROOT/'live_review.py','onAction',{},'LiveReview')
  action(w,SimpleNamespace(getId=lambda:4));self.drain(q)
  self.assertEqual(w.row_offset,1)

 def test_up_from_first_usable_row_returns_to_categories_after_empty_leading_rows(self):
  for empty_count in (1,2):
   with self.subTest(empty_count=empty_count):
    w,_,c,q=self.state(lambda p:[] if p.startswith('empty') else [{'file':p+'/title'}])
    w.set_rows([{'label':p,'path':p} for p in ['empty'+str(i) for i in range(empty_count)]+['found']]);self.drain(q)
    if empty_count==1:w.focus=901
    else:w.show_row_window(2,0);self.drain(q);w.focus=900
    action=extract(ROOT/'live_review.py','onAction',{},'LiveReview')
    action(w,SimpleNamespace(getId=lambda:3));self.drain(q)
    self.assertEqual(w.focus,600)
 def test_mouse_down_arrow_advances_one_row_and_keeps_hover_focus(self):
  w,_,c,q=self.state();w.set_rows([{'label':str(i),'path':str(i)} for i in range(4)]);self.drain(q)
  w.focus=701;w.shift_rows(1,1);self.drain(q)
  self.assertEqual(w.row_offset,1);self.assertEqual(w.focus,701)

 def test_first_mouse_wheel_from_categories_moves_row(self):
  w,_,c,q=self.state();w.set_rows([{'label':str(i),'path':str(i)} for i in range(3)]);self.drain(q)
  w.focus=600;w.mouse=False
  w.arrow=MethodType(extract(ROOT/'live_review.py','arrow',{'event':lambda *a,**kw:None},'LiveReview'),w)
  extract(ROOT/'live_review.py','onAction',{},'LiveReview')(w,SimpleNamespace(getId=lambda:105));self.drain(q)
  self.assertEqual(w.row_offset,1);self.assertEqual(w.focus,701)
 def test_down_from_empty_initial_window_finds_later_results(self):
  w,_,c,q=self.state(lambda p:[] if p.startswith('empty') else [{'file':p+'/title'}])
  w.set_rows([{'label':p,'path':p} for p in ('empty0','empty1','found')]);self.drain(q);w.focus=600
  extract(ROOT/'live_review.py','onAction',{},'LiveReview')(w,SimpleNamespace(getId=lambda:4));self.drain(q)
  self.assertEqual(w.row_offset,2);self.assertEqual(w.focus,900)

 def test_down_from_hero_enters_categories_then_first_row(self):
  w,_,c,q=self.state();w.set_rows([{'label':str(i),'path':str(i)} for i in range(3)]);self.drain(q)
  down={};identity={id(v):k for k,v in c.items()}
  for cid,control in c.items():control.controlDown=lambda target,cid=cid:down.__setitem__(cid,identity[id(target)])
  w.row_navigation();w.focus=101
  action=extract(ROOT/'live_review.py','onAction',{},'LiveReview')
  def press_down():
   w.focus=down.get(w.focus,w.focus);action(w,SimpleNamespace(getId=lambda:4));self.drain(q)
  press_down();self.assertEqual(w.focus,600);self.assertEqual(w.row_offset,0)
  press_down();self.assertEqual(w.focus,900);self.assertEqual(w.row_offset,0)

 def test_leaving_search_restores_all_hero_down_routes(self):
  w,_,c,q=self.state();w.set_rows([{'label':'first','path':'first'}]);self.drain(q)
  down={};identity={id(v):k for k,v in c.items()}
  for cid,control in c.items():control.controlDown=lambda target,cid=cid:down.__setitem__(cid,identity[id(target)])
  w.row_navigation()
  self.assertEqual(down[102],102)
  w.search_state=None;w.row_navigation()
  for cid in (101,102,103,105,106):self.assertEqual(down[cid],900)

if __name__=='__main__':unittest.main()
