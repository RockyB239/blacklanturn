"""Small Kodi ListItem/vector boundary for real controller refresh tests."""
import ast
from pathlib import Path
from types import SimpleNamespace
from live_core import watch_state,card_artwork,episode_heading
from episode_ui import episode_card
from youtube_core import is_youtube,caption as youtube_caption
from watch_metadata import hydrate_watch_metadata

class NativeItem:
 def __init__(self,label='',path=''):
  self.label=label;self.path=path;self.properties={};self.info={};self.resume=(0.,0.)
 def getPath(self):return self.path
 def setProperty(self,key,value):self.properties[key]=value
 def setArt(self,art):self.art=art
 def setInfo(self,kind,info):self.info.update(info)
 def getVideoInfoTag(self):return self
 def setResumePoint(self,position,total):self.resume=(position,total)

def media_functions():
 ns=dict(is_youtube=is_youtube,youtube_caption=youtube_caption,hydrate_watch_metadata=hydrate_watch_metadata,xbmcgui=SimpleNamespace(ListItem=NativeItem),watch_state=watch_state,card_artwork=card_artwork,episode_heading=episode_heading,episode_card=episode_card)
 tree=ast.parse((Path(__file__).parents[1]/'addon/live_review.py').read_text())
 nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('media_item','hydrate_watch_metadata')]
 exec(compile(ast.Module(body=nodes,type_ignores=[]),'actual-media-items','exec'),ns)
 return ns

def native_cards(state,controls):
 ns=media_functions()
 state.apply_row.__func__.__globals__['media_item']=ns['media_item']
 # The controller cache methods are separately compiled by the shared fixture.
 if 'hydrate_watch_metadata' in ns:state.apply_refreshed_row.__func__.__globals__['hydrate_watch_metadata']=ns['hydrate_watch_metadata']
 for control in controls.values():control.getListItem=lambda position,c=control:c.items[position]
