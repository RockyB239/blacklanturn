"""Private display-only YouTube rows; current watch state never comes from disk JSON."""
from copy import deepcopy
from contextlib import closing
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
import io,json,math,os,pickle,re,sqlite3,tempfile,threading,time
from youtube_core import video_id

MAX_BYTES=2*1024*1024
MAX_ROWS=18
MAX_ITEMS=60
FRESH_AGE=300
MAX_AGE=24*3600
_QUERY={'video_id','playlist_id','channel_id','page','page_token','click_tracking','visitor','refresh','filtered','%exclude','bl_shelf','resume','category_label'}

def _route(path):
 if not isinstance(path,str) or len(path)>32768:return False
 try:
  u=urlsplit(path)
  return (u.scheme=='plugin' and u.netloc=='plugin.video.youtube' and u.path.startswith('/') and not u.fragment
          and not any(c in path for c in ('\n','\r','\0')) and not set(parse_qs(u.query,keep_blank_values=True))-_QUERY)
 except ValueError:return False

def _cursor(value):
 if value is None:return None
 if not isinstance(value,dict):raise ValueError('Invalid cursor')
 keys={'path','continuation','clickTrackingParams','visitor','related_seeds','seed_index','page_token','relevance_family'}
 if set(value)-keys:raise ValueError('Unknown cursor context')
 result={k:deepcopy(v) for k,v in value.items() if not (v is None and k in ('visitor','clickTrackingParams'))}
 for k,v in result.items():
  if k=='path':
   if not _route(v):raise ValueError('Invalid continuation route')
  elif k=='related_seeds':
   if not isinstance(v,list) or len(v)>6 or any(not isinstance(s,str) or not re.fullmatch(r'[A-Za-z0-9_-]{11}',s) for s in v):raise ValueError('Invalid seeds')
  elif k=='seed_index':
   if type(v) is not int or not 0<=v<=6:raise ValueError('Invalid seed index')
  elif not isinstance(v,str) or len(v)>32768:raise ValueError('Invalid cursor field')
 if result.get('related_seeds'):
  if not 0<=result.get('seed_index',0)<len(result['related_seeds']):raise ValueError('Seed index outside cursor')
 elif not result.get('path') and not result.get('continuation'):raise ValueError('Cursor has no continuation')
 return result

def display_row(row):
 if not isinstance(row,dict) or not _route(row.get('path')):raise ValueError('Invalid row route')
 u=urlsplit(row['path'])
 if u.path.rstrip('/') not in ('/special/recommendations','/special/my_subscriptions'):raise ValueError('Not a Home row')
 label=row.get('label');files=row.get('local_items')
 if not isinstance(label,str) or not 0<len(label)<=256 or not isinstance(files,list) or not 0<len(files)<=MAX_ITEMS:raise ValueError('Invalid row')
 result={'path':row['path'],'label':label,'local_items':[]}
 for source in files:
  if not isinstance(source,dict) or not _route(source.get('file')):raise ValueError('Invalid card')
  if source.get('_page_control') or source.get('_youtube_more'):continue
  item={'file':source['file'],'filetype':'directory' if source.get('filetype')=='directory' else 'file'}
  if item['filetype']=='file' and not video_id(item):raise ValueError('Not a video')
  for k,limit in [('title',1024),('label',1024),('plot',12000)]:
   v=source.get(k,'')
   if not isinstance(v,str) or len(v)>limit:raise ValueError('Invalid display text')
   item[k]=v
  runtime=source.get('runtime',0)
  if runtime is None or runtime==-1:runtime=0 # Native live/unknown-duration sentinel.
  if type(runtime) not in (int,float) or not math.isfinite(runtime) or not 0<=runtime<=10000000:raise ValueError('Invalid duration')
  item['runtime']=runtime
  for k in ('artist','studio'):
   values=source.get(k,[])
   if isinstance(values,str):values=[values]
   if not isinstance(values,list) or len(values)>20 or any(not isinstance(v,str) or len(v)>1024 for v in values):raise ValueError('Invalid channel')
   item[k]=deepcopy(values)
  art=source.get('art',{})
  if not isinstance(art,dict):raise ValueError('Invalid artwork')
  item['art']={}
  for k in ('thumb','fanart','icon','youtubefallback'):
   v=art.get(k)
   if not isinstance(v,str) or len(v)>4096:continue
   parsed=urlsplit(v)
   # No arbitrary filesystem or credential-bearing URL from a cache file.
   remote=parsed.scheme=='https' and not parsed.username and (parsed.hostname or '').endswith(('.ytimg.com','.ggpht.com','.googleusercontent.com'))
   bundled=(item['filetype']=='directory' and not parsed.scheme and not parsed.netloc and v.startswith('/') and '/addons/plugin.video.youtube/' in v and not parsed.query and not parsed.fragment
            and '..' not in Path(v).parts and v.split('/addons/plugin.video.youtube/',1)[1].startswith('resources/media/')
            and Path(v).suffix.lower() in ('.png','.jpg','.jpeg'))
   if remote or bundled:item['art'][k]=v
  if 'thumb' in item['art']:item['thumbnail']=item['art']['thumb']
  result['local_items'].append(item)
 if not result['local_items']:raise ValueError('Empty row')
 for key in ('youtube_cursor','youtube_fallback'):
  if key in row:result[key]=_cursor(row[key])
 if row.get('youtube_category'):result['youtube_category']=True
 if isinstance(row.get('relevance_family'),str):result['relevance_family']=row['relevance_family'][:128]
 return result

class SavedRows:
 def __init__(self,path,scope,clock=time.time):
  self.path=Path(path);self.scope=scope;self.clock=clock;self.lock=threading.RLock();self.rows=[]
  try:
   with self.path.open('rb') as f:raw=f.read(MAX_BYTES+1)
   if len(raw)>MAX_BYTES:return
   data=json.loads(raw)
   if not isinstance(data,dict) or data.get('version')!=1 or data.get('scope')!=scope:return
   rows=data.get('rows')
   if not isinstance(rows,list) or len(rows)>MAX_ROWS:return
   for row in rows:
    stamp=row.get('fetched_at')
    if type(stamp) not in (int,float) or not math.isfinite(stamp) or not 0<=clock()-stamp<=MAX_AGE:continue
    clean=display_row(row);clean['fetched_at']=stamp;self.rows.append(clean)
  except (OSError,ValueError,TypeError,AttributeError,OverflowError,RecursionError):self.rows=[]
 def get(self):
  with self.lock:
   return [dict(deepcopy(r),_youtube_saved=True,_youtube_saved_scope=self.scope) for r in self.rows if 0<=self.clock()-r['fetched_at']<=MAX_AGE]
 def fresh(self):
  rows=self.get();return bool(rows) and all(0<=self.clock()-r['fetched_at']<FRESH_AGE for r in rows)
 def put(self,row,current=lambda:True):
  return self.put_many([row],current=current)
 def put_many(self,incoming,replace_categories=False,current=lambda:True):
  if not current():return False
  try:cleaned=[display_row(row) for row in incoming]
  except (TypeError,ValueError,OverflowError,RecursionError):return False
  if not cleaned:return False
  with self.lock:
   if not current():return False
   stamp=self.clock();paths={r['path'] for r in cleaned}
   for clean in cleaned:clean['fetched_at']=stamp
   rows=[r for r in self.rows if r['path'] not in paths and 0<=stamp-r['fetched_at']<=MAX_AGE and not (replace_categories and r.get('youtube_category'))]+cleaned
   rows=rows[-MAX_ROWS:]
   raw=json.dumps({'version':1,'scope':self.scope,'rows':rows},ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
   if len(raw)>MAX_BYTES:return False
   pending=None
   try:
    self.path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=self.path.parent,prefix=self.path.name+'.',delete=False) as f:
     pending=f.name;os.chmod(pending,0o600);f.write(raw);f.flush();os.fsync(f.fileno())
    if not current():return False
    os.replace(pending,self.path);self.rows=rows;return True
   except OSError:return False
   finally:
    if pending:
     try:os.unlink(pending)
     except FileNotFoundError:pass
 def clear(self):
  with self.lock:
   self.rows=[]
   try:self.path.unlink()
   except OSError:pass

class HistoryUnavailable(RuntimeError):pass
class _HistoryValue(pickle.Unpickler):
 def find_class(self,module,name):raise ValueError('History contains non-data values')

def current_watch(files,path,enabled=True):
 """Read the add-on's current local history, including WAL, without writing it."""
 result=deepcopy(files);ids=list(dict.fromkeys(filter(None,map(video_id,result))));history={};path=Path(path)
 try:
  if enabled and path.exists() and ids:
   with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True,timeout=.15)) as db:
    db.execute('PRAGMA query_only=ON')
    for start in range(0,len(ids),60):
     batch=ids[start:start+60]
     for key,blob in db.execute('SELECT key,value FROM storage_v2 WHERE key IN ('+','.join('?'*len(batch))+')',batch):
      if not isinstance(blob,bytes) or len(blob)>65536:raise ValueError('Invalid history value')
      value=_HistoryValue(io.BytesIO(blob)).load()
      if not isinstance(value,dict):raise ValueError('Invalid history object')
      history[key]=value
  for item in result:
   ident=video_id(item)
   if not ident:continue
   values=history.get(ident,{})
   count=values.get('play_count',0);position=values.get('played_time',0)
   if type(count) not in (int,float) or not math.isfinite(count) or not 0<=count<=1000000:raise ValueError('Invalid play count')
   if type(position) not in (int,float) or not math.isfinite(position) or not 0<=position<=10000000:raise ValueError('Invalid resume')
   item['playcount']=count;item['resume']={'position':position,'total':item.get('runtime',0)}
  return result
 except (sqlite3.Error,OSError,ValueError,TypeError,pickle.UnpicklingError,EOFError,OverflowError,RecursionError) as exc:raise HistoryUnavailable('Local YouTube history unavailable') from exc
