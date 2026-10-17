"""Visible list feedback and bounded retained row data."""
from urllib.parse import urlsplit,parse_qs
from collections import OrderedDict
from copy import deepcopy
import json
import threading
import time


class RowResultCache:
    """Small session-only cache. Invalidation also rejects in-flight old results."""
    def __init__(self, clock=time.monotonic, max_rows=12, max_bytes=2*1024*1024, ttl=120):
        self.clock=clock;self.max_rows=max_rows;self.max_bytes=max_bytes;self.ttl=ttl
        self.entries=OrderedDict();self.bytes=0;self.revision=0
        self.hits=0;self.misses=0;self.lock=threading.RLock()

    def _prune(self):
        now=self.clock()
        for key in list(self.entries):
            if self.entries[key][0]<=now:
                self.bytes-=self.entries.pop(key)[1]

    def get(self,key):
        with self.lock:
            self._prune()
            if key not in self.entries:self.misses+=1;return None
            self.hits+=1;self.entries.move_to_end(key)
            return deepcopy(self.entries[key][2])

    def put(self,key,files,revision=None,ttl=None):
        if not files or len(files)>80:return False
        try:
            saved=deepcopy(files)
            size=len(json.dumps(saved,ensure_ascii=False).encode('utf-8'))
        except (TypeError,ValueError):return False
        if size>self.max_bytes:return False
        with self.lock:
            if revision is not None and revision!=self.revision:return False
            self._prune()
            if key in self.entries:self.bytes-=self.entries.pop(key)[1]
            self.entries[key]=(self.clock()+(self.ttl if ttl is None else ttl),size,saved)
            self.bytes+=size
            while len(self.entries)>self.max_rows or self.bytes>self.max_bytes:
                self.bytes-=self.entries.popitem(last=False)[1][1]
            return key in self.entries

    def clear(self):
        with self.lock:
            self.revision+=1;self.entries.clear();self.bytes=0

    def stats(self):
        with self.lock:
            self._prune()
            return {'entries':len(self.entries),'bytes':self.bytes,'hits':self.hits,'misses':self.misses}

def provider_page_label(previous,path,current_label,requested_label):
    """A page of the same provider list keeps its heading, in any language."""
    before,after=urlsplit(previous),urlsplit(path)
    old,new=parse_qs(before.query),parse_qs(after.query)
    same_route=(before.scheme,before.netloc,before.path)==(after.scheme,after.netloc,after.path)
    if same_route and ('page' in new or 'bl_start' in new) and any(old.get(k,[default])!=new.get(k,[default]) for k,default in (('page','1'),('bl_start','0'))):
        ignored={'page','bl_start'}
        if before.netloc=='plugin.video.themoviedb.helper':ignored.update(('cacheonly','plugin_category','update_listing','reload'))
        if {k:v for k,v in old.items() if k not in ignored}=={k:v for k,v in new.items() if k not in ignored}:
            return current_label
    return requested_label

def row_message(label,state,search=False):
    if state=='loading':return label+' · Loading…'
    if state=='error' and search:return label+' could not load results. Try another category or search, or use Options → Retry.'
    if state=='error':return label+' could not load. Open title actions to retry, or check its integration in Settings.'
    if state=='empty':return ('No results for '+label+'. Try another search.' if search else label+' · This list returned no titles.')
    return ''

def trim_row_cache(cache,offset,limit=8):
    populated=[n for n,v in cache.items() if v.get('files') is not None]
    keep=set(sorted(populated,key=lambda n:(abs(n-offset),-n))[:max(2,limit)])
    for n in populated:
        if n not in keep:cache[n]['files']=None
