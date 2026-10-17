"""Public TMDbHelper search routes and deterministic cross-category matching."""
from urllib.parse import urlencode,urlsplit,parse_qs,unquote
import re,unicodedata
SEARCH_KINDS=(('all','All'),('movie','Movies'),('tv','Shows'),('person','People'),('company','Studios'),('collection','Collections'))

def route(info,kind,**params):
    return 'plugin://plugin.video.themoviedb.helper/?'+urlencode(dict(info=info,tmdb_type=kind,nextpage='true',widget='true',**params))

def search_sources(query):
    query=str(query).strip()
    if not query:return []
    sources=[{'kind':kind,'label':label,'path':route('search',kind,query=query)} for kind,label in SEARCH_KINDS if kind!='all']
    best={'label':'Best matches','path':route('blacklanturn_search_matches','both',query=query)}
    return [{'kind':'all','label':'All','rows':[best]+sources}]+sources

def _name(value):
    text=unicodedata.normalize('NFKD',str(value or '')).casefold()
    return ' '.join(re.findall(r'[^\W_]+',''.join(c for c in text if not unicodedata.combining(c))))

def entity_kind(item):
    q=parse_qs(urlsplit(item.get('file','')).query)
    if 'page' in q and q.get('info')==['search']:return None
    if q.get('info')==['discover'] and q.get('with_companies',[''])[0].isdigit():return 'company'
    kind=q.get('tmdb_type',[''])[0]
    return kind if kind in ('movie','tv','person','collection') and q.get('tmdb_id',[''])[0].isdigit() else None

def best_matches(query,files,limit=40):
    needle=_name(query);unique={}
    for item in files:
        if entity_kind(item) and item.get('file') not in unique:unique[item['file']]=item
    def rank(pair):
        index,item=pair;name=_name(item.get('title') or item.get('label'))
        collection=entity_kind(item)=='collection' and name.endswith(' collection')
        base=name[:-11] if collection else name
        match=0 if needle in (name,base) else 1 if name.startswith(needle+' ') else 2
        art=item.get('art') or {}
        useful_art=any(isinstance(v,str) and (v.startswith('http') or unquote(v).startswith('image://http')) for v in art.values())
        quality=int(bool(item.get('plot')))+int(bool(item.get('year')))+int(useful_art)
        try:votes=max(0,int(str(item.get('votes') or 0).replace(',','')))
        except (ValueError,TypeError):votes=0
        return match,-votes,-quality,index
    return [item for _,item in sorted(enumerate(unique.values()),key=rank)][:limit]

def load_best_matches(query,provider,should_continue=lambda:True,workers=1):
    def fetch(kinds):
        files=[];failed=False
        for kind in kinds:
            if not should_continue():raise ValueError('Search cancelled')
            try:files.extend(provider(route('search',kind,query=query)))
            except Exception:failed=True
        return files,failed
    if workers==2:
        # One title lookup overlaps one sequential studio/collection lane.
        # Workers never touch controls, and results retain their original order.
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=1) as pool:
            side=pool.submit(fetch,('company','collection'))
            files,failed=fetch(('both',))
            extra,side_failed=side.result()
        files.extend(extra);failed=failed or side_failed
    else:files,failed=fetch(('both','company','collection'))
    if not should_continue():raise ValueError('Search cancelled')
    matches=best_matches(query,files)
    if not matches and failed:raise ValueError('Search could not return results')
    return matches

def search_caption(item):
    kind=entity_kind(item);labels={'movie':'Movie','tv':'Show','person':'Person','company':'Studio','collection':'Collection'}
    parts=[labels.get(kind,'')]
    if kind=='company':
        countries=item.get('country') or []
        if isinstance(countries,str):countries=[countries]
        parts.extend(x for x in countries if isinstance(x,str))
    elif kind in ('movie','tv','collection') and item.get('year'):parts.append(str(item['year']))
    return ' · '.join(x for x in parts if x)

def clear_search_selection(state):
    state.selected=None
    for key in ('title','titleLogo','plot','hero','episodeLine','episodeMeta','meta','technicalMeta','watchMeta','watchState'):
        state.setProperty(key,'')
    for key in ('hasSelection','allEpisodes','browsable'):state.setProperty(key,'false')
    for n in range(5):
        state.setProperty('ratingValue'+str(n),'');state.setProperty('ratingIcon'+str(n),'')

def discovery_result(item,crew=False):
    if item.get('_page_control'):return None
    source=urlsplit(item.get('file',''));params=parse_qs(source.query)
    kind=params.get('tmdb_type',[''])[0];identity=params.get('tmdb_id',[''])[0];info=params.get('info',[''])[0]
    if source.netloc!='plugin.video.themoviedb.helper':return None
    name=item.get('title') or item.get('label') or 'Discovery'
    company=params.get('with_companies',[''])[0]
    if info=='discover' and company.isdigit():
        return {'heading':name+' / STUDIO','button':'View titles','rows':[{'label':label+' · '+name,'path':route('discover',media,with_companies=company,with_id='True',sort_by='popularity.desc')} for media,label in [('movie','Movies'),('tv','Shows')]]}
    if not identity.isdigit():return None
    if info not in ('details','collection','credits','credits_in_both','stars_in_movies','stars_in_tvshows','crew_in_movies','crew_in_tvshows'):return None
    if kind=='person':
        prefix='crew_in_' if crew else 'stars_in_'
        return {'hide_captions':True,'heading':name+' / '+('CREW CREDITS' if crew else 'FILMOGRAPHY'),'button':'Open credits' if crew else 'Filmography',
                'rows':[{'label':label+' · '+name,'path':route(prefix+suffix,'person',tmdb_id=identity)} for suffix,label in [('movies','Movies'),('tvshows','Shows')]]}
    if kind=='collection' and info in ('collection','details'):
        return {'heading':name+' / COLLECTION','button':'View titles','rows':[{'label':name,'path':item['file'] if info=='collection' else route('collection','collection',tmdb_id=identity)}]}
    return None
