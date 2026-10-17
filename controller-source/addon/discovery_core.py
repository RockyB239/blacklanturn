"""Owner-configured discovery pages, with lossless legacy migration."""
from copy import deepcopy
from hashlib import sha256
from live_core import valid_source

def migrate_pages(config):
    result=deepcopy(config)
    for group in ('Genres','Categories'):
        for index,page in enumerate(result.setdefault(group,[])):
            page.setdefault('id',sha256((group+str(index)+page.get('label','')+page.get('section','Both')).encode()).hexdigest()[:16])
            page.setdefault('section','Both');page.setdefault('enabled',True)
            if 'rows' not in page:
                page['rows']=[{'label':page.get('label','List'),'path':page['path'],'enabled':True}] if valid_source(page.get('path','')) else []
            for row in page['rows']:row.setdefault('enabled',True)
    result['DiscoverySchema']=2
    return result

def collection_pages(config,section):
    return [page for group in ('Genres','Categories') for page in config.get(group,[])
            if page.get('enabled',True) and page.get('section','Both') in (section,'Both')]

def page_rows(config,section,page_id=None):
    if page_id is None:rows=config.get(section,[])
    else:
        page=next((p for p in collection_pages(config,section) if p.get('id')==page_id),None)
        rows=page.get('rows',[]) if page else []
    return [r for r in rows if r.get('enabled',True) and valid_source(r.get('path',''))]

def window_shift(offset,slot,direction,count):
    """Two native shelf controls display an arbitrary ordered row collection."""
    if direction>0 and slot==1 and offset+2<count:return offset+1
    if direction<0 and slot==0 and offset>0:return offset-1
    return None
