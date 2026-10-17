"""Optional read-only enrichment from TMDbHelper's public video metadata cache.

Kodi directory JSON omits the video's language. Cache schema is checked before
reading; unavailable or changed caches leave the normal candidate fallback intact.
No account tables, keys, network requests or database writes are used here.
"""
from pathlib import Path
import re,sqlite3

def cached_video_metadata(helper_profile,identity):
    if not identity or len(identity)!=2 or identity[0] not in ('movie','tv') or not str(identity[1]).isdigit():return {}
    root=Path(helper_profile)
    directories=[p for p in root.glob('database_*') if re.fullmatch(r'database_\d+',p.name)]
    directories.sort(key=lambda p:int(p.name.split('_')[-1]),reverse=True)
    for folder in directories:
        db=folder/'ItemDetails.db'
        if not db.is_file():continue
        try:
            with sqlite3.connect(db.resolve().as_uri()+'?mode=ro',uri=True,timeout=.25) as connection:
                columns={r[1] for r in connection.execute('PRAGMA table_info(video)')}
                if not {'parent_id','key','name','iso_language','content'}<=columns:continue
                rows=connection.execute('SELECT key,name,iso_language,content FROM video WHERE parent_id=?',(identity[0]+'.'+str(identity[1]),)).fetchall()
                return {key:{'name':name or '', 'language':language or '', 'type':kind or ''} for key,name,language,kind in rows if key}
        except (OSError,sqlite3.Error):continue
    return {}

def cached_title_aliases(helper_profile,identity):
    """Read localized/original names only for the exact selected public title."""
    if not identity or len(identity)!=2 or identity[0] not in ('movie','tv') or not str(identity[1]).isdigit():return []
    table='tvshow' if identity[0]=='tv' else 'movie'
    directories=sorted((p for p in Path(helper_profile).glob('database_*') if re.fullmatch(r'database_\d+',p.name)),key=lambda p:int(p.name.split('_')[-1]),reverse=True)
    for folder in directories:
        db=folder/'ItemDetails.db'
        if not db.is_file():continue
        try:
            with sqlite3.connect(db.resolve().as_uri()+'?mode=ro',uri=True,timeout=.25) as connection:
                columns={r[1] for r in connection.execute('PRAGMA table_info('+table+')')}
                if not {'id','title','originaltitle'}<=columns:continue
                row=connection.execute('SELECT title,originaltitle FROM '+table+' WHERE id=?',(identity[0]+'.'+str(identity[1]),)).fetchone()
                return list(dict.fromkeys(value for value in (row or ()) if isinstance(value,str) and value.strip()))
        except (OSError,sqlite3.Error):continue
    return []
