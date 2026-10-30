"""Remote-first BlackLanturn settings hub; actions are handled by its owner."""
import xbmcgui
from backend_core import SETTINGS_GROUPS
class BackendSettings(xbmcgui.WindowXMLDialog):
 def onInit(self):
  self.result=None;self.loaded_category=-1
  self.getControl(100).addItems([xbmcgui.ListItem(label=g[0]) for g in SETTINGS_GROUPS])
  initial_row=self.row
  self.getControl(100).selectItem(self.category);self.populate(self.category)
  self.getControl(200).selectItem(initial_row);self.row=initial_row;self.setFocusId(getattr(self,'initial_focus',100))
 def populate(self,index):
  if self.loaded_category==index:return
  self.loaded_category=index;self.category=index
  title,description,rows=SETTINGS_GROUPS[index]
  self.setProperty('section',title);self.setProperty('sectionHelp',description)
  control=self.getControl(200);control.reset()
  items=[]
  for action,title,help in rows:
   if action=='series_end_suggestions':help='Next-series suggestions: '+('On' if self.config.get('SeriesEndSuggestions',True) else 'Off')+'  ·  Different shows never autoplay'
   elif action=='youtube_previews':help='Current mode: '+('Automatic' if self.config.get('YouTubePreviews',True) else 'Manual')
   if action=='youtube_end_suggestions':help='Next-video suggestions: '+('On' if self.config.get('YouTubeEndSuggestions',True) else 'Off')
   elif action=='youtube_end_autoplay':help='Next-video autoplay: '+('On' if self.config.get('YouTubeEndAutoplay',False) else 'Off')+'  ·  Requires suggestions to be enabled'
   elif action=='preview_mode':help='Current mode: '+('Automatic' if self.config.get('PreviewMode',self.preview_mode)=='auto' else 'Manual')
   elif action=='preview_delay':help='Current delay: '+str(self.config.get('PreviewDelay',5))+' seconds'
   elif action=='preview_language':help='Current preference: '+('English first, other languages as fallback' if self.config.get('PreviewLanguage','en')=='en' else 'Provider order')
   elif action=='icon_pack':
    from icon_packs import pack_label
    help='Current style: '+pack_label(self.config)+'  ·  Keeps your sidebar choices and order'
   elif action=='title_logos':help='Title logos: '+('On' if self.config.get('TitleLogos',True) else 'Off')+'  ·  Plain titles remain the fallback'
   elif action=='status_display':
    from navigation_core import status_settings
    values=status_settings(self.config);help='  ·  '.join(k.title()+': '+('On' if v else 'Off') for k,v in values.items())
   items.append(xbmcgui.ListItem(label=title,label2=help))
  control.addItems(items);self.row=0
 def onFocus(self,cid):
  if cid in (100,200):self.populate(self.getControl(100).getSelectedPosition())
 def onClick(self,cid):
  if cid==100:self.populate(self.getControl(100).getSelectedPosition());self.setFocusId(200)
  elif cid==200:
   category=self.getControl(100).getSelectedPosition()
   if category!=self.category:self.populate(category)
   self.row=self.getControl(200).getSelectedPosition()
   action=SETTINGS_GROUPS[self.category][2][self.row][0]
   if action.startswith('kodi:') or action in ('sidebar','status_display','icon_pack'):
    self.result=action;self.close();return
   self.handler(action)
   row=self.row;self.loaded_category=-1;self.populate(self.category)
   self.getControl(200).selectItem(row);self.row=row;self.setFocusId(200)
 def onAction(self,action):
  if action.getId() in (9,10,92):self.close()
  elif self.getFocusId()==100:self.populate(self.getControl(100).getSelectedPosition())

class LoadingPreview(xbmcgui.WindowXMLDialog):
 def onClick(self,cid):
  if cid==900:self.close()
 def onAction(self,action):
  if action.getId() in (9,10,92):self.close()
