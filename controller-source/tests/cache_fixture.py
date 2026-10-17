"""Bind the real new controller methods into partial native-API test fixtures."""
import ast,json,time,threading
from pathlib import Path
from types import MethodType
from urllib.parse import parse_qs,urlsplit
from row_feedback import RowResultCache
from watch_metadata import hydrate_watch_metadata
from playback_core import restored_position,item_key
from public_rows import PublicRowSnapshots,snapshot_scope,public_path
from filtered_pages import provider_path,upstream_path,logical_files,needs_fill,fill_page,PageCancelled
from browse_controls import should_exclude_anime
from search_ui import load_best_matches
NAMES=('step_search_rows','request_row_loads','restart_pending_rows','cached_row_items','cached_provider_list','retained_row_items','fill_discovery_page','configure_row_snapshots','apply_refreshed_row','publish_cache_stats','invalidate_row_results')
def bind(state,namespace):
    if not hasattr(state,"preview_dispatch_lock"):state.preview_dispatch_lock=threading.RLock()
    ns=dict(namespace,hydrate_watch_metadata=hydrate_watch_metadata,item_key=item_key,restored_position=restored_position,public_path=public_path,TMDB='plugin://plugin.video.themoviedb.helper/',parse_qs=parse_qs,urlsplit=urlsplit,provider_path=provider_path,upstream_path=upstream_path,logical_files=logical_files,needs_fill=needs_fill,fill_page=fill_page,PageCancelled=PageCancelled,should_exclude_anime=should_exclude_anime)
    tree=ast.parse((Path(__file__).parents[1]/'addon/live_review.py').read_text())
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='LiveReview')
    nodes=[n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name in NAMES]
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'actual-cache-methods','exec'),ns)
    if 'xbmc' not in namespace:namespace['xbmc']=__import__('types').SimpleNamespace()
    if not hasattr(namespace['xbmc'],'getInfoLabel'):namespace['xbmc'].getInfoLabel=lambda _:str(state.getFocusId()) if hasattr(state,'getFocusId') else ''
    ns['xbmc']=namespace['xbmc']
    ns['gui_labels']=lambda labels:{label:namespace['xbmc'].getInfoLabel(label) for label in labels}
    ns['load_best_matches']=load_best_matches
    if not hasattr(state,'result_cache'):state.result_cache=RowResultCache()
    for name in NAMES:setattr(state,name,MethodType(ns[name],state))
    if 'PROFILE' not in namespace:state.configure_row_snapshots=lambda:False
def with_cache(fn,namespace):
    def invoke(state,*args,**kwargs):
        bind(state,namespace)
        namespace.update(restored_position=restored_position,TMDB='plugin://plugin.video.themoviedb.helper/',provider_path=provider_path,upstream_path=upstream_path,should_exclude_anime=should_exclude_anime,needs_fill=needs_fill)
        return fn(state,*args,**kwargs)
    return invoke
