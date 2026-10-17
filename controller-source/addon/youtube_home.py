"""Preserve the connected YouTube client's personalized video shelf groups."""
import hashlib,re
from copy import deepcopy
from urllib.parse import urlencode
from youtube_core import BASE
MAX_GROUPS=16

def _text(value):
    if not isinstance(value,dict):return ''
    if isinstance(value.get('simpleText'),str):return value['simpleText']
    if isinstance(value.get('runs'),list):return ''.join(x.get('text','') for x in value['runs'] if isinstance(x,dict))
    return next((s for s in (_text(v) for v in value.values()) if s),'')

def _sections(payload):
    if not isinstance(payload,dict):return
    for key,value in payload.items():
        if key in ('sectionListRenderer','sectionListContinuation') and isinstance(value,dict):yield value
        elif isinstance(value,dict):yield from _sections(value)

def section_continuation(payload):
    for section in _sections(payload):
        for entry in section.get('continuations',[]):
            data=entry.get('nextContinuationData',{})
            if isinstance(data.get('continuation'),str) and len(data['continuation'])<32768:return data
    return {}

def parse_shelves(payload):
    rows=[]
    for section in _sections(payload):
        for entry in section.get('contents',[]):
            shelf=entry.get('shelfRenderer',{});label=_text(shelf.get('headerRenderer',{})) or _text(shelf.get('title',{}))
            content=shelf.get('content',{});listing=content.get('horizontalListRenderer') or content.get('verticalListRenderer') or {}
            items=[];seen=set()
            for entry in listing.get('items',[])[:100]:
                tile=entry.get('tileRenderer',{});ident=tile.get('onSelectCommand',{}).get('watchEndpoint',{}).get('videoId','')
                if not isinstance(ident,str) or not re.fullmatch(r'[A-Za-z0-9_-]{11}',ident) or ident in seen:continue
                seen.add(ident);meta=tile.get('metadata',{}).get('tileMetadataRenderer',{})
                thumb=tile.get('header',{}).get('tileHeaderRenderer',{}).get('thumbnail',{}).get('thumbnails',[])
                items.append({'kind':'youtube#video','id':ident,'_partial':True,'snippet':{'title':_text(meta.get('title',{})),'thumbnails':thumb}})
            if label and items:
                rows.append({'label':label,'items':items})
            if len(rows)>=MAX_GROUPS:return rows
    return rows

def local_rows(shelves,items):
    rows=[]
    for shelf in shelves:
        videos=[deepcopy(items[x['id']]) for x in shelf['items'] if x['id'] in items]
        if not videos:continue
        key=hashlib.sha256((shelf['label']+'\0'+','.join(x['id'] for x in shelf['items'])).encode()).hexdigest()[:20]
        rows.append({'label':shelf['label'],'path':BASE+'/special/recommendations?'+urlencode({'bl_shelf':key}),'local_items':videos})
    return rows

def merge_shelves(previous,incoming):
    result=deepcopy(previous);by_label={row['label'].casefold():row for row in result}
    for row in incoming:
        key=row['label'].casefold()
        if key in by_label:
            existing=by_label[key];seen={item['id'] for item in existing['items']}
            existing['items'].extend(deepcopy(item) for item in row['items'] if item['id'] not in seen)
            existing['items']=existing['items'][:50]
        elif len(result)<MAX_GROUPS:
            added=deepcopy(row);result.append(added);by_label[key]=added
    return result
