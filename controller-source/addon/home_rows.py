"""Private, account-scoped Home artwork; normal Trakt requests still refresh it."""
import json,time
from urllib.parse import urlsplit,parse_qs,urlencode
from public_rows import PublicRowSnapshots,_items,_item_path,snapshot_scope,_finite_number,public_path,PUBLIC_ITEMS

BASE='plugin://plugin.video.themoviedb.helper/'

def home_path(path,paging=False):
    if not isinstance(path,str):return False
    try:
        url=urlsplit(path);query=parse_qs(url.query,keep_blank_values=True)
        if (url.scheme,url.netloc,url.path)!=('plugin','plugin.video.themoviedb.helper','/') or url.fragment:return False
        if any(len(values)!=1 for values in query.values()):return False
        if query.get('info')!=['trakt_recommendations'] or query.get('tmdb_type') not in (['movie'],['tv']):return False
        allowed={'info','tmdb_type','nextpage','widget'}|({'page','cacheonly','reload'} if paging else set())
        if set(query)-allowed:return False
        for key in ('nextpage','widget','cacheonly'):
            if key in query and query[key][0] not in ('true','false'):return False
        if 'page' in query and (not query['page'][0].isdigit() or not 1<=int(query['page'][0])<=10000):return False
        safe=dict((key,values[0]) for key,values in query.items());safe['info']='popular'
        return public_path(BASE+'?'+urlencode(safe))
    except (TypeError,ValueError):return False

def home_item_path(path):
    public=_item_path(path)
    if public:return public
    try:
        url=urlsplit(path);query=parse_qs(url.query,keep_blank_values=True)
        if any(len(values)!=1 for values in query.values()) or 'page' not in query:return ''
        query.pop('plugin_category',None)
        if 'cacheonly' in query:query['cacheonly']=[query['cacheonly'][0].lower()]
        canonical=url._replace(query=urlencode({key:values[0] for key,values in query.items()})).geturl()
        return canonical if home_path(canonical,paging=True) else ''
    except (TypeError,ValueError,AttributeError):return ''

# Browse display reuse is deliberately separate from the two-row startup model.
_HOME_BROWSE_TYPES={
    'trakt_recommendations':('movie','tv'),
    'trakt_trending':('movie','tv'),
    'trakt_ondeck':('tv',),
    'trakt_inprogress':('movie',),
    'trakt_nextepisodes':('tv',),
    'trending_week':('movie','tv'),
}

def home_browse_path(path,paging=False):
    if not isinstance(path,str) or len(path)>512 or any(ord(char)<=32 or ord(char)==127 for char in path):return False
    try:
        url=urlsplit(path);query=parse_qs(url.query,keep_blank_values=True)
        if any(len(values)!=1 for values in query.values()):return False
        info=query.get('info',[''])[0];kind=query.get('tmdb_type',[''])[0]
        if kind not in _HOME_BROWSE_TYPES.get(info,()):return False
        if paging and 'bl_start' in query:
            cursor=query.pop('bl_start')[0]
            if not cursor.isascii() or not cursor.isdigit() or len(cursor)>5 or not 0<=int(cursor)<=10000:return False
            if 'page' not in query and int(cursor)==0:return False
        # Reuse the strict original URL/query/pagination rules, without widening
        # home_path itself: the saved startup model must still be recommendations.
        query['info']=['trakt_recommendations']
        canonical=url._replace(query=urlencode({key:values[0] for key,values in query.items()})).geturl()
        return home_path(canonical,paging=paging)
    except (TypeError,ValueError):return False

def home_browse_item_path(path):
    if not isinstance(path,str) or any(ord(char)<=32 or ord(char)==127 for char in path):return ''
    try:
        url=urlsplit(path);query=parse_qs(url.query,keep_blank_values=True)
        # Title actions retain the existing public-safe validation. List cards
        # may only navigate within the bounded Home allowlist and require a page.
        if query.get('info',[''])[0] in PUBLIC_ITEMS:return _item_path(path)
        if any(len(values)!=1 for values in query.values()) or not {'page','bl_start'} & query.keys():return ''
        query.pop('plugin_category',None)
        if 'cacheonly' in query:query['cacheonly']=[query['cacheonly'][0].lower()]
        canonical=url._replace(query=urlencode({key:values[0] for key,values in query.items()})).geturl()
        return canonical if home_browse_path(canonical,paging=True) else ''
    except (TypeError,ValueError):return ''

def _home_browse_items(files):
    items=_items(files,path_filter=home_browse_item_path,max_items=40)
    # Reserve 1 KiB for the strictly bounded row route, timestamp and JSON keys;
    # one oversized provider row must not consume the whole Home display budget.
    if items and len(json.dumps(items,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8'))>256*1024-1024:return None
    return items

def home_scope(config,identity,authorization,now=None):
    # Match the exact native authorization locally; never persist its raw value.
    try:
        token=json.loads(authorization)
        if not isinstance(token,dict) or not all(isinstance(token.get(k),str) and token[k] for k in ('access_token','refresh_token')):return None
        created=token.get('created_at');expires=token.get('expires_in')
        if not _finite_number(created) or not _finite_number(expires):return None
        now=time.time() if now is None else now
        if not created<=now<created+expires:return None
        return snapshot_scope(config,b'private-home-v1\0'+identity)
    except (TypeError,ValueError):return None

class HomeRowSnapshots(PublicRowSnapshots):
    max_bytes=1024*1024
    max_rows=12
    max_age=24*3600
    path_allowed=staticmethod(home_browse_path)
    sanitize_items=staticmethod(_home_browse_items)

    def get(self,path):
        files=super().get(path)
        if files is not None and parse_qs(urlsplit(path).query).get('info',[''])[0] in ('trakt_ondeck','trakt_inprogress','trakt_nextepisodes'):
            from home_progress import PENDING_SCOPE
            for item in files:
                if parse_qs(urlsplit(item['file']).query).get('info',[''])[0] in PUBLIC_ITEMS:item[PENDING_SCOPE]=self.scope
        return files
