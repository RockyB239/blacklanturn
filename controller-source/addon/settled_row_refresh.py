"""Defer only public display revalidation while the user moves between rows.

One replaceable pair, no thread/timer/provider. The existing monitor submits
settled work to the existing serial worker; missing rows remain immediate.
"""
import time,threading
from public_rows import public_path
SETTLE=.6
_init_lock=threading.Lock()

def schedule_lock(owner):
    lock=getattr(owner,'row_schedule_lock',None)
    if lock is None:
        with _init_lock:
            lock=getattr(owner,'row_schedule_lock',None)
            if lock is None:lock=threading.RLock();owner.row_schedule_lock=lock
    return lock

def defer_refreshes(owner,pending,focus_slot=None,now=None):
    owner.deferred_public_refresh=None
    if not getattr(owner,'defer_public_refresh',False) or getattr(owner,'section','') not in ('Movies','Shows') or getattr(owner,'mode','')!='home':return pending
    home=getattr(owner,'home_snapshot_cache',None);delayed=[];immediate=[]
    for n,definition in pending:
        path=definition.get('path','')
        eligible=(definition.get('_snapshot_refresh') and not definition.get('_settled_refresh')
                  and public_path(path) and not (home is not None and home.path_allowed(path)))
        (delayed if eligible else immediate).append((n,definition))
    if delayed:
        owner.deferred_public_refresh={'pending':delayed,'focus':focus_slot,'created':time.monotonic() if now is None else now,
            'generation':owner.generation,'revision':owner.result_cache.revision,'serial':owner.row_request_serial,
            'paths':tuple(owner.paths),'tokens':{n:getattr(owner,'path_tokens',{}).get(n,0) for n,_ in delayed},
            'lifetime':getattr(owner,'window_lifetime',None)}
    return immediate

def drain_refreshes(owner,now=None,dialog=lambda:0):
    saved=getattr(owner,'deferred_public_refresh',None)
    if saved is None:return False
    def current():return (getattr(owner,'alive',False) and owner.generation==saved['generation'] and owner.result_cache.revision==saved['revision']
             and owner.row_request_serial==saved['serial'] and tuple(owner.paths)==saved['paths']
             and getattr(owner,'window_lifetime',None) is saved['lifetime']
             and all(getattr(owner,'path_tokens',{}).get(n,0)==token for n,token in saved['tokens'].items())
             and getattr(owner,'section','') in ('Movies','Shows') and getattr(owner,'mode','')=='home')
    if not current():
        if getattr(owner,'deferred_public_refresh',None) is saved:owner.deferred_public_refresh=None
        return False
    now=time.monotonic() if now is None else now
    if now-saved['created']<SETTLE or now-getattr(owner,'dwell',now)<SETTLE:return False
    if (getattr(owner,'row_window_busy',False) or getattr(owner,'nav',False) or getattr(owner,'settings_open',False)
        or getattr(owner,'actions_open',False) or getattr(owner,'owned_preview',False) or not all(owner.window_ready)
        or owner.getProperty('loading')=='true' or owner.getFocusId() not in (900,901)
        or owner.player.isPlaying() or dialog() not in (0,9999)):return False
    # Native focus/dialog calls above can run user navigation callbacks. Claim
    # only the same saved request, atomically with foreground serial/queue work.
    with schedule_lock(owner):
        if getattr(owner,'deferred_public_refresh',None) is not saved:return False
        if not current():owner.deferred_public_refresh=None;return False
        if (getattr(owner,'row_window_busy',False) or getattr(owner,'nav',False) or getattr(owner,'settings_open',False)
            or getattr(owner,'actions_open',False) or now-getattr(owner,'dwell',now)<SETTLE):return False
        owner.deferred_public_refresh=None
        owner.request_row_loads([(n,dict(definition,_settled_refresh=True)) for n,definition in saved['pending']],saved['focus'])
        return True
