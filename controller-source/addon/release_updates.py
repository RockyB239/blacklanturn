"""Curated BlackLanturn release notices. Never tracks third-party add-on updates."""
import copy,hashlib,json,os,re,tempfile,time
from pathlib import Path,PurePosixPath
from urllib.parse import urlsplit,unquote
from urllib.request import urlopen,Request
MAX_BYTES=262144
FEED='https://rockyb239.github.io/blacklanturn/hosted-files/releases-v1.json'
def version(value):
 if not isinstance(value,str) or not re.fullmatch(r'\d{1,5}\.\d{1,5}\.\d{1,5}',value):raise ValueError('Invalid release version')
 return tuple(map(int,value.split('.')))
def text(value,limit=240):
 if not isinstance(value,str) or not value or len(value)>limit or any(ord(c)<32 for c in value) or '[' in value or ']' in value:raise ValueError('Invalid release text')
 return value
def identity(marker):
 if not isinstance(marker,dict):raise ValueError('Invalid installed release')
 edition=marker.get('edition');v=marker.get('build_version',marker.get('version'));rev=marker.get('release_revision',marker.get('revision',0))
 if edition not in ('apple','general') or type(rev) is not int or not 0<=rev<=100000:raise ValueError('Invalid installed release')
 version(v);return {'edition':edition,'version':v,'revision':rev}
def order(entry):return version(entry['version']),entry['revision']
def validate_catalog(cat):
 if not isinstance(cat,dict) or set(cat)!={'schema','releases'} or cat['schema']!=1 or not isinstance(cat['releases'],list) or len(cat['releases'])>30:raise ValueError('Invalid release catalog')
 ids=set()
 for e in cat['releases']:
  if not isinstance(e,dict) or set(e)!={'id','edition','version','revision','title','summary','sections','files'}:raise ValueError('Invalid release entry')
  identity(e)
  if not isinstance(e['id'],str) or not re.fullmatch(r'[a-zA-Z0-9._-]{1,100}',e['id']) or e['id'] in ids:raise ValueError('Invalid release identity')
  ids.add(e['id']);text(e['title'],100);text(e['summary'],240)
  if not isinstance(e['sections'],list) or not 1<=len(e['sections'])<=12:raise ValueError('Invalid release sections')
  for s in e['sections']:
   if not isinstance(s,dict) or set(s)!={'heading','bullets'}:raise ValueError('Invalid section')
   text(s['heading'],80)
   if not isinstance(s['bullets'],list) or not 1<=len(s['bullets'])<=6:raise ValueError('Invalid release bullets')
   for line in s['bullets']:text(line)
  if not isinstance(e['files'],dict) or not 1<=len(e['files'])<=1000:raise ValueError('Release installation proof missing')
  for p,digest in e['files'].items():
   if not isinstance(p,str) or len(p)>240 or not p.startswith('addons/') or '\\' in p or any(x in ('..','.') for x in p.split('/')) or str(PurePosixPath(p))!=p:raise ValueError('Unsafe release proof path')
   if not isinstance(digest,str) or not re.fullmatch(r'[a-f0-9]{64}',digest):raise ValueError('Invalid release proof hash')
 return cat

def empty_state(enabled=True):return {'schema':2,'enabled':enabled,'installed':None,'available':None,'completed':None,'history':[],'seen':[]}
def validate_state(s):
 if not isinstance(s,dict) or set(s)!=set(empty_state()) or s['schema']!=2 or type(s['enabled']) is not bool:raise ValueError('Invalid release notice state')
 if s['installed'] is not None:identity(s['installed'])
 if not isinstance(s['history'],list) or len(s['history'])>20 or not isinstance(s['seen'],list) or len(s['seen'])>80 or any(not isinstance(x,str) or len(x)>120 for x in s['seen']):raise ValueError('Invalid release history')
 entries=s['history']+[e for e in (s['available'],s['completed']) if e]
 for e in entries:validate_catalog({'schema':1,'releases':[e]})
 return s

def verified(home,entry):
 base=Path(home).resolve();total=0
 try:
  receipt=base/'userdata/blacklanturn-install-complete.json'
  if receipt.is_symlink() or receipt.stat().st_size>16384:return False
  completed=json.loads(receipt.read_text())
  expected={'schema':1,'id':entry['id'],'edition':entry['edition'],'version':entry['version'],'revision':entry['revision'],'complete':True}
  if completed!=expected:return False
 except (ValueError,OSError):return False
 for name,want in entry['files'].items():
  p=base/name
  if any(q.is_symlink() for q in (p,*p.parents)) or not p.is_file():return False
  size=p.stat().st_size;total+=size
  if size>25*1024*1024 or total>50*1024*1024:return False
  if hashlib.sha256(p.read_bytes()).hexdigest()!=want:return False
 return True

def refresh(state,marker,catalog,now,home):
 validate_catalog(catalog);installed=identity(marker)
 s=copy.deepcopy(validate_state(state) if state else empty_state())
 if s['installed'] is None:s['installed']=installed
 matches=[e for e in catalog['releases'] if e['edition']==installed['edition']]
 delivered=next((e for e in matches if order(e)==order(installed)),None)
 if order(installed)>order(s['installed']) and delivered and verified(home,delivered):
  s['installed']=installed;s['completed']=copy.deepcopy(delivered)
  s['history']=([e for e in s['history'] if e['id']!=delivered['id']]+[copy.deepcopy(delivered)])[-20:]
 candidates=[e for e in matches if order(e)>order(s['installed'])]
 s['available']=copy.deepcopy(max(candidates,key=order)) if candidates else None
 return s

def pending(state):
 if not state or not state['enabled']:return None
 for kind,key in (('completed','completed'),('available','available')):
  entry=state.get(key)
  if entry and kind+':'+entry['id'] not in state['seen']:return {'kind':kind,'release':entry}
 return None

def dismiss(state,event=None):
 s=copy.deepcopy(state);event=event or pending(s)
 if event:
  key=event['kind']+':'+event['release']['id']
  s['seen']=list(dict.fromkeys(s['seen']+[key]))[-80:]
 return s

def read_state(path,legacy=None):
 p=Path(path)
 if not p.exists():
  enabled=True
  if legacy and Path(legacy).is_file():
   try:
    old=json.loads(Path(legacy).read_text());enabled=old.get('enabled',True)
   except (ValueError,OSError):pass
  return empty_state(enabled if type(enabled) is bool else True)
 if p.stat().st_size>MAX_BYTES:raise ValueError('Oversized release notice state')
 return validate_state(json.loads(p.read_text(encoding='utf-8')))
def write_state(path,state):
 validate_state(state);p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
 raw=json.dumps(state,ensure_ascii=False,indent=2)
 if len(raw.encode())>MAX_BYTES:raise ValueError('Oversized release notice state')
 fd,name=tempfile.mkstemp(prefix=p.name+'.',dir=str(p.parent))
 try:
  with os.fdopen(fd,'w',encoding='utf-8') as f:f.write(raw);f.flush();os.fsync(f.fileno())
  os.replace(name,p)
 finally:
  if os.path.exists(name):os.unlink(name)
def transact(path,transform,legacy=None):
 # The legacy utility supplies the same bounded cross-interpreter lock. Its
 # reader/writer are explicitly overridden; old inventory data is never loaded.
 from update_notes import transact as locked
 return locked(path,transform,reader=lambda p:read_state(p,legacy),writer=write_state)

def fetch_catalog(source=FEED):
 url=urlsplit(source)
 if url.scheme=='file':
  p=Path(unquote(url.path))
  if url.netloc or p.stat().st_size>MAX_BYTES:raise ValueError('Invalid local catalog')
  raw=p.read_bytes()
 elif url.scheme=='https' and url.hostname=='rockyb239.github.io' and not url.username and not url.password:
  start=time.monotonic()
  with urlopen(Request(source,headers={'User-Agent':'BlackLanturn/1'}),timeout=2) as response:
   if urlsplit(response.url).hostname!=url.hostname:raise ValueError('Unexpected catalog redirect')
   raw=b''
   while len(raw)<=MAX_BYTES:
    remaining=5-(time.monotonic()-start)
    if remaining<=0:raise OSError('Release catalog timed out')
    # read1 performs one bounded socket read, rather than waiting to fill a
    # large buffer while a slow peer keeps the inactivity timeout alive.
    sock=getattr(getattr(getattr(response,'fp',None),'raw',None),'_sock',None)
    if sock is not None:sock.settimeout(min(2,remaining))
    part=response.read1(min(16384,MAX_BYTES+1-len(raw)));raw+=part
    if time.monotonic()-start>=5:raise OSError('Release catalog timed out')
    if not part:break
 else:raise ValueError('Unsupported release catalog source')
 if len(raw)>MAX_BYTES:raise ValueError('Oversized release catalog')
 return validate_catalog(json.loads(raw.decode('utf-8')))

def sections_text(entry):
 if not entry:return 'BlackLanturn release notes will appear here when a release is available.'
 return '\n\n'.join('[B]'+s['heading']+'[/B]\n'+'\n'.join('• '+line for line in s['bullets']) for s in entry['sections'])
