"""Bounded, lossless per-provider-page discovery ordering for public discovery rows.

No network, disk, settings, account or Kodi calls. Returns existing item objects
so artwork and watched/resume metadata remain provider-owned. A soft diversity
objective never deletes a valid title just because it appeared elsewhere.
"""
from collections import OrderedDict,Counter
from urllib.parse import parse_qs,urlsplit,urlencode
import math,re,threading

def identity(item):
    q=parse_qs(urlsplit(item.get('file','')).query);u=item.get('uniqueid') or {}
    kind=q.get('tmdb_type',q.get('type',['movie']))[0]
    ident=q.get('tmdb_id',[u.get('tvshow.tmdb') or u.get('tmdb') or ''])[0]
    return kind+':'+str(ident) if str(ident).isdigit() else ''

def votes(item):
    try:
        v=float(str(item.get('votes','')).replace(',','').strip())
        return v if math.isfinite(v) and v>=0 else None
    except (ValueError,TypeError):return None

def hard_eligible(item,policy):
    """Pure eligibility shared by page readiness and final row ordering."""
    ident=identity(item)
    if not ident:return True
    if ident in (policy.get('exclude_ids') or []):return False
    ceiling=policy.get('max_votes')
    number=votes(item) if ceiling is not None else None
    return ceiling is None or (number is not None and number<=ceiling)

def franchise(item):
    value=item.get('set')
    if value:return str(value).casefold()
    title=(item.get('title') or item.get('label') or '').casefold()
    groups=[('star trek',r'\bstar trek\b'),('star wars',r'\bstar wars\b|\bthe mandalorian\b|\bandor\b|\bahsoka\b'),('walking dead',r'\bthe walking dead\b'),('pirates of the caribbean',r'\bpirates of the caribbean\b'),('conjuring',r'\bthe conjuring\b|\bannabelle\b'),('harry potter',r'\bharry potter\b|\bfantastic beasts\b'),('lord of the rings',r'\bthe lord of the rings\b|\bthe hobbit\b'),('doctor who',r'^doctor who\b|^torchwood\b'),('dragon ball',r'\bdragon ball\b')]
    return next((name for name,pattern in groups if re.search(pattern,title)),'')

class Selector:
    def __init__(self,max_entries=256):
        self.max_entries=max_entries;self.orders=OrderedDict();self.exposed=OrderedDict();self.lock=threading.RLock();self.last={}
    def clear(self):
        with self.lock:self.orders.clear();self.exposed.clear()
    def preview(self,namespace,row,page,files,policy):
        # A pool probe must not freeze its insufficient first page or claim
        # titles have been displayed. Only apply_row commits visible exposure.
        with self.lock:
            probe=Selector(self.max_entries)
            probe.orders=OrderedDict(self.orders);probe.exposed=OrderedDict(self.exposed)
        return probe.choose(namespace,row,page,files,policy),dict(probe.last)
    def choose(self,namespace,row,page,files,policy):
        if not policy.get('enabled'):return list(files)
        key=(namespace,row,page)
        with self.lock:
            controls=[];titles=[]
            for item in files:
                ident=identity(item)
                if not ident:controls.append(item);continue
                if not hard_eligible(item,policy):continue
                titles.append(item)
            byid={identity(x):x for x in titles}
            seen=set().union(*(v for k,v in self.exposed.items() if k[0]==namespace and k!=key)) if self.exposed else set()
            previous=self.orders.get(key)
            if previous is not None:
                chosen=[byid[i] for i in previous if i in byid]
                chosen_ids={identity(x) for x in chosen};chosen.extend(x for x in titles if identity(x) not in chosen_ids)
            else:
                # Fresh titles lead. Allow two shared titles and two from each
                # known franchise in the first screen, then retain deferred items.
                pending=sorted(enumerate(titles),key=lambda pair:(identity(pair[1]) in seen,pair[0]))
                head=[];tail=[];families=Counter();repeats=0
                for _,item in pending:
                    ident=identity(item);family=franchise(item);repeat=ident in seen
                    if len(head)<12 and (not repeat or repeats<2) and (not family or families[family]<2):
                        head.append(item);repeats+=repeat
                        if family:families[family]+=1
                    else:tail.append(item)
                # A short candidate pool is reported, not filled with unrelated
                # data or made inaccessible. Provider continuation stays intact.
                if len(head)<12:
                    count=min(12-len(head),len(tail));head.extend(tail[:count]);tail=tail[count:]
                chosen=head+tail
            self.orders[key]=tuple(identity(x) for x in chosen);self.orders.move_to_end(key)
            self.exposed[key]={identity(x) for x in chosen[:12]};self.exposed.move_to_end(key)
            while len(self.orders)>self.max_entries:self.orders.popitem(last=False)
            while len(self.exposed)>self.max_entries:self.exposed.popitem(last=False)
            self.last={'namespace':namespace,'row':row,'count':len(chosen),'head_repeats':sum(identity(x) in seen for x in chosen[:12]),'eligible_count':len(titles),'filtered_count':len(files)-len(controls)-len(titles)}
            return chosen+controls

def _canonical(path):
    u=urlsplit(path)
    return u._replace(query=urlencode(sorted((k,v[0]) for k,v in parse_qs(u.query).items() if k not in ('page','bl_start','plugin_category','cacheonly','update_listing','reload')))).geturl()

def order_discovery_row(window,slot,files):
    """Order only opted-in public pools already fetched by the normal worker.

    No provider, settings or persistent-history access. Native paging and focus
    remain with the caller. Account/config scope comes from its existing cache.
    """
    if (getattr(window,'section','') not in ('Movies','Shows') or getattr(window,'mode','')!='home'
            or any(getattr(window,k,None) is not None for k in ('search_state','episode_browser_context','person_context'))
            or getattr(window,'discovery_stack',[])):
        return files
    snapshot=getattr(window,'snapshot_cache',None)
    scope=getattr(snapshot,'scope',None)
    if not scope:return files
    definitions=getattr(window,'page_definitions',[]);index=getattr(window,'row_offset',0)+slot
    if not 0<=index<len(definitions):return files
    definition=definitions[index];policy=definition.get('discovery_order') or {}
    if not isinstance(policy,dict) or policy.get('enabled') is not True:return files
    path=window.paths[slot];u=urlsplit(path);q=parse_qs(u.query)
    public=('discover','popular','top_rated','trending_week','trending_day','now_playing','upcoming','airing_today','on_the_air','trakt_popular','trakt_trending')
    if (u.scheme,u.netloc,u.path)!=('plugin','plugin.video.themoviedb.helper','/') or q.get('info',[''])[0] not in public:return files
    if _canonical(path)!=_canonical(definition.get('path','')):return files
    selector=getattr(window,'discovery_order_selector',None)
    if selector is None or getattr(window,'discovery_order_scope',None)!=scope:
        selector=Selector();window.discovery_order_selector=selector;window.discovery_order_scope=scope
    # Changing an individual recipe cannot reuse its previous frozen order.
    import json
    row=json.dumps([index,definition.get('label',''),definition.get('path',''),policy],sort_keys=True,separators=(',',':'))
    namespace=window.section+':'+str(getattr(window,'active_page',None) or 'All')
    return selector.choose(namespace,row,path,files,policy)
