"""Read visible local-shelf status from Helper's existing sync cache; no sync/network."""
from copy import deepcopy
import sqlite3,math
from title_preferences import title_key
from movie_series import helper_database

def hydrate_local(profile,items):
    db=helper_database(profile);result=deepcopy(items)
    if db is None:return result
    keys={key:key.replace(':','.',1) for key in (title_key(x) for x in result) if key}
    if not keys:return result
    data={}
    try:
        with sqlite3.connect(db.resolve().as_uri()+'?mode=ro',uri=True,timeout=.03) as c:
            ids=list(keys.values())
            for start in range(0,len(ids),128):
                batch=ids[start:start+128];marks=','.join('?' for _ in batch)
                data.update((row[0],row[1:]) for row in c.execute('SELECT id,plays,aired_episodes,watched_episodes,playback_progress FROM simplecache WHERE id IN ('+marks+')',batch))
    except (OSError,sqlite3.Error):return result
    for item in result:
        key=title_key(item);state=data.get(keys.get(key))
        if state is None:continue
        plays,aired,watched,progress=state
        try:
            if key.startswith('tv:'):
                if aired is not None and aired>0 and watched is not None:item['playcount']=int(watched>=aired)
                continue
            if plays is not None:item['playcount']=max(0,int(plays))
            total=float(item.get('runtime') or (item.get('resume') or {}).get('total') or 0)
            percent=float(progress or 0)
            if not math.isfinite(total) or not math.isfinite(percent):continue
            position=total*percent/100 if 4<=percent<=96 and total>0 and not item.get('playcount') else 0
            item['resume']={'position':position,'total':total if position else 0}
        except (TypeError,ValueError,OverflowError):continue
    return result
