"""Release-order franchise browsing, only on an explicit user request."""
from datetime import date
from title_preferences import title_key
import sqlite3
from pathlib import Path

def helper_database(profile):
    folders=sorted((p for p in Path(profile).glob('database_*') if p.name[9:].isdigit()),key=lambda p:int(p.name[9:]),reverse=True)
    return next((p/'ItemDetails.db' for p in folders if (p/'ItemDetails.db').is_file()),None)

def collection_identity(profile,ident):
    db=helper_database(profile)
    if db is None or not str(ident).isdigit():return None
    try:
        with sqlite3.connect(db.resolve().as_uri()+'?mode=ro',uri=True,timeout=.05) as c:
            row=c.execute('SELECT collection.tmdb_id, collection.title FROM movie JOIN belongs ON belongs.id=movie.id JOIN collection ON collection.id=belongs.parent_id WHERE movie.tmdb_id=?',(ident,)).fetchone()
        return {'id':str(row[0]),'name':row[1] or 'Movie series'} if row and str(row[0]).isdigit() else None
    except (OSError,sqlite3.Error):return None

def _day(item):
    try:return date.fromisoformat(item.get('premiered') or '')
    except (ValueError,TypeError):return None

def release_order(items,today=None):
    today=today or date.today();unique={}
    for item in items:
        key=title_key(item)
        if key and key.startswith('movie:') and key not in unique:unique[key]=item
    def order(item):
        day=_day(item)
        try:year=int(item.get('year') or 0)
        except (ValueError,TypeError):year=0
        return (day.year if day else year if 0<year<10000 else 9999,day.month if day else 12,day.day if day else 31)
    ordered=sorted(unique.values(),key=order)
    nxt=next((x for x in ordered if _day(x) is not None and _day(x)<=today and not x.get('playcount')),None)
    return ordered,nxt

def load_series(path,provider,current):
    from urllib.parse import urlsplit,parse_qs
    from browse_controls import is_next_page
    start=parse_qs(urlsplit(path).query);seen=set();items=[]
    for _ in range(20):
        if not current():return []
        if path in seen:raise ValueError('Movie series pagination repeated; try again later')
        seen.add(path);rows=provider(path)
        if not current():return []
        items.extend(x for x in rows if title_key(x) and title_key(x).startswith('movie:'))
        if len(items)>400:raise ValueError('Movie series exceeds the supported limit')
        controls=[x for x in rows if x.get('filetype')=='directory' and parse_qs(urlsplit(x.get('file','')).query).get('page') and not title_key(x)]
        if not controls:return items
        path=controls[0]['file'];u=urlsplit(path);q=parse_qs(u.query)
        if u.netloc!='plugin.video.themoviedb.helper' or q.get('info')!=start.get('info') or q.get('tmdb_id')!=start.get('tmdb_id'):raise ValueError('Movie series continuation changed identity')
    raise ValueError('Movie series pagination limit reached; no partial order was shown')
