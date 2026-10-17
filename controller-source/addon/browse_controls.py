"""Row navigation and conservative, cached anime classification.

Only public genre/country metadata is read. No account tables, keys, writes or
per-title network requests are used. Missing metadata leaves a title available.
"""
from collections import OrderedDict
from pathlib import Path
from urllib.parse import parse_qs,urlsplit
import re,sqlite3,time,threading

def can_choose_genre(state):
    return (getattr(state,'section','') in ('Movies','Shows')
            and getattr(state,'mode','home')=='home' and not getattr(state,'nav',False)
            and getattr(state,'search_state',None) is None
            and getattr(state,'episode_browser_context',None) is None
            and not getattr(state,'discovery_stack',[]))

def should_exclude_anime(state,path):
    if getattr(state,'section','') not in ('Home','Movies','Shows'):return False
    if any(getattr(state,k,None) is not None for k in ('search_state','episode_browser_context','person_context')):return False
    if getattr(state,'discovery_stack',[]):return False
    query=parse_qs(urlsplit(path).query)
    info=query.get('info',[''])[0]
    if info in ('trakt_watchlist','trakt_ondeck','trakt_inprogress','trakt_nextepisodes','trakt_history','trakt_collection','trakt_favorites'):return False
    pages=[p for group in ('Genres','Categories') for p in getattr(state,'config',{}).get(group,[])]
    page=next((p for p in pages if p.get('id')==getattr(state,'active_page',None)),None)
    if page and (re.search(r'\b(?:animation|anime)\b',page.get('label',''),re.I)
                 or page.get('id') in ('bl-movies-animation','bl-shows-animation')):return False
    return True

def is_next_page(item,path):
    if item.get('filetype')!='directory':return False
    before,after=urlsplit(path),urlsplit(item.get('file',''))
    old,new=parse_qs(before.query),parse_qs(after.query)
    if (before.scheme,before.netloc,before.path)!=(after.scheme,after.netloc,after.path):return False
    try:
        if (int(new.get('page',['1'])[0]),int(new.get('bl_start',['0'])[0]))<=(int(old.get('page',['1'])[0]),int(old.get('bl_start',['0'])[0])):return False
    except (TypeError,ValueError):return False
    ignored={'page','bl_start','cacheonly','plugin_category','update_listing','reload'}
    return {k:v for k,v in old.items() if k not in ignored}=={k:v for k,v in new.items() if k not in ignored}

def page_card(direction,path):
    label='Previous' if direction=='previous' else 'Next'
    image=str(Path(__file__).resolve().parent/'resources/media'/('page-'+direction+'.png'))
    return {'label':label,'title':label,'plot':'Return to the previous titles in this row.' if direction=='previous' else 'Browse more titles in this row.',
            'file':path,'filetype':'directory','_page_control':direction,'art':{'navigation':image,'icon':image}}

def page_cards(files,history,path,position=0,display_position=False):
    files=list(files)
    original=files[position] if 0<=position<len(files) else None
    already_displayed=any(x.get('_page_control')=='previous' for x in files)
    ordinary=[];more=[]
    for item in files:
        if item.get('_page_control')=='previous':continue
        if is_next_page(item,path):
            more.append(page_card('next',item['file']))
        else:ordinary.append(item)
    result=ordinary+more
    if history.pages:
        result.insert(0,page_card('previous','blacklanturn://previous-page'))
    if display_position and not already_displayed:
        selected=max(0,min(position,len(result)-1))
    elif original:
        selected=next((n for n,x in enumerate(result) if x.get('file')==original.get('file')),0)
    else:selected=0
    return result,selected

def _identity(item):
    query=parse_qs(urlsplit(item.get('file','')).query)
    kind=query.get('tmdb_type',query.get('type',['']))[0]
    uid=item.get('uniqueid') or {}
    ident=query.get('tmdb_id',[uid.get('tvshow.tmdb') or uid.get('tmdb','')])[0]
    return kind+'.'+str(ident) if kind in ('movie','tv') and str(ident).isdigit() else None

def _classification(item,metadata):
    genres=item.get('genre') or []
    if isinstance(genres,str):genres=[genres]
    genres={str(x).casefold() for x in genres}
    if 'anime' in genres:return True
    cached_genres,cached_countries=metadata or (set(),set())
    animated='animation' in genres or 16 in (item.get('genre_ids') or []) or 16 in cached_genres
    countries=item.get('origin_country') or item.get('country') or []
    if isinstance(countries,str):countries=[countries]
    countries={x.strip().casefold() for x in list(countries)+list(cached_countries) if isinstance(x,str) and x.strip()}
    if not animated:return False if genres or cached_genres else None
    if not countries:return None
    return bool(countries & {'jp','japan','日本'})

class AnimeMetadata:
    def __init__(self,profile,clock=time.monotonic):
        self.profile=Path(profile);self.clock=clock;self.cache=OrderedDict();self.reads=0;self.lock=threading.RLock()
    def _metadata(self,identities):
        now=self.clock();missing=[key for key in identities if key not in self.cache or self.cache[key][0]<=now]
        found={}
        if missing:
            folders=sorted((p for p in self.profile.glob('database_*') if re.fullmatch(r'database_\d+',p.name)),key=lambda p:int(p.name.split('_')[-1]),reverse=True)
            for folder in folders:
                db=folder/'ItemDetails.db'
                if not db.is_file():continue
                try:
                    with sqlite3.connect(db.resolve().as_uri()+'?mode=ro',uri=True,timeout=.05) as c:
                        if not {'parent_id','tmdb_id'}<={x[1] for x in c.execute('PRAGMA table_info(genre)')}:continue
                        if not {'parent_id','iso_country'}<={x[1] for x in c.execute('PRAGMA table_info(country)')}:continue
                        self.reads+=1
                        marks=','.join('?' for _ in missing)
                        for parent,genre in c.execute('SELECT parent_id,tmdb_id FROM genre WHERE parent_id IN ('+marks+')',missing):
                            if isinstance(genre,int):found.setdefault(parent,(set(),set()))[0].add(genre)
                        for parent,country in c.execute('SELECT parent_id,iso_country FROM country WHERE parent_id IN ('+marks+')',missing):
                            if isinstance(country,str) and country.strip():found.setdefault(parent,(set(),set()))[1].add(country.strip())
                    break
                except (OSError,sqlite3.Error):continue
            for key in missing:
                value=found.get(key,(set(),set()))
                self.cache[key]=(now+(600 if all(value) else 15),value)
                self.cache.move_to_end(key)
            while len(self.cache)>1024:self.cache.popitem(last=False)
        return {key:self.cache[key][1] for key in identities if key in self.cache}
    def without_anime(self,files):
        files=list(files)
        identities=list(dict.fromkeys(key for key in (_identity(x) for x in files if _classification(x,None) is None) if key))
        with self.lock:metadata=self._metadata(identities)
        return [x for x in files if x.get('_page_control') or _classification(x,metadata.get(_identity(x))) is not True]
