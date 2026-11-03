"""Local movie/show feedback; read once and write only on an explicit choice."""
import hashlib,json,os,re,threading
from itertools import combinations
from pathlib import Path
from urllib.parse import parse_qs,urlsplit
from uuid import uuid4
SESSION=uuid4().hex
MAX_BYTES=256*1024
MAX_TITLES=2000
PUBLIC_LISTS=frozenset(('discover','popular','top_rated','trending_week','trending_day','now_playing','upcoming','airing_today','on_the_air','trakt_popular','trakt_trending','trakt_recommendations','recommendations','similar'))

def title_key(item):
    if not isinstance(item,dict) or item.get('_page_control') or item.get('type') in ('episode','season','person','addon'):return None
    u=urlsplit(item.get('file') or '')
    if (u.scheme,u.netloc,u.path)!=('plugin','plugin.video.themoviedb.helper','/'):return None
    q=parse_qs(u.query)
    if any(k in q for k in ('season','episode')):return None
    if q.get('info',[''])[0] not in ('play','seasons','details'):return None
    kind=q.get('tmdb_type',[''])[0];ident=q.get('tmdb_id',[''])[0]
    series=kind=='tv' and (item.get('type')=='tvshow' or item.get('filetype')=='directory' and q.get('info')==['seasons'])
    if isinstance(item.get('episode'),int) and item['episode']>=0 and not series:return None
    if kind not in ('movie','tv') or not re.fullmatch(r'[1-9][0-9]*',ident):return None
    return kind+':'+ident

def discovery_scope(window,path):
    if getattr(window,'section','') not in ('Home','Movies','Shows') or getattr(window,'mode','') not in ('home','details'):return False
    if any(getattr(window,k,None) is not None for k in ('search_state','episode_browser_context','person_context')):return False
    u=urlsplit(path);q=parse_qs(u.query)
    if 'with_watch_providers' in q:return False
    return (u.scheme,u.netloc,u.path)==('plugin','plugin.video.themoviedb.helper','/') and q.get('info',[''])[0] in PUBLIC_LISTS

def record_item(record):
    kind,ident=record['key'].split(':')
    return {'label':record['label'],'file':'plugin://plugin.video.themoviedb.helper/?info='+('seasons' if kind=='tv' else 'play')+'&tmdb_type='+kind+'&tmdb_id='+ident}

def _similarity(item):
    genres=item.get('genre') or []
    if isinstance(genres,str):genres=re.split(r'[,/|]',genres)
    if not isinstance(genres,(list,tuple)):genres=[]
    return {
        'genres':sorted({g.strip().casefold()[:80] for g in genres[:10] if isinstance(g,str) and g.strip()}),
        'collection':str(item.get('set') or '').strip().casefold()[:200],
    }

def _preference_index(records):
    collections=set()
    genre_pairs=set()
    for key,record in records.items():
        if record['mode']!='more':continue
        kind=key.split(':')[0]
        if record['collection']:collections.add((kind,record['collection']))
        genre_pairs.update((kind,pair) for pair in combinations(record['genres'],2))
    return collections,genre_pairs

class TitlePreferences:
    def __init__(self,path,session=None):
        self.path=Path(path);self.session=SESSION if session is None else session;self.lock=threading.RLock();self.records={};self.error=''
        try:
            if self.path.stat().st_size>MAX_BYTES:raise ValueError('Title preference file is too large')
            value=json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(value,dict) or value.get('version')!=1 or not isinstance(value.get('titles'),dict) or len(value['titles'])>MAX_TITLES:raise ValueError('Unsupported title preference file')
            for key,record in value['titles'].items():
                if not re.fullmatch(r'(movie|tv):[1-9][0-9]*',key) or not isinstance(record,dict) or record.get('mode') not in ('hide','less') or not isinstance(record.get('label'),str) or len(record['label'])>200 or not isinstance(record.get('session',''),str):raise ValueError('Invalid title preference')
            preferred=value.get('preferred',{})
            if not isinstance(preferred,dict) or len(value['titles'])+len(preferred)>MAX_TITLES:
                raise ValueError('Invalid positive title preferences')
            for key,record in preferred.items():
                if (key in value['titles'] or not re.fullmatch(r'(movie|tv):[1-9][0-9]*',key)
                    or not isinstance(record,dict) or record.get('mode')!='more'
                    or not isinstance(record.get('label'),str) or len(record['label'])>200
                    or not isinstance(record.get('collection'),str) or len(record['collection'])>200
                    or not isinstance(record.get('genres'),list) or len(record['genres'])>10
                    or any(not isinstance(genre,str) or len(genre)>80 for genre in record['genres'])):
                    raise ValueError('Invalid positive title preference')
            self.records={**value['titles'],**preferred}
        except FileNotFoundError:pass
        except (OSError,ValueError,TypeError) as exc:self.error=str(exc)
        self.preferred_index=_preference_index(self.records)
    def state(self,item):
        with self.lock:return self.records.get(title_key(item),{}).get('mode','')
    def entries(self,mode):
        with self.lock:return sorted((dict(v,key=k) for k,v in self.records.items() if v['mode']==mode),key=lambda x:x['label'].casefold())
    def set(self,item,mode):
        key=title_key(item)
        if not key or mode not in ('hide','less','more'):raise ValueError('Choose a supported movie or show')
        label=str(item.get('title') or item.get('label') or key)[:200]
        with self.lock:
            prior=self.records.get(key);updated=dict(self.records);updated[key]={'mode':mode,'label':label,'session':self.session}
            if mode=='more':updated[key].update(_similarity(item))
            self._write(updated)
            return dict(prior) if prior else None
    def restore(self,item,previous=None):
        key=title_key(item)
        if not key:raise ValueError('Choose a supported movie or show')
        with self.lock:
            updated=dict(self.records)
            if previous:updated[key]=dict(previous)
            else:updated.pop(key,None)
            self._write(updated)
    def _write(self,updated):
        if self.error:raise ValueError('Saved title preferences could not be read; the original file was left unchanged')
        # Version 1 readers can still load their original negative preferences.
        titles={key:record for key,record in updated.items() if record['mode']!='more'}
        preferred={key:record for key,record in updated.items() if record['mode']=='more'}
        payload={'version':1,'titles':titles}
        if preferred:payload['preferred']=preferred
        raw=json.dumps(payload,ensure_ascii=False,sort_keys=True).encode('utf-8')
        if len(updated)>MAX_TITLES or len(raw)>MAX_BYTES:raise ValueError('Title preference storage is full; restore some titles first')
        self.path.parent.mkdir(parents=True,exist_ok=True)
        import tempfile
        fd,name=tempfile.mkstemp(prefix=self.path.name+'.',suffix='.pending',dir=str(self.path.parent))
        temporary=Path(name)
        try:
            with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
            os.replace(temporary,self.path)
        finally:
            if temporary.exists():temporary.unlink()
        self.records=updated
        self.preferred_index=_preference_index(updated)
    def apply(self,files,enabled=True):
        if not enabled:return files
        with self.lock:
            if not self.records:return files
            def keep(item):
                key=title_key(item);record=self.records.get(key)
                if not record or record['mode']=='more':return True
                if record['mode']=='hide' or record.get('session')==self.session:return False
                return int.from_bytes(hashlib.sha256((self.session+':'+key).encode()).digest()[:2],'big')%4==0
            visible=[item for item in files if keep(item)]
            collections,pairs=self.preferred_index
            if not collections and not pairs:return visible
            positions=[];matches=[]
            for index,item in enumerate(visible):
                key=title_key(item)
                if not key:continue
                positions.append(index)
                if key in self.records:continue
                kind=key.split(':')[0];metadata=_similarity(item)
                if (kind,metadata['collection']) in collections:matches.append((0,index))
                elif any((kind,pair) in pairs for pair in combinations(metadata['genres'],2)):
                    matches.append((1,index))
            promoted=[index for _,index in sorted(matches)[:3]]
            if not promoted:return visible
            order=promoted+[index for index in positions if index not in promoted]
            ordered=[visible[index] for index in order]
            for position,item in zip(positions,ordered):visible[position]=item
            return visible
