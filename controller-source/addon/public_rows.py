"""Bounded, disposable public TMDb display snapshots. Never an account cache."""
from collections import OrderedDict
from contextlib import contextmanager
from copy import deepcopy
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlsplit,parse_qs,urlencode,unquote
import json,math,os,re,threading,time
from datetime import date
from xml.etree import ElementTree

_ART_CONTROLS=re.compile(r'[\x00-\x20]')
MAX_BYTES=2*1024*1024
MAX_ROWS=48
MAX_ITEMS=80
# Last successful display only; provider/session freshness is independent.
MAX_AGE=24*3600
PUBLIC_LISTS=frozenset(('popular','top_rated','upcoming','now_playing','trending_day','trending_week','airing_today','on_the_air','discover','similar','recommendations','trakt_trending','trakt_popular'))
PUBLIC_ITEMS=frozenset(('details','play','seasons','episodes','flatseasons'))

def public_path(path,item=False):
    """Fail closed: no arbitrary actions, search text, users, lists or secrets."""
    if not isinstance(path,str):return False
    try:
        url=urlsplit(path);query=parse_qs(url.query,keep_blank_values=True)
        if (url.scheme,url.netloc,url.path) != ('plugin','plugin.video.themoviedb.helper','/') or url.fragment:return False
        if any(len(v)!=1 for v in query.values()):return False
        info=query.get('info',[''])[0]
        if info not in (PUBLIC_LISTS|PUBLIC_ITEMS if item else PUBLIC_LISTS):return False
        if query.get('tmdb_type',['movie'])[0] not in ('movie','tv'):return False
        if info in PUBLIC_ITEMS and not query.get('tmdb_id',[''])[0].isdigit():return False
        fixed={'info','tmdb_type','nextpage','widget','cacheonly','update_listing','reload','with_id','include_adult'}
        numeric={'page','tmdb_id','season','episode','with_genres','without_genres','year','primary_release_year','first_air_date_year','with_networks','with_companies','with_keywords','without_keywords'}
        dates={field+'.'+bound for field in ('primary_release_date','first_air_date') for bound in ('gte','lte')}
        thresholds={field+'.'+bound for field in ('vote_average','vote_count') for bound in ('gte','lte')}
        if set(query)-fixed-numeric-dates-thresholds-{'sort_by','with_original_language','with_origin_country','region','with_separator','bl_start','countries','years'}:return False
        if {'countries','years'} & query.keys():
            if info!='trakt_popular':return False
            if 'countries' in query:
                countries=query['countries'][0].split(',')
                if not 1<=len(countries)<=32 or any(not re.fullmatch('[a-z]{2}',country) for country in countries):return False
            if 'years' in query:
                years=query['years'][0]
                if not re.fullmatch(r'[12]\d{3}(?:-[12]\d{3})?',years):return False
                bounds=[int(value) for value in years.split('-')]
                if bounds[0]>bounds[-1]:return False
        for k in numeric & query.keys():
            if not re.fullmatch(r'\d+(?:[,|]\d+)*',query[k][0]):return False
        for k in {'nextpage','widget','cacheonly','update_listing','with_id','include_adult'} & query.keys():
            if query[k][0] not in ('true','false'):return False
        for k in dates & query.keys():
            value=query[k][0]
            if re.fullmatch(r't[+-]\d{1,5}',value):continue
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):return False
            date.fromisoformat(value)
        for k in thresholds & query.keys():
            value=query[k][0]
            if not re.fullmatch(r'\d{1,9}(?:\.\d{1,3})?',value):return False
            if float(value)>(10 if k.startswith('vote_average.') else 100000000):return False
        if 'bl_start' in query and (not re.fullmatch(r'\d{1,5}',query['bl_start'][0]) or int(query['bl_start'][0])>10000):return False
        if 'with_separator' in query and query['with_separator'][0] not in ('OR','AND'):return False
        if 'with_origin_country' in query and not re.fullmatch('[A-Z]{2}',query['with_origin_country'][0]):return False
        if 'reload' in query and query['reload'][0] not in ('true','false','','$INFO[Window(Home).Property(TMDbHelper.Widgets.Reload)]','$INFO[System.Time(hh:mm:ss)]') and not re.fullmatch(r'\d+(?:[.:]\d+)*',query['reload'][0]):return False
        if 'sort_by' in query and query['sort_by'][0] not in ('popularity.desc','vote_average.desc','primary_release_date.desc','first_air_date.desc','revenue.desc','vote_count.desc'):return False
        if 'with_original_language' in query and not re.fullmatch('[a-z]{2}',query['with_original_language'][0]):return False
        if 'region' in query and not re.fullmatch('[A-Z]{2}',query['region'][0]):return False
        return True
    except (ValueError,TypeError):return False

def _item_path(path):
    if public_path(path,item=True):return path
    if not isinstance(path,str):return ''
    try:
        url=urlsplit(path);query=parse_qs(url.query,keep_blank_values=True)
        if query.get('info',[''])[0] not in PUBLIC_LISTS or 'page' not in query:return ''
        if any(len(values)!=1 for values in query.values()):return ''
        # Provider breadcrumb text is display-only and is never retained on disk.
        query.pop('plugin_category',None)
        if 'cacheonly' in query and query['cacheonly'][0].casefold() in ('true','false'):
            query['cacheonly']=[query['cacheonly'][0].casefold()]
        canonical=url._replace(query=urlencode({key:values[0] for key,values in query.items()})).geturl()
        return canonical if public_path(canonical,item=True) else ''
    except (TypeError,ValueError):return ''

@lru_cache(maxsize=4)
def _helper_setting_ids(schema):
    ids=tuple(sorted({node.attrib['id'] for node in ElementTree.fromstring(schema).iter('setting')
                      if node.attrib.get('id') and node.attrib.get('type')!='action'}))
    if not any('trakt' in key.lower() and any(word in key.lower() for word in ('user','token')) for key in ids):raise ValueError('Account settings schema unavailable')
    return ids

def helper_settings_identity(schema,get_setting):
    """Reuse schema parsing, and always read current settings through Kodi's API."""
    try:ids=_helper_setting_ids(bytes(schema) if isinstance(schema,(bytearray,memoryview)) else schema)
    except (ElementTree.ParseError,TypeError) as exc:raise ValueError('Helper settings schema unavailable') from exc
    values={key:get_setting(key) for key in ids}
    return sha256(json.dumps(values,sort_keys=True,separators=(',',':')).encode('utf-8')).digest()

def snapshot_scope(config,identity=b''):
    # Recent search text does not change any public discovery row or account.
    scoped={key:value for key,value in config.items() if key!='SearchQuery'}
    digest=sha256(json.dumps(scoped,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8'))
    digest.update(b'\0');digest.update(identity)
    return digest.hexdigest()

def _art(value):
    if not isinstance(value,str) or len(value)>4096 or _ART_CONTROLS.search(value):return ''
    try:
        u=urlsplit(value)
        if u.scheme=='image':
            # Kodi wraps native artwork keys. Validate its single decoded origin,
            # retaining the original key so existing image-cache entries still match.
            if u.path!='/' or not u.netloc or u.query or u.fragment:return ''
            inner=unquote(u.netloc,errors='strict')
            if _ART_CONTROLS.search(inner):return ''
            u=urlsplit(inner)
        return value if u.scheme=='https' and u.netloc=='image.tmdb.org' and not u.query and not u.fragment else ''
    except (ValueError,UnicodeError):return ''

def _finite_number(value,minimum=0,maximum=32503680000):
    if type(value) not in (int,float):return False
    try:return minimum<=value<=maximum and math.isfinite(float(value))
    except (OverflowError,ValueError):return False

def _items(files,path_filter=_item_path,max_items=MAX_ITEMS):
    if not isinstance(files,list) or not 0<len(files)<=max_items:return None
    result=[];artwork_memo={}
    def artwork(value):
        if not isinstance(value,str):return ''
        if value in artwork_memo:return artwork_memo[value]
        safe=_art(value)
        # One sanitization call only. Keep no unsafe addresses or global state.
        if safe and len(artwork_memo)<256:artwork_memo[value]=safe
        return safe
    for data in files:
        if not isinstance(data,dict):return None
        path=path_filter(data.get('file'))
        if not path:return None
        # Validate every rendering field before handing a disk row to native controls.
        text={'file','filetype','type','label','title','plot','mpaa','premiered','set','showtitle'}
        for key in text & data.keys():
            if not isinstance(data[key],str):return None
        for key in ('year','season','episode'):
            if key in data and (type(data[key]) is not int or not -1<=data[key]<=1000000):return None
        for key in ('runtime','rating'):
            if key in data and not _finite_number(data[key],maximum=100 if key=='rating' else 1000000000):return None
        for key in ('art','uniqueid'):
            if key in data and not isinstance(data[key],dict):return None
        for key in ('genre','country','director','studio','writer'):
            if key in data and not isinstance(data[key],(str,list)):return None
        if 'votes' in data and not ((type(data['votes']) is int and 0<=data['votes']<=10**12) or (isinstance(data['votes'],str) and len(data['votes'])<=32 and (data['votes']=='' or re.fullmatch(r'\d+(?:,\d{3})*',data['votes'])))):return None
        item={k:deepcopy(v) for k,v in data.items() if k in text|{'year','season','episode','rating','runtime','votes','genre','country','director','studio','writer'} and not isinstance(v,list)}
        item['file']=path
        for key in ('genre','country','director','studio','writer'):
            if isinstance(data.get(key),list):item[key]=[value for value in data[key] if isinstance(value,str)]
        if isinstance(data.get('art'),dict):item['art']={k:safe for k,v in data['art'].items() if isinstance(k,str) and (safe:=artwork(v))}
        if artwork(data.get('thumbnail')):item['thumbnail']=data['thumbnail']
        if isinstance(data.get('uniqueid'),dict):item['uniqueid']={k:v for k,v in data['uniqueid'].items() if k in ('tmdb','tvshow.tmdb','imdb') and isinstance(v,(str,int)) and re.fullmatch(r'(?:tt)?\d+',str(v))}
        result.append(item)
    return result

class PublicRowSnapshots:
    format_version=2
    max_bytes=MAX_BYTES
    max_rows=MAX_ROWS
    max_age=MAX_AGE
    path_allowed=staticmethod(public_path)
    sanitize_items=staticmethod(_items)
    def __init__(self,path,scope,clock=time.time,archive=False):
        self.path=Path(path);self.scope=scope;self.clock=clock;self.revision=0
        self.lock=threading.RLock();self.rows=OrderedDict();self.batch_depth=0;self.dirty=False
        # Private subclasses cannot opt into public visited history.
        self.archive_enabled=bool(archive) and type(self) is PublicRowSnapshots;self._archive=None;self._load()

    def _archive_store(self):
        if not self.archive_enabled:return None
        if self._archive is None:
            from public_row_archive import PublicRowArchive
            self._archive=PublicRowArchive(self.path.with_name(self.path.stem+'.archive.sqlite3'),self.scope,self.clock)
        return self._archive

    def _load(self):
        try:
            with self.path.open('rb') as stream:raw=stream.read(self.max_bytes+1)
            if len(raw)>self.max_bytes:return
            document=json.loads(raw)
            if not isinstance(document,dict) or document.get('version')!=self.format_version or document.get('scope')!=self.scope:return
            rows=document.get('rows')
            if not isinstance(rows,list) or len(rows)>self.max_rows:return
            for row in rows:
                if not isinstance(row,dict) or not self.path_allowed(row.get('path')):continue
                stamp=row.get('time')
                if not _finite_number(stamp) or not 0<=self.clock()-stamp<=self.max_age:continue
                items=self.sanitize_items(row.get('items'))
                if items:self.rows[row['path']]={'path':row['path'],'time':stamp,'items':items}
        except (OSError,ValueError,TypeError,OverflowError,RecursionError):self.rows.clear()

    def _prune(self):
        for path,row in list(self.rows.items()):
            if not 0<=self.clock()-row['time']<=self.max_age:self.rows.pop(path)

    def get(self,path):
        with self.lock:
            self._prune()
            row=self.rows.get(path)
            if row:return deepcopy(row['items'])
            archive=self._archive_store()
            return archive.get(path) if archive is not None else None

    def _encode(self,rows):
        return json.dumps({'version':self.format_version,'scope':self.scope,'rows':list(rows.values())},ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')

    def _write(self,raw):
        temporary=None
        try:
            self.path.parent.mkdir(parents=True,exist_ok=True)
            import tempfile
            with tempfile.NamedTemporaryFile(dir=str(self.path.parent),prefix=self.path.name+'.',suffix='.tmp',delete=False) as stream:
                temporary=stream.name;stream.write(raw);stream.flush();os.fsync(stream.fileno())
            os.replace(temporary,self.path)
        finally:
            if temporary:
                try:os.unlink(temporary)
                except FileNotFoundError:pass

    @contextmanager
    def batch(self):
        with self.lock:self.batch_depth+=1
        try:yield self
        finally:
            with self.lock:
                self.batch_depth-=1
                if not self.batch_depth:self.flush()

    def flush(self):
        with self.lock:
            if not self.dirty:return
            self._prune();raw=self._encode(self.rows)
            while len(raw)>self.max_bytes and self.rows:
                self.rows.popitem(last=False);raw=self._encode(self.rows)
            self._write(raw);self.dirty=False

    def put(self,path,files,revision=None):
        if not self.path_allowed(path):return False
        try:
            items=self.sanitize_items(files)
            if not items and files!=[]:return False
            with self.lock:
                if revision is not None and revision!=self.revision:return False
                self._prune();rows=self.rows.copy();rows.pop(path,None);evicted=[]
                if items:rows[path]={'path':path,'time':self.clock(),'items':items}
                while len(rows)>self.max_rows:evicted.append(rows.popitem(last=False)[1])
                raw=self._encode(rows)
                while len(raw)>self.max_bytes:
                    evicted.append(rows.popitem(last=False)[1])
                    if not rows:
                        archive=self._archive_store()
                        if archive is not None:archive.replace(path,[])
                        return False
                    raw=self._encode(rows)
                if self.batch_depth:
                    self.rows=rows;self.dirty=True
                else:
                    self._write(raw);self.rows=rows;self.dirty=False
                archive=self._archive_store()
                if archive is not None:
                    # Upgrade legacy resident displays only as normal background
                    # publication evicts them; preserve their original age.
                    for row in evicted:archive.replace(row['path'],row['items'],stamp=row['time'])
                    archive.replace(path,items or [])
                return path in rows or files==[]
        except (OSError,TypeError,ValueError,RecursionError):return False

    def clear(self,preserve_disk=False,preserve_display=False):
        with self.lock:
            self.revision+=1
            # Watch updates retire queued publications, but these sanitized
            # displays have no watch state. Keep their original expiry/history.
            if preserve_display:return
            self.rows.clear();self.dirty=False
            if preserve_disk:return
            archive=self._archive_store()
            if archive is not None:archive.clear()
            try:self.path.unlink()
            except FileNotFoundError:pass
            except OSError:
                # Best effort overwrite prevents an old valid snapshot resurfacing.
                try:self._write(self._encode(self.rows))
                except OSError:pass
