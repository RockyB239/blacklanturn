"""Remote-first BlackLanturn settings hub; actions are handled by its owner."""
import xbmcgui
from pathlib import Path
from backend_core import SETTINGS_GROUPS
from icon_packs import icon_path,selected_pack

ROOT=Path(__file__).resolve().parent
MENU_ICONS={
 'Kodi settings':'settings','Playback & sync':'continue-watching','Appearance':'pictures',
 'Skin & discovery':'genres','Recommendations':'trending','Previews':'youtube','Help':'guide',
 'kodi:settings':'settings','kodi:PlayerSettings':'continue-watching','kodi:SystemSettings':'tools',
 'kodi:InterfaceSettings':'pictures','kodi:addonbrowser':'addons','kodi:ServiceSettings':'services',
 'kodi:MediaSettings':'collections','kodi:filemanager':'files','kodi:Profiles':'my-stuff',
 'kodi:SkinSettings':'settings','kodi:PVRSettings':'live-tv','kodi:GameSettings':'games',
 'kodi:systeminfo':'tools','kodi:eventlog':'notifications',
 'addon:plugin.video.umbrella':'video-addons','addon:plugin.video.youtube':'youtube',
 'addon:plugin.video.themoviedb.helper':'movies','sync_settings':'continue-watching',
 'integration_status':'services','icon_pack':'pictures','title_logos':'movies',
 'ratings':'top-rated','rating_order':'top-rated','status_display':'weather',
 'collections':'collections','saved_searches':'search','rows':'playlist','sidebar':'home',
 'genres':'genres','categories':'collections','row_sources':'video-addons',
 'series_end_suggestions':'tv','hidden_titles':'bookmark','reduced_titles':'bookmark',
 'preview_mode':'movies','preview_delay':'history','preview_language':'international',
 'youtube_previews':'youtube','youtube_end_suggestions':'youtube','youtube_end_autoplay':'youtube',
 'help':'guide','update_notes':'updates','startup_preview':'builds','clear_search':'search','recovery':'restore'}

def menu_item(label,config,key,description=''):
 item=xbmcgui.ListItem(label=label,label2=description)
 artwork=icon_path(ROOT,MENU_ICONS.get(key,'settings'),selected_pack(config))
 item.setArt({'icon':artwork,'thumb':artwork})
 return item

class BackendSettings(xbmcgui.WindowXMLDialog):
 def onInit(self):
  self.result=None;self.loaded_category=-1
  self.getControl(100).addItems([menu_item(g[0],self.config,g[0]) for g in SETTINGS_GROUPS])
  initial_row=self.row
  self.getControl(100).selectItem(self.category);self.populate(self.category)
  self.getControl(200).selectItem(initial_row);self.row=initial_row;self.setFocusId(getattr(self,'initial_focus',100))
 def populate(self,index):
  if self.loaded_category==index:return
  self.loaded_category=index;self.category=index
  title,description,rows=SETTINGS_GROUPS[index]
  self.setProperty('section',title);self.setProperty('sectionHelp',description)
  self.setProperty('sectionIcon',icon_path(ROOT,MENU_ICONS.get(title,'settings'),selected_pack(self.config)))
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
    help='Current style: '+pack_label(self.config)+'  ·  Applies to menus, genres and YouTube category artwork'
   elif action=='title_logos':help='Title logos: '+('On' if self.config.get('TitleLogos',True) else 'Off')+'  ·  Plain titles remain the fallback'
   elif action=='status_display':
    from navigation_core import status_settings
    values=status_settings(self.config);help='  ·  '.join(k.title()+': '+('On' if v else 'Off') for k,v in values.items())
   items.append(menu_item(title,self.config,action,help))
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
