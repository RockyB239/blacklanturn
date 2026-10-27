"""Bounded, disposable public TMDb display snapshots. Never an account cache."""
from collections import OrderedDict
from contextlib import contextmanager
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlsplit,parse_qs,urlencode
import json,math,os,re,tempfile,threading,time
from xml.etree import ElementTree

MAX_BYTES=2*1024*1024
MAX_ROWS=12
MAX_ITEMS=80
MAX_AGE=15*60
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
        fixed={'info','tmdb_type','nextpage','widget','cacheonly','update_listing','reload'}
        numeric={'page','tmdb_id','season','episode','with_genres','without_genres','year','primary_release_year','first_air_date_year','with_networks','with_companies'}
        if set(query)-fixed-numeric-{'sort_by','with_original_language','region'}:return False
        for k in numeric & query.keys():
            if not re.fullmatch(r'\d+(?:[,|]\d+)*',query[k][0]):return False
        for k in {'nextpage','widget','cacheonly','update_listing'} & query.keys():
            if query[k][0] not in ('true','false'):return False
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

def helper_settings_identity(schema,get_setting):
    """Read through Kodi's settings API, including tvOS's native settings store."""
    try:ids=sorted({node.attrib['id'] for node in ElementTree.fromstring(schema).iter('setting') if node.attrib.get('id') and node.attrib.get('type')!='action'})
    except (ElementTree.ParseError,TypeError) as exc:raise ValueError('Helper settings schema unavailable') from exc
    if not any('trakt' in key.lower() and any(word in key.lower() for word in ('user','token')) for key in ids):raise ValueError('Account settings schema unavailable')
    values={key:get_setting(key) for key in ids}
    return sha256(json.dumps(values,sort_keys=True,separators=(',',':')).encode('utf-8')).digest()

def snapshot_scope(config,identity=b''):
    # Recent search text does not change any public discovery row or account.
    scoped={key:value for key,value in config.items() if key!='SearchQuery'}
    digest=sha256(json.dumps(scoped,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8'))
    digest.update(b'\0');digest.update(identity)
    return digest.hexdigest()

def _art(value):
    if not isinstance(value,str):return ''
    try:
        u=urlsplit(value)
        return value if u.scheme=='https' and u.netloc=='image.tmdb.org' and not u.query and not u.fragment else ''
    except ValueError:return ''

def _finite_number(value,minimum=0,maximum=32503680000):
    if type(value) not in (int,float):return False
    try:return minimum<=value<=maximum and math.isfinite(float(value))
    except (OverflowError,ValueError):return False

def _items(files):
    if not isinstance(files,list) or not 0<len(files)<=MAX_ITEMS:return None
    result=[]
    for data in files:
        if not isinstance(data,dict):return None
        path=_item_path(data.get('file'))
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
        for key in ('genre','director','studio','writer'):
            if key in data and not isinstance(data[key],(str,list)):return None
        item={k:deepcopy(v) for k,v in data.items() if k in text|{'year','season','episode','rating','runtime','genre','director','studio','writer'} and not isinstance(v,list)}
        item['file']=path
        for key in ('genre','director','studio','writer'):
            if isinstance(data.get(key),list):item[key]=[value for value in data[key] if isinstance(value,str)]
        if isinstance(data.get('art'),dict):item['art']={k:safe for k,v in data['art'].items() if isinstance(k,str) and (safe:=_art(v))}
        if _art(data.get('thumbnail')):item['thumbnail']=data['thumbnail']
        if isinstance(data.get('uniqueid'),dict):item['uniqueid']={k:v for k,v in data['uniqueid'].items() if k in ('tmdb','tvshow.tmdb','imdb') and isinstance(v,(str,int)) and re.fullmatch(r'(?:tt)?\d+',str(v))}
        result.append(item)
    return result

class PublicRowSnapshots:
    def __init__(self,path,scope,clock=time.time):
        self.path=Path(path);self.scope=scope;self.clock=clock;self.revision=0
        self.lock=threading.RLock();self.rows=OrderedDict();self.batch_depth=0;self.dirty=False;self._load()

    def _load(self):
        try:
            with self.path.open('rb') as stream:raw=stream.read(MAX_BYTES+1)
            if len(raw)>MAX_BYTES:return
            document=json.loads(raw)
            if not isinstance(document,dict) or document.get('version')!=1 or document.get('scope')!=self.scope:return
            rows=document.get('rows')
            if not isinstance(rows,list) or len(rows)>MAX_ROWS:return
            for row in rows:
                if not isinstance(row,dict) or not public_path(row.get('path')):continue
                stamp=row.get('time');items=_items(row.get('items'))
                if _finite_number(stamp) and 0<=self.clock()-stamp<=MAX_AGE and items:
                    self.rows[row['path']]={'path':row['path'],'time':stamp,'items':items}
        except (OSError,ValueError,TypeError,OverflowError,RecursionError):self.rows.clear()

    def _prune(self):
        for path,row in list(self.rows.items()):
            if not 0<=self.clock()-row['time']<=MAX_AGE:self.rows.pop(path)

    def get(self,path):
        with self.lock:
            self._prune()
            row=self.rows.get(path)
            return deepcopy(row['items']) if row else None

    def _encode(self,rows):
        return json.dumps({'version':1,'scope':self.scope,'rows':list(rows.values())},ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')

    def _write(self,raw):
        temporary=None
        try:
            self.path.parent.mkdir(parents=True,exist_ok=True)
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
            while len(raw)>MAX_BYTES and self.rows:
                self.rows.popitem(last=False);raw=self._encode(self.rows)
            self._write(raw);self.dirty=False

    def put(self,path,files,revision=None):
        if not public_path(path):return False
        try:
            items=_items(files)
            if not items and files!=[]:return False
            with self.lock:
                if revision is not None and revision!=self.revision:return False
                self._prune();rows=self.rows.copy();rows.pop(path,None)
                if items:rows[path]={'path':path,'time':self.clock(),'items':items}
                while len(rows)>MAX_ROWS:rows.popitem(last=False)
                if self.batch_depth:
                    self.rows=rows;self.dirty=True
                else:
                    raw=self._encode(rows)
                    while len(raw)>MAX_BYTES:
                        rows.popitem(last=False)
                        if not rows:return False
                        raw=self._encode(rows)
                    self._write(raw);self.rows=rows;self.dirty=False
                return path in rows or files==[]
        except (OSError,TypeError,ValueError,RecursionError):return False

    def clear(self):
        with self.lock:
            self.revision+=1;self.rows.clear();self.dirty=False
            try:self.path.unlink()
            except FileNotFoundError:pass
            except OSError:
                # Best effort overwrite prevents an old valid snapshot resurfacing.
                try:self._write(self._encode(self.rows))
                except OSError:pass
