"""Fit verified YouTube thumbnail variants without touching playback state."""
from copy import deepcopy
from urllib.parse import urlsplit
from youtube_core import video_id

def fit_cards(files,metadata):
    if not isinstance(metadata,dict):metadata={}
    result=deepcopy(files)
    for item in result:
        ident=video_id(item)
        if not ident:continue
        entry=metadata.get(ident);entry=entry if isinstance(entry,dict) else {}
        snippet=entry.get('snippet');snippet=snippet if isinstance(snippet,dict) else {}
        thumbnails=snippet.get('thumbnails',{})
        values=thumbnails.values() if isinstance(thumbnails,dict) else thumbnails or []
        candidates=[]
        for image in values:
            if not isinstance(image,dict) or image.get('unverified'):continue
            try:w=float(image.get('width',0));h=float(image.get('height',0))
            except (TypeError,ValueError):continue
            if h>0 and w>=320 and abs(w/h-16/9)<.04 and image.get('url'):candidates.append((w*h,image['url']))
        # Medium is YouTube's standard unpadded 16:9 fallback. Prefer a verified
        # max-resolution variant from the provider's cached metadata when present.
        image=max(candidates)[1] if candidates else 'https://i.ytimg.com/vi/'+ident+'/mqdefault.jpg'
        # Older cached API metadata can advertise retired fhd/uhd filenames.
        # The standard max-resolution endpoint has a working unpadded fallback.
        if urlsplit(image).path.rsplit('/',1)[-1] in ('fhddefault.jpg','uhddefault.jpg'):
            image='https://i.ytimg.com/vi/'+ident+'/maxresdefault.jpg'
        item['art']=dict(item.get('art') or {},thumb=image,youtubefallback='https://i.ytimg.com/vi/'+ident+'/mqdefault.jpg');item['thumbnail']=image
    return result

def cached_fit_cards(files):
    # These standard endpoints avoid stale provider filenames and an extra
    # account context/database per directory. Kodi handles the lower resolution
    # fallback when maxres is unavailable; no per-thumbnail network probe.
    metadata={ident:{'snippet':{'thumbnails':{'maxres':{
        'url':'https://i.ytimg.com/vi/'+ident+'/maxresdefault.jpg',
        'width':1280,'height':720}}}} for ident in (video_id(item) for item in files) if ident}
    return fit_cards(files,metadata)
