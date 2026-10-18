"""Preserve the connected YouTube client's personalized video shelf groups."""
import hashlib,re
from copy import deepcopy
from urllib.parse import urlencode,urlsplit,parse_qs
from youtube_core import BASE,video_id
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

def _cursor(listing,visitor=None):
    for entry in listing.get('continuations',[]):
        data=entry.get('nextContinuationData',{})
        token=data.get('continuation')
        if isinstance(token,str) and 0<len(token)<32768:
            return dict(data,visitor=visitor)
    return None

def _tiles(listing):
    items=[];seen=set()
    for entry in listing.get('items',[])[:100]:
        tile=entry.get('tileRenderer',{});command=tile.get('onSelectCommand',{})
        ident=command.get('watchEndpoint',{}).get('videoId','')
        meta=tile.get('metadata',{}).get('tileMetadataRenderer',{});label=_text(meta.get('title',{}))
        thumb=tile.get('header',{}).get('tileHeaderRenderer',{}).get('thumbnail',{}).get('thumbnails',[])
        if isinstance(ident,str) and re.fullmatch(r'[A-Za-z0-9_-]{11}',ident):
            item={'kind':'youtube#video','id':ident,'_partial':True,'snippet':{'title':label,'thumbnails':thumb}}
        else:
            browse=command.get('browseEndpoint',{}).get('browseId','')
            if not isinstance(browse,str) or not re.fullmatch(r'VL[A-Za-z0-9_-]{1,160}',browse):continue
            ident=browse
            item={'id':ident,'file':BASE+'/playlist/'+browse[2:]+'/','filetype':'directory','title':label,'label':label,
                  'art':{'thumb':next((t['url'] for t in reversed(thumb) if isinstance(t,dict) and t.get('url')),'video-addons.png')}}
        if ident not in seen:seen.add(ident);items.append(item)
    return items

def parse_horizontal(payload,visitor=None):
    listing=payload.get('continuationContents',{}).get('horizontalListContinuation',{})
    visitor=payload.get('responseContext',{}).get('visitorData') or visitor
    return _tiles(listing),_cursor(listing,visitor)

def parse_shelves(payload):
    rows=[];visitor=payload.get('responseContext',{}).get('visitorData')
    for section in _sections(payload):
        for entry in section.get('contents',[]):
            shelf=entry.get('shelfRenderer',{});label=_text(shelf.get('headerRenderer',{})) or _text(shelf.get('title',{}))
            content=shelf.get('content',{});listing=content.get('horizontalListRenderer') or content.get('verticalListRenderer') or {}
            items=_tiles(listing)
            if label and items:
                rows.append({'label':label,'items':items,'youtube_cursor':_cursor(listing,visitor)})
            if len(rows)>=MAX_GROUPS:return rows
    return rows

def local_rows(shelves,items):
    rows=[]
    for shelf in shelves:
        videos=[deepcopy(x if x.get('filetype')=='directory' else items[x['id']]) for x in shelf['items'] if x.get('filetype')=='directory' or x['id'] in items]
        if not videos:continue
        key=hashlib.sha256((shelf['label']+'\0'+','.join(x['id'] for x in shelf['items'])).encode()).hexdigest()[:20]
        rows.append({'label':shelf['label'],'path':BASE+'/special/recommendations?'+urlencode({'bl_shelf':key}),'local_items':videos,'youtube_cursor':deepcopy(shelf.get('youtube_cursor')),'youtube_category':True})
    return rows

def merge_shelves(previous,incoming):
    result=deepcopy(previous);by_label={row['label'].casefold():row for row in result}
    for row in incoming:
        key=row['label'].casefold()
        if key in by_label:
            existing=by_label[key];seen={item['id'] for item in existing['items']}
            existing['items'].extend(deepcopy(item) for item in row['items'] if item['id'] not in seen)
            existing['items']=existing['items'][:50]
            # The latest response owns the continuation for this merged shelf.
            if row.get('youtube_cursor'):existing['youtube_cursor']=deepcopy(row['youtube_cursor'])
        elif len(result)<MAX_GROUPS:
            added=deepcopy(row);result.append(added);by_label[key]=added
    return result

def split_page(files,path):
    """Recognize native opaque paging context without accepting unrelated folders."""
    before=urlsplit(path);old=parse_qs(before.query);items=[];cursor=None
    ignored={'page','page_token','click_tracking','visitor','refresh','filtered','%exclude'}
    for item in files:
        after=urlsplit(item.get('file',''));new=parse_qs(after.query)
        same=(before.scheme,before.netloc,before.path.rstrip('/'))==(after.scheme,after.netloc,after.path.rstrip('/'))
        changed=bool(new.get('page_token') and new.get('page_token')!=old.get('page_token'))
        try:changed=changed or int(new.get('page',['1'])[0])>int(old.get('page',['1'])[0])
        except (ValueError,TypeError):pass
        if (item.get('filetype')=='directory' and before.netloc=='plugin.video.youtube' and same and changed
                and {k:v for k,v in old.items() if k not in ignored}=={k:v for k,v in new.items() if k not in ignored}):
            cursor={'path':item['file']}
        elif not item.get('_youtube_more') and not item.get('_page_control'):items.append(item)
    return merge_page([],items,{}),cursor

def merge_page(existing,incoming,counts):
    """Prefer diverse category choices while retaining small real categories."""
    result=deepcopy(existing);seen={video_id(x) or x.get('file') for x in result};fresh=[];overlap=[]
    for item in incoming:
        ident=video_id(item);key=ident or item.get('file')
        if not key or key in seen:continue
        seen.add(key)
        (overlap if ident and counts.get(ident,0)>=2 else fresh).append(deepcopy(item))
    # A soft preference must not empty a finite or playlist-heavy category.
    if len(result)+len(fresh)<5:
        eligible={x.get('file') for x in fresh+overlap[:max(0,5-len(result)-len(fresh))]}
        fresh=[deepcopy(x) for x in incoming if x.get('file') in eligible and not (video_id(x) or x.get('file')) in {video_id(y) or y.get('file') for y in result}]
        unique=[];keys=set()
        for item in fresh:
            key=video_id(item) or item.get('file')
            if key not in keys:keys.add(key);unique.append(item)
        fresh=unique
    return result+fresh
