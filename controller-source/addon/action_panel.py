"""Native remote-first Action Panel. All work is dispatched after it closes."""
from pathlib import Path
import time
import xbmcgui
from action_panel_model import build_panel,panel_header
from icon_packs import icon_path,selected_pack
ROOT=Path(__file__).resolve().parent
BACK=(9,10,92,216,247)

class ActionPanel(xbmcgui.WindowXMLDialog):
 def onInit(self):
  self.result=None;self.active_group=None;self.active_actions=[];self.origin=0
  head=panel_header(self.item,self.section)
  for key,value in head.items():self.setProperty(key,value)
  self.getControl(101).setLabel(head['title']);self.getControl(102).setLabel(head['meta']);self.getControl(103).setImage(head['art'])
  quick=self.model['quick'];groups=self.model['groups'];self.quick_ids=[];self.group_ids=[]
  for n in range(5):
   button=self.getControl(1000+n);button.setVisible(n<len(quick));self.getControl(2300+n).setVisible(n<len(quick))
   if n>=len(quick):continue
   self.quick_ids.append(1000+n);button.setPosition(188+n*(1544//max(1,len(quick))),286);button.setWidth(1544//max(1,len(quick))-18)
   button.setLabel(quick[n]['label'])
   icon=self.getControl(2300+n);icon.setPosition(188+n*(1544//max(1,len(quick)))+(1544//max(1,len(quick))-18)//2-min(300,len(quick[n]['label'])*15)//2-49,304);icon.setWidth(42);icon.setHeight(42)
   slug={'play':'continue-watching','browse_episodes':'continue-watching','player':'video-addons','details':'guide','genre':'genres','jump_streaming_shelf':'genres'}.get(quick[n]['id'])
   icon.setImage(icon_path(ROOT,slug or 'collections',self.pack));icon.setVisible(bool(slug))
  for n in range(5):
   button=self.getControl(1100+n);button.setVisible(n<len(groups));self.getControl(2100+n).setVisible(n<len(groups));self.getControl(2200+n).setVisible(n<len(groups))
   if n>=len(groups):continue
   self.group_ids.append(1100+n);button.setLabel(groups[n]['label'])
   self.getControl(2100+n).setImage(icon_path(ROOT,groups[n]['icon'],self.pack))
  self.getControl(5100).setVisible(bool(groups))
  target=self.group_ids[0] if groups else self.quick_ids[0] if quick else 1999
  for n,cid in enumerate(self.quick_ids):
   c=self.getControl(cid);c.controlLeft(self.getControl(self.quick_ids[max(0,n-1)]));c.controlRight(self.getControl(self.quick_ids[min(len(self.quick_ids)-1,n+1)]));c.controlDown(self.getControl(target));c.controlUp(self.getControl(1999))
  for n,cid in enumerate(self.group_ids):
   c=self.getControl(cid);c.controlLeft(c);c.controlRight(self.getControl(5100));c.controlUp(self.getControl(self.group_ids[n-1] if n else self.quick_ids[0] if quick else 1999));c.controlDown(self.getControl(self.group_ids[min(n+1,len(self.group_ids)-1)]))
  self.getControl(1999).controlDown(self.getControl(self.quick_ids[-1] if quick else target));self.getControl(1999).controlLeft(self.getControl(self.quick_ids[-1] if quick else target))
  if groups:self.show_group(next((n for n,g in enumerate(groups) if g['id']=='refresh'),0))
  self.setFocusId(self.quick_ids[0] if quick else target)
  self.setProperty('panelReadyMs',str(round((time.monotonic()-self.opened_at)*1000,1)))
 def show_actions(self,title,actions,origin):
  self.active_actions=actions;self.origin=origin;self.getControl(104).setLabel(title)
  control=self.getControl(5100);control.reset();control.setVisible(bool(actions));items=[]
  for action in actions:
   li=xbmcgui.ListItem(label=action['label'],label2=action.get('description',''));items.append(li)
  control.addItems(items);control.selectItem(0)
  control.controlLeft(self.getControl(origin));control.controlRight(control);control.controlUp(self.getControl(self.quick_ids[0] if self.quick_ids else origin))
 def show_group(self,n):
  if self.active_group==n:return
  self.active_group=n;group=self.model['groups'][n]
  for i in range(5):self.getControl(2200+i).setVisible(i==n)
  self.show_actions(group['label'],group['actions'],1100+n)
 def onFocus(self,cid):
  if 1100<=cid<1100+len(self.model['groups']):self.show_group(cid-1100)
 def onClick(self,cid):
  if cid==1999:self.close();return
  if cid in self.quick_ids:
   action=self.model['quick'][cid-1000]
   if action['id']=='player':
    self.active_group=None
    for i in range(5):self.getControl(2200+i).setVisible(False)
    primary=dict(action,label='Choose player or source…',description='Open your available playback choices for this title.')
    self.show_actions('Play using',[primary]+self.model['playback'],cid);self.setFocusId(5100);return
   self.result=action['id'];self.close()
  elif cid in self.group_ids:self.show_group(cid-1100);self.setFocusId(5100)
  elif cid==5100:
   n=self.getControl(5100).getSelectedPosition()
   if 0<=n<len(self.active_actions):self.result=self.active_actions[n]['id'];self.close()
 def onAction(self,action):
  if action.getId() in BACK:
   if self.getFocusId()==5100:self.setFocusId(self.origin)
   else:self.close()

def choose_action(options,item=None,section='',config=None,episode=False):
 model=build_panel(options,episode)
 if not model['quick'] and not model['groups']:return None
 dialog=ActionPanel('ActionPanel.xml',str(ROOT),'Default','1080i')
 dialog.item=item;dialog.section=section;dialog.model=model;dialog.pack=selected_pack(config or {});dialog.result=None
 dialog.opened_at=time.monotonic();dialog.doModal();result=dialog.result;del dialog;return result
