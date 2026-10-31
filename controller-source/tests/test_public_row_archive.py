"""Demand-read public displays survive resident eviction without retaining accounts."""
import json,sqlite3,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
from public_rows import PublicRowSnapshots,public_path
from home_rows import HomeRowSnapshots
P='plugin://plugin.video.themoviedb.helper/?info=popular&tmdb_type=movie'
ITEM={'file':'plugin://plugin.video.themoviedb.helper/?info=details&tmdb_type=movie&tmdb_id=42','title':'Public title','resume':{'position':42},'token':'secret'}
class ArchiveTests(unittest.TestCase):
 def store(self,folder,**kw):
  import inspect
  self.assertIn('archive',inspect.signature(PublicRowSnapshots).parameters,'Optional archive support is missing')
  return PublicRowSnapshots(Path(folder)/'rows.json','scope',clock=kw.pop('clock',lambda:1000),archive=True,**kw)
 def database(self,folder):return Path(folder)/'rows.archive.sqlite3'
 def test_public_display_survives_resident_eviction_and_restart_without_loading_archive(self):
  with tempfile.TemporaryDirectory() as f:
   s=self.store(f)
   for n in range(55):self.assertTrue(s.put(P+'&page='+str(n+1),[dict(ITEM,title=str(n))]))
   reopened=self.store(f);self.assertLessEqual(len(reopened.rows),48)
   before=len(reopened.rows);self.assertEqual(reopened.get(P+'&page=1')[0]['title'],'0');self.assertEqual(len(reopened.rows),before)
   self.assertNotIn(b'secret',self.database(f).read_bytes());self.assertNotIn('resume',str(reopened.get(P+'&page=1')))
 def test_opt_in_is_lazy_and_private_subclass_cannot_enable_archive(self):
  with tempfile.TemporaryDirectory() as f:
   s=self.store(f);self.assertFalse(self.database(f).exists());self.assertIsNone(s.get(P));self.assertFalse(self.database(f).exists())
   private=HomeRowSnapshots(Path(f)/'private.json','scope',archive=True)
   private.put('plugin://plugin.video.themoviedb.helper/?info=trakt_recommendations&tmdb_type=movie',[ITEM])
   self.assertFalse((Path(f)/'private.archive.sqlite3').exists())
 def test_count_and_payload_pressure_evict_oldest_rows(self):
  with tempfile.TemporaryDirectory() as f:
   s=self.store(f)
   with s.batch():
    for n in range(258):s.put(P+'&page='+str(n+1),[ITEM])
   self.assertIsNone(s.get(P+'&page=1'));self.assertIsNotNone(s.get(P+'&page=258'))
   with sqlite3.connect(self.database(f)) as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM rows').fetchone()[0],256)
  with tempfile.TemporaryDirectory() as f:
   s=self.store(f)
   with s.batch():
    for n in range(65):s.put(P+'&page='+str(n+1),[dict(ITEM,plot='x'*240000)])
   self.assertIsNone(s.get(P+'&page=1'));self.assertIsNotNone(s.get(P+'&page=65'))
   with sqlite3.connect(self.database(f)) as c:self.assertLessEqual(c.execute('SELECT SUM(length(payload)) FROM rows').fetchone()[0],12*1024*1024)
   self.assertLessEqual(self.database(f).stat().st_size,16*1024*1024)
 def test_empty_and_oversized_replacement_cannot_revive_old_archive(self):
  with tempfile.TemporaryDirectory() as f:
   s=self.store(f);s.put(P,[ITEM]);self.assertTrue(s.put(P,[]));self.assertIsNone(self.store(f).get(P))
   s.put(P,[ITEM]);self.assertTrue(s.put(P,[dict(ITEM,title='Larger',plot='x'*300000)]))
   s.path.unlink();self.assertIsNone(self.store(f).get(P))
 def test_clear_rejects_late_batch_writes_and_archive_cannot_resurface(self):
  with tempfile.TemporaryDirectory() as f:
   s=self.store(f)
   with s.batch():
    s.put(P,[ITEM]);old=s.revision;s.clear();self.assertFalse(s.put(P,[ITEM],revision=old))
   self.assertIsNone(self.store(f).get(P));self.assertFalse(self.database(f).exists())
 def test_scope_expiry_rollback_and_corruption_are_misses(self):
  with tempfile.TemporaryDirectory() as f:
   s=self.store(f);s.put(P,[ITEM]);s.path.unlink()
   self.assertIsNone(PublicRowSnapshots(s.path,'new',clock=lambda:1000,archive=True).get(P))
   self.assertIsNone(self.store(f,clock=lambda:87401).get(P));self.assertIsNone(self.store(f,clock=lambda:999).get(P))
   self.database(f).write_bytes(b'invalid sqlite');self.assertIsNone(self.store(f).get(P))
 def test_tampered_path_status_and_oversized_blob_fail_closed(self):
  with tempfile.TemporaryDirectory() as f:
   s=self.store(f);s.put(P,[ITEM]);s.path.unlink()
   with sqlite3.connect(self.database(f)) as c:
    payload=c.execute('SELECT payload FROM rows').fetchone()[0];d=json.loads(payload);d['path']=P+'&user=me';c.execute('UPDATE rows SET payload=?',(json.dumps(d).encode(),))
   self.assertIsNone(self.store(f).get(P))
   s.put(P,[ITEM]);s.path.unlink()
   with sqlite3.connect(self.database(f)) as c:c.execute('UPDATE rows SET payload=?',(b'x'*(256*1024+1),))
   self.assertIsNone(self.store(f).get(P))
 def test_private_route_and_unknown_query_never_create_archive(self):
  with tempfile.TemporaryDirectory() as f:
   s=self.store(f)
   for path in (P+'&token=secret',P.replace('popular','trakt_watchlist'),P.replace('popular','trakt_recommendations')):self.assertFalse(s.put(path,[ITEM]));self.assertIsNone(s.get(path))
   self.assertFalse(self.database(f).exists())
 def test_locked_archive_read_is_short_miss_and_clear_removes_it(self):
  import time
  with tempfile.TemporaryDirectory() as f:
   s=self.store(f);s.put(P,[ITEM]);s.path.unlink()
   with sqlite3.connect(self.database(f)) as c:
    c.execute('BEGIN EXCLUSIVE');start=time.monotonic();self.assertIsNone(self.store(f).get(P));self.assertLess(time.monotonic()-start,.5)
   s.clear();self.assertIsNone(self.store(f).get(P))

 def test_oversized_resident_replacement_also_withdraws_old_archive(self):
  with tempfile.TemporaryDirectory() as f:
   s=self.store(f);s.put(P,[ITEM]);self.assertFalse(s.put(P,[dict(ITEM,plot='x'*(2*1024*1024+1))]))
   s.path.unlink();self.assertIsNone(self.store(f).get(P))
 def test_clear_can_invalidate_database_when_directory_unlink_fails(self):
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as f:
   s=self.store(f);s.put(P,[ITEM]);database=self.database(f);original=Path.unlink
   def unlink(path,*args,**kw):
    if path==database:raise PermissionError('directory readonly')
    return original(path,*args,**kw)
   with patch.object(Path,'unlink',unlink):s.clear()
   self.assertIsNone(self.store(f).get(P))
 def test_archive_read_does_not_modify_database_or_admit_tampered_metadata(self):
  with tempfile.TemporaryDirectory() as f:
   s=self.store(f);s.put(P,[ITEM]);s.path.unlink();database=self.database(f);stamp=database.stat().st_mtime_ns
   self.assertEqual(self.store(f).get(P)[0]['title'],'Public title');self.assertEqual(database.stat().st_mtime_ns,stamp)
   for column,value in (('scope','other'),('version',99),('path',P+'&page=2'),('stamp',float('inf'))):
    s.put(P,[ITEM]);s.path.unlink()
    with sqlite3.connect(database) as c:c.execute('UPDATE rows SET '+column+'=?',(value,))
    self.assertIsNone(self.store(f).get(P),column)
 def test_physical_and_total_metadata_budget_violations_miss(self):
  with tempfile.TemporaryDirectory() as f:
   s=self.store(f);s.put(P,[ITEM]);s.path.unlink()
   with sqlite3.connect(self.database(f)) as c:
    row=c.execute('SELECT * FROM rows').fetchone()
    for n in range(256):c.execute('INSERT INTO rows VALUES (?,?,?,?,?,?,?)',('extra'+str(n),)+row[1:])
   self.assertIsNone(self.store(f).get(P))
   with self.database(f).open('r+b') as stream:stream.truncate(16*1024*1024+1)
   self.assertIsNone(self.store(f).get(P))

class LegacyResidentRetention(unittest.TestCase):
 def test_row_count_eviction_archives_legacy_display_without_extending_original_age(self):
  with tempfile.TemporaryDirectory() as f:
   target=Path(f)/'rows.json';legacy=PublicRowSnapshots(target,'scope',clock=lambda:1000)
   for n in range(3):legacy.put(P+'&page='+str(n+1),[dict(ITEM,title='Legacy '+str(n+1))])
   upgraded=PublicRowSnapshots(target,'scope',clock=lambda:1500,archive=True);upgraded.max_rows=2
   self.assertFalse(target.with_name('rows.archive.sqlite3').exists())
   self.assertTrue(upgraded.put(P+'&page=4',[dict(ITEM,title='New display')]))
   reloaded=PublicRowSnapshots(target,'scope',clock=lambda:1500,archive=True)
   retained=reloaded.get(P+'&page=1');self.assertIsNotNone(retained,'Legacy row was lost on row-count eviction')
   self.assertEqual(retained[0]['title'],'Legacy 1')
   with sqlite3.connect(target.with_name('rows.archive.sqlite3')) as c:
    old=c.execute('SELECT stamp,payload FROM rows WHERE path=?',(P+'&page=1',)).fetchone()
   self.assertEqual(old[0],1000);self.assertEqual(json.loads(old[1])['time'],1000)
   later=PublicRowSnapshots(target,'scope',clock=lambda:87401,archive=True)
   self.assertIsNone(later.get(P+'&page=1'));self.assertEqual(later.get(P+'&page=4')[0]['title'],'New display')
 def test_byte_eviction_retains_legacy_display_without_archive_access_on_reads(self):
  with tempfile.TemporaryDirectory() as f:
   target=Path(f)/'rows.json';legacy=PublicRowSnapshots(target,'scope',clock=lambda:1000)
   legacy.put(P+'&page=1',[dict(ITEM,title='Legacy bytes',plot='x'*40000)])
   upgraded=PublicRowSnapshots(target,'scope',clock=lambda:1500,archive=True)
   self.assertEqual(upgraded.get(P+'&page=1')[0]['title'],'Legacy bytes')
   self.assertFalse(target.with_name('rows.archive.sqlite3').exists())
   upgraded.max_bytes=65536;self.assertTrue(upgraded.put(P+'&page=2',[dict(ITEM,plot='y'*40000)]))
   fresh=PublicRowSnapshots(target,'scope',clock=lambda:1500,archive=True)
   retained=fresh.get(P+'&page=1');self.assertIsNotNone(retained,'Legacy row was lost on byte-pressure eviction')
   self.assertEqual(retained[0]['title'],'Legacy bytes')
   self.assertNotIn(P+'&page=1',fresh.rows)

class InternationalTests(unittest.TestCase):
 def test_country_and_year_chart_filters_keep_lossless_next_page(self):
  from urllib.parse import urlencode,parse_qs,urlsplit
  from browse_controls import is_next_page
  for kind in ('movie','tv'):
   for countries,years in (('gb,kr,jp,fr,es,de,in,se,no,dk,fi,is,mx,it,br,hk,cn,tw,au,ca','2021-2026'),('dk,no,se,fi,is',None),('mx,br,ar,cl,co,pe,uy',None),('gb,fr','1900-1999')):
    q={'info':'trakt_popular','tmdb_type':kind,'nextpage':'true','widget':'true','countries':countries}
    if years:q['years']=years
    path='plugin://plugin.video.themoviedb.helper/?'+urlencode(q)
    nxt='plugin://plugin.video.themoviedb.helper/?'+urlencode(dict(q,page=2,cacheonly='False',plugin_category='display only'))
    with tempfile.TemporaryDirectory() as f:
     s=PublicRowSnapshots(Path(f)/'rows.json','scope');self.assertTrue(s.put(path,[ITEM,{'file':nxt,'filetype':'directory','label':'Next'}]))
     result=PublicRowSnapshots(s.path,'scope').get(path);self.assertTrue(is_next_page(result[-1],path));self.assertNotIn('plugin_category',parse_qs(urlsplit(result[-1]['file']).query))
 def test_country_and_year_filters_do_not_admit_private_or_unbounded_parameters(self):
  for suffix in ('countries=GB','countries=gb,,fr','countries=gb;fr','countries='+','.join(['gb']*33),'countries=gb&years=0','countries=gb&years=2026-1900','countries=gb&years=99999','countries=gb&years=2021-2026&user=me','countries=gb&countries=fr','years=2021-2026&query=secret'):
   self.assertFalse(public_path(P.replace('popular','trakt_popular')+'&'+suffix),suffix)
  self.assertFalse(public_path(P+'&countries=gb'));self.assertFalse(public_path(P.replace('popular','trakt_trending')+'&countries=gb'))
