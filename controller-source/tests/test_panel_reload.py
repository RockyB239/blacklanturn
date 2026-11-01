import unittest,threading
from types import SimpleNamespace
from test_window_lifecycle import ROOT,extract
class Reload(unittest.TestCase):
 def run_reload(self,fail=False,related=False):
  calls=[];focus=3100 if related else 901
  item={'file':'chosen'};control=SimpleNamespace(getSelectedPosition=lambda:1,reset=lambda:calls.append('reset'),addItems=lambda x:calls.append(('items',x)),selectItem=lambda p:calls.append(('select',p)))
  state=SimpleNamespace(alive=True,generation=3,paths=['first','second'],rows=[[{'file':'a'}],[{},item]],selected=item,mode='details' if related else 'home',related_path='similar',related=[{},item],related_history=SimpleNamespace(),related_owner=object(),row_offset=0,row_cache={0:'keep',1:'replace'},preview_dispatch_lock=threading.RLock(),row_labels={1:'Row'},actions_open=False,input_generation=0,config={},
   getFocusId=lambda:focus,getControl=lambda cid:control,stop_preview=lambda:None,setProperty=lambda *x:calls.append(x),update=lambda x:calls.append(('update',x)),setFocusId=lambda cid:calls.append(('focus',cid)),apply_row=lambda *a,**k:calls.append(('apply',a,k)))
  class Inline:
   def __init__(self,target,**kw):self.target=target
   def start(self):self.target()
  def provider(path):
   calls.append(('fetch',path))
   if fail:raise OSError('unavailable')
   return [{'file':'new'},item]
  ns={'threading':SimpleNamespace(Thread=Inline),'get_list':provider,'valid_source':lambda p:True,'provider_path':lambda p:p,'restored_position':lambda f,i,p:p,'item_key':lambda i:i.get('file'),'page_cards':lambda f,*a,**k:(f,1),'media_item':lambda x:x}
  extract(ROOT/'live_review.py','refresh_panel_list',ns,'LiveReview')(state,focus)
  return state,calls
 def test_only_originating_row_is_reloaded(self):
  w,calls=self.run_reload();self.assertEqual([c for c in calls if c[0]=='fetch'],[('fetch','second')]);self.assertEqual(w.row_cache[0],'keep');self.assertFalse(w.actions_open)
 def test_failure_keeps_current_cards_and_focus(self):
  w,calls=self.run_reload(fail=True);self.assertFalse(any(c[0] in ('apply','reset') for c in calls));self.assertEqual(w.rows[1][1],{'file':'chosen'})
 def test_details_list_uses_related_path_not_browse_path(self):
  w,calls=self.run_reload(related=True);self.assertIn(('fetch','similar'),calls);self.assertFalse(any(c[0]=='apply' for c in calls))
