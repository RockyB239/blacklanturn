"""Read-only adapter to the installed YouTube add-on's existing account client.

This is its regular YouTube video Home for TV clients, not YouTube TV and not
YouTube.com's browser feed. Browser Home requires separate cookie authentication.
"""
import sys,threading,atexit
from contextlib import contextmanager
from types import SimpleNamespace
from pathlib import Path
from youtube_core import video_id
from youtube_home import parse_shelves,section_continuation,local_rows
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

def load_home_rows(current=lambda:True):
    if not current():return []
    with _session(current) as runtime:
        context,provider=runtime.context,runtime.provider;client=provider.get_client(context)
        return _load_home(runtime,client,current)

def _load_home(runtime,client,current):
    raw=client.get_browse_items(browse_id='FEwhat_to_watch',client='tv',do_auth=True,json_path=None)
    if not current():return []
    shelves=parse_shelves(raw);more=section_continuation(raw)
    if more and len(shelves)<8:
        raw=client.get_browse_items(browse_id='FEwhat_to_watch',client='tv',do_auth=True,json_path=None,page_token=more['continuation'],click_tracking=more.get('clickTrackingParams'),visitor=client.json_traverse(raw,('responseContext','visitorData')))
        if not current():return []
        shelves+=parse_shelves(raw)
    # Keep YouTube's interest labels and order. Resolve metadata/watch state using
    # the same provider pipeline as its normal lists, without incognito flags.
    unique={x['id']:x for shelf in shelves[:8] for x in shelf['items']}
    if not unique:return []
    items=_resolve(runtime,unique,current)
    return local_rows(shelves[:8],{video_id(x):x for x in items})

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
