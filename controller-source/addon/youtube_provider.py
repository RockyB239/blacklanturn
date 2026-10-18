"""Read-only adapter to the installed YouTube add-on's existing account client.

This is its regular YouTube video Home for TV clients, not YouTube TV and not
YouTube.com's browser feed. Browser Home requires separate cookie authentication.
"""
import sys,threading,atexit,time
from contextlib import contextmanager
from types import SimpleNamespace
from pathlib import Path
from youtube_core import video_id
from youtube_home import parse_shelves,parse_horizontal,section_continuation,local_rows,merge_shelves,MAX_GROUPS
from youtube_artwork import cached_fit_cards

_lock=threading.RLock()
_runtime=None
_STORES=('_bookmarks_list','_data_cache','_feed_history','_function_cache','_playback_history','_requests_cache','_search_history','_watch_later_list')

def _identity():
    from youtube_browser import read_account_store
    from youtube_core import connected_account
    connected,identity=connected_account(read_account_store())
    if not connected:raise RuntimeError('YouTube account unavailable')
    return identity

def _create_runtime(identity):
    import xbmcaddon,xbmcvfs
    root=str(Path(xbmcvfs.translatePath(xbmcaddon.Addon('plugin.video.youtube').getAddonInfo('path')))/'resources/lib')
    if root not in sys.path:sys.path.insert(0,root)
    from youtube_plugin.kodion.context.xbmc.xbmc_context import XbmcContext
    from youtube_plugin.youtube.provider import Provider
    context=XbmcContext(path='/special/recommendations',params={});provider=Provider()
    return SimpleNamespace(identity=identity,context=context,provider=provider)

def _retire(runtime):
    for name in _STORES:
        store=getattr(runtime.context,name,None)
        if store is None:continue
        timer=getattr(store,'_close_timer',None)
        if timer:
            timer.cancel()
            if timer is not threading.current_thread() and timer.is_alive():timer.join(2)
            if timer.is_alive():raise RuntimeError('YouTube cache timer still active')
        if store._close(event='shutdown') is False or getattr(store,'_db',None) is not None:
            raise RuntimeError('YouTube cache still busy')
        atexit.unregister(store._close)
    # Context teardown mutates provider class settings. Keep those settings intact.
    atexit.unregister(runtime.context.tear_down)
    atexit.unregister(runtime.provider.tear_down);runtime.provider.tear_down()

@contextmanager
def _session(current):
    global _runtime
    with _lock:
        identity=_identity()
        if not current():raise RuntimeError('YouTube request retired')
        if _runtime is not None and _runtime.identity!=identity:
            _retire(_runtime);_runtime=None
        if _runtime is None:_runtime=_create_runtime(identity)
        _runtime.context.get_settings(refresh=True)
        try:yield _runtime
        finally:
            # Run before native cleanup callbacks registered lazily by this read.
            atexit.unregister(_shutdown);atexit.register(_shutdown)

def _shutdown():
    global _runtime
    with _lock:
        if _runtime is not None:
            try:_retire(_runtime)
            except Exception:return # Native callbacks remain registered on busy resources.
            _runtime=None
atexit.register(_shutdown)

def _resolve(runtime,unique,current):
    from youtube_plugin.youtube.helper.v3 import response_to_items
    context,provider=runtime.context,runtime.provider
    resolved=response_to_items(provider,context,{'kind':'youtube#videoListResponse','items':list(unique.values())},process_next_page=False,hide_progress=True) or []
    if not current():return []
    items=[]
    for item in resolved:
        path=item.get_uri();ident=video_id({'file':path})
        if not ident:continue
        duration=item.get_duration() or 0
        items.append({'file':path,'filetype':'file','title':item.get_name(),'label':item.get_name(),'plot':item.get_plot() or '',
                      'runtime':duration,'playcount':item.get_play_count() or 0,'resume':{'position':item.get_start_time() or 0,'total':duration},
                      'artist':item.get_artists() or [],'studio':item.get_studios() or [],'art':{'thumb':item.get_image(),'fanart':item.get_fanart() or ''}})
    return cached_fit_cards(items)

@contextmanager
def _content_refresh(runtime,refresh):
    # Native request caching honors this context flag. Never clear account,
    # history or shared databases, and never leave it set for later previews.
    params=runtime.context.get_params() if refresh else None
    missing=object();previous=params.get('refresh',missing) if params is not None else missing
    if params is not None:params['refresh']=1
    try:yield
    finally:
        if params is not None:
            if previous is missing:params.pop('refresh',None)
            else:params['refresh']=previous

def load_home_rows(current=lambda:True,refresh=False):
    if not current():return []
    with _session(current) as runtime:
        context,provider=runtime.context,runtime.provider;client=provider.get_client(context)
        with _content_refresh(runtime,refresh):return _load_home(runtime,client,current)

def _resolve_entries(runtime,entries,current):
    unique={x['id']:x for x in entries if x.get('kind')=='youtube#video'}
    resolved={}
    for start in range(0,len(unique),40):
        if not current():return []
        batch=dict(list(unique.items())[start:start+40])
        resolved.update({video_id(x):x for x in _resolve(runtime,batch,current)})
    return [x if x.get('filetype')=='directory' else resolved[x['id']] for x in entries if x.get('filetype')=='directory' or x['id'] in resolved]

def load_shelf_page(cursor,current=lambda:True):
    if not current():raise RuntimeError('YouTube request retired')
    with _session(current) as runtime:
        client=runtime.provider.get_client(runtime.context)
        raw=client.get_browse_items(browse_id='FEwhat_to_watch',client='tv',do_auth=True,json_path=None,
                                    page_token=cursor['continuation'],click_tracking=cursor.get('clickTrackingParams'),visitor=cursor.get('visitor'))
        if not current():raise RuntimeError('YouTube request retired')
        if not isinstance(raw,dict) or 'horizontalListContinuation' not in raw.get('continuationContents',{}):
            raise RuntimeError('YouTube shelf response unavailable')
        entries,more=parse_horizontal(raw,cursor.get('visitor'))
        return _resolve_entries(runtime,entries,current),more

def load_related_page(cursor,current=lambda:True):
    if not current():raise RuntimeError('YouTube request retired')
    seeds=cursor['related_seeds'];index=cursor.get('seed_index',0)
    if not 0<=index<len(seeds):raise ValueError('Invalid related shelf cursor')
    with _session(current) as runtime:
        client=runtime.provider.get_client(runtime.context)
        raw=client.get_related_videos(video_id=seeds[index],page_token=cursor.get('page_token'),
                                     click_tracking=cursor.get('click_tracking'),visitor=cursor.get('visitor'))
        if not current():raise RuntimeError('YouTube request retired')
        if raw=={}:raw={'items':[]} # Native fallback clients exhausted this seed.
        if not isinstance(raw,dict) or not isinstance(raw.get('items'),list):raise RuntimeError('Related videos unavailable')
        files=_resolve_entries(runtime,raw['items'][:100],current)
        token=raw.get('nextPageToken')
        if token and token!=cursor.get('page_token'):
            more=dict(cursor,page_token=token,click_tracking=raw.get('clickTracking'),visitor=raw.get('visitorData'))
        elif index+1<len(seeds):more={'related_seeds':list(seeds),'seed_index':index+1}
        else:more=None
        return files,more

def _load_home(runtime,client,current):
    # Main recommendations/subscriptions resolve independently. Broader interest
    # groups use this bounded background request and never gate those rows.
    raw=client.get_browse_items(browse_id='FEwhat_to_watch',client='tv',do_auth=True,json_path=None)
    if not current():return []
    shelves=merge_shelves([],parse_shelves(raw));seen=set();deadline=time.monotonic()+15
    for _ in range(5):
        more=section_continuation(raw);token=more.get('continuation')
        if not token or token in seen or len(shelves)>=MAX_GROUPS or time.monotonic()>=deadline:break
        if not current():return []
        seen.add(token)
        try:
            raw=client.get_browse_items(browse_id='FEwhat_to_watch',client='tv',do_auth=True,json_path=None,page_token=token,click_tracking=more.get('clickTrackingParams'),visitor=client.json_traverse(raw,('responseContext','visitorData')))
        except Exception:break # Keep earlier real groups on a later-page failure.
        if not current():return []
        shelves=merge_shelves(shelves,parse_shelves(raw))
    unique={x['id']:x for shelf in shelves for x in shelf['items'] if x.get('kind')=='youtube#video'}
    if not shelves:return []
    # The native converter's page size must not truncate the later shelves.
    items=[];entries=list(unique.items())
    for start in range(0,len(entries),40):
        if not current():return []
        items.extend(_resolve(runtime,dict(entries[start:start+40]),current))
    return local_rows(shelves,{video_id(x):x for x in items})

def refresh_watch_items(files,current=lambda:True):
    from copy import deepcopy
    unique={ident:{'kind':'youtube#video','id':ident,'_partial':True,'snippet':{'title':item.get('title') or item.get('label','')}}
            for item in files if (ident:=video_id(item))}
    if not unique:return deepcopy(files)
    with _session(current) as runtime:
        fresh={video_id(item):item for item in _resolve(runtime,unique,current)}
    result=deepcopy(files)
    for item in result:
        updated=fresh.get(video_id(item))
        if updated:
            item['playcount']=updated['playcount'];item['resume']=updated['resume']
    return result

class _PreviewSettings:
    def __init__(self,base):self.base=base
    def __getattr__(self,name):return getattr(self.base,name)
    def default_player_web_urls(self):return False
    def default_player_fallback(self):return False
    def mpd_video_qualities(self,value=None):return [q for q in self.base.mpd_video_qualities() if q['nom_height']<=720]
    def stream_features(self,value=None,raw_values=False):
        features=[x for x in self.base.stream_features(raw_values=True) if x not in ('vp9','av01')]
        if 'avc1' not in features:features.append('avc1')
        return features if raw_values else frozenset(features)
    def max_video_height(self):return min(720,self.base.max_video_height())
    def fixed_video_quality(self,value=None):return min(720,self.base.fixed_video_quality())

class _PreviewUI:
    def __init__(self,base,effects):self.base,self.effects=base,effects
    def __getattr__(self,name):return getattr(self.base,name)
    def set_property(self,*args,**kwargs):self.effects.append((self.base.set_property,args,kwargs))
    def clear_property(self,*args,**kwargs):self.effects.append((self.base.clear_property,args,kwargs))
    def pop_property(self,*args,**kwargs):return None # Never consume a full-video one-shot preference.
    def get_property(self,*args,**kwargs):return False if kwargs.get('as_bool') else self.base.get_property(*args,**kwargs)
    def show_notification(self,*args,**kwargs):pass # A decorative preview failure retains its artwork.

class _PreviewContext:
    def __init__(self,base,params):
        self.base,self.params,self.effects=base,params,[]
        self.ui=_PreviewUI(base.get_ui(),self.effects)
    def __getattr__(self,name):return getattr(self.base,name)
    def get_params(self):return self.params
    def get_param(self,name,default=None):return self.params.get(name,default)
    def get_path(self):return '/play'
    def get_ui(self):return self.ui
    def get_settings(self,**kwargs):return _PreviewSettings(self.base.get_settings(**kwargs))
    def send_notification(self,*args,**kwargs):self.effects.append((self.base.send_notification,args,kwargs))

class PreparedPreview:
    def __init__(self,item,effects,current):
        self.listitem,self.path,self.effects,self.current,self.published=item,item.getPath(),effects,current,False
    def publish(self):
        if self.published or not self.current():return False
        self.published=True
        for method,args,kwargs in self.effects:method(*args,**kwargs)
        return True

def _prepare_preview(runtime,context):
    from youtube_plugin.youtube.helper.yt_play import _play_stream
    from youtube_plugin.kodion.items import playback_item
    media=_play_stream(runtime.provider,context)
    if not media or isinstance(media,tuple):return None
    return playback_item(context,media)

def resolve_preview(path,current):
    """Resolve off Kodi's player queue; a retired request cannot open a video.

    Native stream conversion retains ISA/headers and incognito/end-time handling.
    Buffer its player notification until the controller owns the actual dispatch.
    No cloned native context, extra database runtime or sign-in flow is created.
    """
    import math
    from urllib.parse import urlsplit,parse_qs
    ident=video_id({'file':path})
    if not ident:raise ValueError('Unsupported preview source')
    values=parse_qs(urlsplit(path).query)
    def number(key):
        try:value=float(values.get(key,['0'])[0]);return value if math.isfinite(value) and value>=0 else 0.0
        except (TypeError,ValueError):return 0.0
    params={'video_id':ident,'incognito':True,'screensaver':True,'start':number('start'),'end':number('end')}
    if not current():return None
    with _session(current) as runtime:
        context=_PreviewContext(runtime.context,params)
        item=_prepare_preview(runtime,context)
        if not current() or item is None:return None
        if urlsplit(item.getPath()).scheme not in ('http','https'):raise ValueError('Preview did not resolve to a stream')
        return PreparedPreview(item,context.effects,current)
