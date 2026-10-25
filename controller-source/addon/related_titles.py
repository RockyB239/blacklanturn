"""Choose one provider list for Details; paging stays owned by that list."""
from browse_controls import is_next_page
from live_core import valid_source

def _valid_path(path):
    try:return isinstance(path,str) and valid_source(path)
    except (TypeError,ValueError):return False

def _titles(rows,path):
    if not isinstance(rows,list):return []
    return [item for item in rows if isinstance(item,dict)
            and _valid_path(item.get('file'))
            and not item.get('_page_control') and not is_next_page(item,path)]

def load_related(make_path,provider,kind,identity,valid=lambda:True):
    """Recommendations first, one Similar fallback; never return only controls.

    Preserve successful provider ordering and exact routes/status/artwork. A
    cancelled Details owner cannot launch a fallback or publish stale results.
    """
    if kind not in ('movie','tv') or not str(identity).isdigit() or not valid():return '',[]
    for info in ('recommendations','similar'):
        if not valid():return '',[]
        path=make_path(info,kind,tmdb_id=identity)
        try:rows=provider(path)
        except Exception:rows=[]
        if not valid():return '',[]
        if _titles(rows,path):
            return path,[x for x in rows if isinstance(x,dict) and _valid_path(x.get('file'))]
    return path,[]
