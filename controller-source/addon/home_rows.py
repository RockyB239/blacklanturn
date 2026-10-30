"""Private, account-scoped Home artwork; normal Trakt requests still refresh it."""
import json,time
from urllib.parse import urlsplit,parse_qs,urlencode
from public_rows import PublicRowSnapshots,_items,_item_path,snapshot_scope,_finite_number,public_path

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
    max_bytes=256*1024
    max_rows=2
    max_age=24*3600
    path_allowed=staticmethod(home_path)
    sanitize_items=staticmethod(lambda files:_items(files,path_filter=home_item_path,max_items=40))
