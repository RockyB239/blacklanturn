"""Bind display snapshots to the current account and existing progressive refresh."""
from pathlib import Path
from hashlib import sha256
import copy,json,re,time,threading
from contextlib import contextmanager
from youtube_core import tab_rows,connected_account
from youtube_home import split_page
from youtube_saved import SavedRows,current_watch,HistoryUnavailable,FRESH_AGE
from youtube_provider import refresh_watch_items as provider_watch

SCOPE_KEYS=('youtube.language','youtube.region','kodion.content.max_per_page','kodion.safe.search','kodion.history.local',
 'youtube.view.hide_videos','youtube.view.filter.list','youtube.view.shorts.duration','youtube.folder.my_subscriptions.sources',
 'youtube.folder.my_subscriptions_filtered.show','youtube.filter.my_subscriptions_filtered.blacklist','youtube.filter.my_subscriptions_filtered.list')
def saved_scope(identity,addon):
 values=[addon.getAddonInfo('version')]+[addon.getSetting(k) for k in SCOPE_KEYS]
 return sha256(json.dumps([identity,values],separators=(',',':')).encode()).hexdigest()

class SavedYouTube:
 def invalidate_saved_youtube_settings(self):
  self.youtube_settings_epoch=object()
 @contextmanager
 def youtube_saved_request(self):
  local=getattr(self,'youtube_request_local',None)
  if local is None:local=self.youtube_request_local=threading.local()
  previous=getattr(local,'settings',None);local.settings={}
  try:yield
  finally:local.settings=previous
 def request_saved_settings(self,identity,addon):
  frame=getattr(getattr(self,'youtube_request_local',None),'settings',None)
  key=(identity,getattr(self,'youtube_settings_epoch',None))
  if frame is not None and key in frame:return frame[key]
  value=(saved_scope(identity,addon),addon.getSettingBool('kodion.history.local'))
  if frame is not None:frame[key]=value
  return value
 def saved_youtube_context(self):
  import xbmcaddon,xbmcvfs
  from youtube_browser import read_account_store
  try:
   account=read_account_store();connected,identity=connected_account(account)
   active=getattr(self,'youtube_connection',None)
   if not connected or not getattr(active,'connected',False) or active.identity!=identity:return None
   manager=account['access_manager'];user=manager['users'][str(manager['current_user'])];uid=user.get('id','')
   if not isinstance(uid,str) or not re.fullmatch(r'[a-fA-F0-9]{32}',uid):return None
   addon=xbmcaddon.Addon('plugin.video.youtube')
   scope,local_history=self.request_saved_settings(identity,addon)
   store=getattr(self,'youtube_saved_store',None)
   if store is None or store.scope!=scope:
    root=Path(xbmcvfs.translatePath(xbmcaddon.Addon('script.blacklanturn.preview').getAddonInfo('profile')))
    store=self.youtube_saved_store=SavedRows(root/'youtube-display-rows.json',scope)
   history=Path(xbmcvfs.translatePath(addon.getAddonInfo('profile')))/uid/'history.sqlite'
   return store,history,local_history
  except (OSError,ValueError,TypeError,KeyError,RuntimeError):return None

 def saved_youtube_home(self):
  self.youtube_saved_active=False;self.youtube_saved_due=float('inf')
  context=self.saved_youtube_context()
  if context is None:return tab_rows('home')
  store,_,_=context;rows=store.get()
  if not rows:return tab_rows('home')
  primary=tab_rows('home');by_path={r['path']:r for r in rows};paths={r['path'] for r in primary}
  self.youtube_saved_active=True
  complete=paths.issubset(by_path) and any(r.get('youtube_category') for r in rows)
  age=max(time.time()-r['fetched_at'] for r in rows)
  self.youtube_saved_due=time.monotonic()+max(0,FRESH_AGE-age) if complete else 0
  return [by_path.get(r['path'],r) for r in primary]+[r for r in rows if r['path'] not in paths]

 def resolve_saved_youtube_row(self,definition,current):
  if not current():return None
  context=self.saved_youtube_context()
  if context is None or definition.get('_youtube_saved_scope')!=context[0].scope or not current():return None
  try:files=current_watch(definition.get('local_items',[]),context[1],context[2])
  except HistoryUnavailable:
   # Ask the native provider for current history on these exact IDs. Never
   # replace a category with the general feed or bind it to a different cursor.
   files=provider_watch(definition.get('local_items',[]),current)
  latest=self.saved_youtube_context()
  if not current() or latest is None or latest[0].scope!=context[0].scope:return None
  return files

 def youtube_saved_guard(self,current):
  origin=self.saved_youtube_context()
  if origin is None:return current
  scope=origin[0].scope
  def owned():
   if not current():return False
   latest=self.saved_youtube_context()
   return latest is not None and latest[0].scope==scope and current()
  return owned

 def remember_fetched_youtube_row(self,definition,files,current):
  if definition.get('_youtube_saved') or not files or not current():return
  context=self.saved_youtube_context()
  if context is None or not current():return
  items,cursor=split_page(files,definition['path'])
  context[0].put(dict(definition,local_items=items,youtube_cursor=cursor),current=current)

 def remember_youtube_shelves(self,rows,current=lambda:True):
  if not current():return
  context=self.saved_youtube_context()
  if context is not None and rows and current():context[0].put_many(rows[1:],replace_categories=True,current=current)

 def maybe_refresh_saved_youtube(self):
  if (not getattr(self,'youtube_saved_active',False) or time.monotonic()<getattr(self,'youtube_saved_due',float('inf'))
      or not self.youtube_home_visible() or getattr(self,'row_window_busy',False) or getattr(self,'youtube_refreshing',False)
      or getattr(self,'youtube_job',None) or getattr(self,'actions_open',False) or getattr(self,'settings_open',False)):return
  self.youtube_saved_due=float('inf')
  self.refresh_youtube_recommendations()
