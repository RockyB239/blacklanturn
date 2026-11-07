"""Demand-read, bounded public display history; never an account/provider cache.

No persistent connections, preload or worker. DELETE journaling and FULL automatic
vacuum bound the main file; an active rollback journal can temporarily add up to
one main-file-sized transaction. A damaged/unavailable archive is only a miss.
"""
from contextlib import closing
from hashlib import sha256
from pathlib import Path
import json,sqlite3

MAX_ROWS=256
MAX_BYTES=12*1024*1024
MAX_ROW_BYTES=256*1024
MAX_FILE_BYTES=16*1024*1024
MAX_PATH=4096
VERSION=1
APPLICATION_ID=0x424c5253
_SCHEMA='CREATE TABLE rows (path_hash TEXT PRIMARY KEY, scope TEXT NOT NULL, version INTEGER NOT NULL, path TEXT NOT NULL, stamp REAL NOT NULL, payload BLOB NOT NULL, sequence INTEGER NOT NULL) WITHOUT ROWID'

class PublicRowArchive:
    def __init__(self,path,scope,clock):
        self.path=Path(path);self.scope=scope;self.clock=clock

    def _connect(self,write=False):
        if self.path.exists():
            if self.path.stat().st_size>MAX_FILE_BYTES:raise ValueError('Archive physical budget exceeded')
        elif not write:return None
        if write:
            self.path.parent.mkdir(parents=True,exist_ok=True)
            c=sqlite3.connect(str(self.path),timeout=.05)
        else:c=sqlite3.connect(self.path.resolve().as_uri()+'?mode=ro',uri=True,timeout=.05)
        # A fixed instruction ceiling also bounds malformed local databases.
        remaining=[1000]
        def progress():
            remaining[0]-=1
            return remaining[0]<0
        c.set_progress_handler(progress,1000)
        try:
            c.execute('PRAGMA trusted_schema=OFF')
            if write and c.execute('PRAGMA user_version').fetchone()[0]==0:
                if c.execute("SELECT name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'").fetchone():raise ValueError('Unknown archive schema')
                c.execute('PRAGMA page_size=4096');c.execute('PRAGMA auto_vacuum=FULL');c.execute('PRAGMA journal_mode=DELETE')
                c.execute(_SCHEMA);c.execute('PRAGMA application_id='+str(APPLICATION_ID));c.execute('PRAGMA user_version='+str(VERSION));c.commit()
            if c.execute('PRAGMA application_id').fetchone()[0]!=APPLICATION_ID or c.execute('PRAGMA user_version').fetchone()[0]!=VERSION:raise ValueError('Unknown archive format')
            if c.execute('PRAGMA journal_mode').fetchone()[0]!='delete':raise ValueError('Unexpected archive journal')
            if c.execute('PRAGMA auto_vacuum').fetchone()[0]!=1 or c.execute('PRAGMA page_size').fetchone()[0]!=4096:raise ValueError('Unexpected archive layout')
            objects=c.execute("SELECT type,name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'").fetchall()
            if objects!=[('table','rows',_SCHEMA)]:raise ValueError('Unknown archive schema')
            if write:c.execute('PRAGMA max_page_count='+str(MAX_FILE_BYTES//4096))
            return c
        except Exception:
            c.close();raise

    @staticmethod
    def _budget(c):
        count,total,largest=c.execute('SELECT COUNT(*),COALESCE(SUM(length(payload)),0),COALESCE(MAX(length(payload)),0) FROM rows').fetchone()
        return count<=MAX_ROWS and total<=MAX_BYTES and largest<=MAX_ROW_BYTES

    def get(self,path):
        from public_rows import MAX_AGE,public_path,_items,_finite_number
        if not isinstance(path,str) or len(path)>MAX_PATH or not public_path(path):return None
        try:
            c=self._connect()
            if c is None:return None
            with closing(c):
                if not self._budget(c):return None
                row=c.execute('SELECT path,stamp,substr(payload,1,?) FROM rows WHERE path_hash=? AND scope=? AND version=?',(MAX_ROW_BYTES+1,sha256(path.encode()).hexdigest(),self.scope,VERSION)).fetchone()
            if row is None or row[0]!=path or not _finite_number(row[1]) or not 0<=self.clock()-row[1]<=MAX_AGE:return None
            raw=row[2]
            if not isinstance(raw,bytes) or len(raw)>MAX_ROW_BYTES:return None
            data=json.loads(raw)
            if not isinstance(data,dict) or data.get('version')!=VERSION or data.get('scope')!=self.scope or data.get('path')!=path or data.get('time')!=row[1]:return None
            return _items(data.get('items'))
        except (OSError,sqlite3.Error,ValueError,TypeError,OverflowError,RecursionError):return None

    def replace(self,path,items,stamp=None):
        from public_rows import MAX_AGE,public_path,_finite_number
        if not isinstance(path,str) or len(path)>MAX_PATH or not public_path(path):return False
        try:
            now=self.clock()
            if stamp is None:stamp=now
            if not _finite_number(now) or not _finite_number(stamp) or not 0<=now-stamp<=MAX_AGE:return False
            raw=json.dumps({'version':VERSION,'scope':self.scope,'path':path,'time':stamp,'items':items},ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')
            keep=bool(items) and len(raw)<=MAX_ROW_BYTES
            if not keep and not self.path.exists():return True
            c=self._connect(write=True)
            with closing(c),c:
                c.execute('BEGIN IMMEDIATE')
                # A format/size violation cannot be trusted as retained history.
                if not self._budget(c):c.execute('DELETE FROM rows')
                c.execute('DELETE FROM rows WHERE scope<>? OR version<>? OR stamp>? OR stamp<?',(self.scope,VERSION,now,now-MAX_AGE))
                key=sha256(path.encode()).hexdigest();c.execute('DELETE FROM rows WHERE path_hash=?',(key,))
                if keep:
                    sequence=c.execute('SELECT COALESCE(MAX(sequence),0)+1 FROM rows').fetchone()[0]
                    c.execute('INSERT INTO rows VALUES (?,?,?,?,?,?,?)',(key,self.scope,VERSION,path,stamp,raw,sequence))
                while not self._budget(c):c.execute('DELETE FROM rows WHERE path_hash=(SELECT path_hash FROM rows ORDER BY sequence,path_hash LIMIT 1)')
            return True
        except (OSError,sqlite3.Error,ValueError,TypeError,OverflowError,RecursionError):
            # Archive failures never fail an otherwise accepted resident display.
            # Discard on failed replacement so a withdrawn old row cannot return.
            self.clear();return False

    def clear(self):
        # No persistent connection can rewrite a removed DB from this object.
        # Unlink sidecars only for this exact owned basename, never a directory.
        for suffix in ('','-journal','-wal','-shm'):
            try:Path(str(self.path)+suffix).unlink()
            except FileNotFoundError:pass
            except OSError:
                if not suffix:
                    # Directory permissions may forbid unlink while the owned
                    # file is still writable. An invalid header cannot resurrect.
                    try:
                        with self.path.open('wb') as stream:stream.write(b'')
                    except OSError:pass
