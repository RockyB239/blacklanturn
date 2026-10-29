"""Public series state from existing TMDbHelper cache; no network or account reads."""
from collections import OrderedDict
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
import re,sqlite3,threading,time
LABELS={'returning series':'Returning series','ended':'Ended','canceled':'Canceled','cancelled':'Canceled','in production':'In production','planned':'Planned','pilot':'Pilot'}
def status_label(value):return LABELS.get(value.strip().casefold(),'') if isinstance(value,str) else ''
def series_id(item):
    if item.get('_page_control') or item.get('type') in ('movie','episode','season','person','addon'):return None
    u=urlsplit(item.get('file',''));q=parse_qs(u.query)
    if u.netloc!='plugin.video.themoviedb.helper' or q.get('tmdb_type',q.get('type',['']))!=['tv'] or any(k in q for k in ('season','episode')):return None
    value=q.get('tmdb_id',[''])[0]
    return value if re.fullmatch(r'[1-9][0-9]*',value) else None
class SeriesStatus:
    def __init__(self,profile,clock=time.monotonic):
        self.profile=Path(profile);self.clock=clock;self.cache=OrderedDict();self.reads=0;self.lock=threading.RLock()
    def enrich(self,files):
        now=self.clock();ids=list(dict.fromkeys(i for i in (series_id(x) for x in files) if i));found={}
        if not ids:return files
        with self.lock:
            missing=[i for i in ids if i not in self.cache or self.cache[i][0]<=now]
            if missing:
                folders=sorted((p for p in self.profile.glob('database_*') if re.fullmatch(r'database_\d+',p.name)),key=lambda p:int(p.name.split('_')[-1]),reverse=True)
                for folder in folders:
                    db=folder/'ItemDetails.db'
                    if not db.is_file():continue
                    try:
                        with sqlite3.connect(db.resolve().as_uri()+'?mode=ro',uri=True,timeout=.02) as c:
                            self.reads+=1
                            for start in range(0,len(missing),128):
                                batch=missing[start:start+128];marks=','.join('?' for _ in batch)
                                for ident,status in c.execute('SELECT tmdb_id,status FROM tvshow WHERE tmdb_id IN ('+marks+')',batch):found[str(ident)]=status_label(status)
                        break
                    except (OSError,sqlite3.Error):continue
                for i in missing:
                    value=found.get(i,'');self.cache[i]=(now+(300 if value else 15),value);self.cache.move_to_end(i)
                while len(self.cache)>1024:self.cache.popitem(last=False)
            result=[]
            for item in files:
                i=series_id(item);value=(status_label(item.get('status')) or self.cache.get(i,(0,''))[1]) if i else ''
                if value:result.append(dict(item,_series_status=value))
                else:result.append({k:v for k,v in item.items() if k!='_series_status'} if '_series_status' in item else item)
            return result
