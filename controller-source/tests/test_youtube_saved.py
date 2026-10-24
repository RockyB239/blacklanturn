"""Real disk/SQLite contracts for disposable account-owned YouTube display rows."""
import copy,json,pickle,sqlite3,tempfile,unittest
from pathlib import Path
import youtube_saved as m

def item(n=1):
 return {'file':'plugin://plugin.video.youtube/play/?video_id='+str(n).zfill(11),'filetype':'file','title':'Video '+str(n),'label':'Video '+str(n),'runtime':600,'art':{'thumb':'https://i.ytimg.com/vi/'+str(n).zfill(11)+'/mqdefault.jpg'},'playcount':4,'resume':{'position':90,'total':600},'access_token':'NEVER_SAVE'}
def row():return {'path':'plugin://plugin.video.youtube/special/recommendations','label':'Recommended for you','local_items':[item()],'youtube_cursor':{'path':'plugin://plugin.video.youtube/special/recommendations?page=2&page_token=opaque'}}

class SavedRows(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.path=Path(self.tmp.name)/'saved.json';self.now=1000
  self.store=m.SavedRows(self.path,'account-one',clock=lambda:self.now)
 def test_real_roundtrip_retains_art_and_cursor_but_never_credentials_or_watch_values(self):
  self.assertTrue(self.store.put(row()));loaded=self.store.get();self.assertEqual(loaded[0]['local_items'][0]['art'],item()['art']);self.assertEqual(loaded[0]['youtube_cursor'],row()['youtube_cursor'])
  raw=self.path.read_text();self.assertNotIn('NEVER_SAVE',raw);self.assertNotIn('playcount',raw);self.assertNotIn('resume',raw)
  self.assertEqual(self.path.stat().st_mode&0o777,0o600)
 def test_reopen_and_hits_cannot_renew_age(self):
  self.store.put(row());raw=self.path.read_bytes();self.now+=301
  other=m.SavedRows(self.path,'account-one',clock=lambda:self.now)
  self.assertFalse(other.fresh());self.assertTrue(other.get());self.assertEqual(self.path.read_bytes(),raw)
  self.now+=m.MAX_AGE;self.assertEqual(other.get(),[])
 def test_account_settings_scope_mismatch_rejects_before_display(self):
  self.store.put(row());self.assertEqual(m.SavedRows(self.path,'account-two',clock=lambda:self.now).get(),[])
 def test_empty_or_invalid_update_does_not_replace_last_good_row(self):
  self.store.put(row());raw=self.path.read_bytes();self.assertFalse(self.store.put(dict(row(),local_items=[])));self.assertEqual(self.path.read_bytes(),raw)
  self.assertFalse(self.store.put(dict(row(),path='plugin://evil/run/')))
 def test_corrupt_oversize_future_and_old_schema_fail_closed(self):
  for raw in ('{','x'*(m.MAX_BYTES+1),json.dumps({'version':77}),json.dumps({'version':1,'scope':'account-one','rows':[dict(row(),fetched_at=self.now+60)]})):
   self.path.write_text(raw);self.assertEqual(m.SavedRows(self.path,'account-one',clock=lambda:self.now).get(),[])
 def test_malicious_item_or_cursor_is_not_accepted(self):
  bad=copy.deepcopy(row());bad['local_items'][0]['file']='plugin://evil/play/?video_id=00000000001';self.assertFalse(self.store.put(bad))
  bad=copy.deepcopy(row());bad['youtube_cursor']={'path':'plugin://plugin.video.youtube/special/recommendations?access_token=NEVER_SAVE'};self.assertFalse(self.store.put(bad))
 def test_cursor_seed_index_cannot_exceed_actual_seed_count(self):
  for cursor in ({'related_seeds':['00000000001'],'seed_index':6},{'seed_index':0},{'visitor':'only'}):
   self.assertFalse(self.store.put(dict(row(),youtube_cursor=cursor)))
 def test_native_subscription_folders_keep_display_category_and_bundled_icon(self):
  folder={'file':'plugin://plugin.video.youtube/special/my_subscriptions/shorts/?category_label=Shorts','filetype':'directory','label':'Shorts',
   'art':{'thumb':'/device/addons/plugin.video.youtube/resources/media/shorts.png'}}
  self.assertTrue(self.store.put(dict(row(),local_items=[folder])))
  saved=self.store.get()[0]['local_items'][0];self.assertEqual(saved['file'],folder['file']);self.assertEqual(saved['art'],folder['art'])
 def test_native_optional_visitor_and_unknown_duration_are_display_safe(self):
  data=dict(row(),local_items=[dict(item(),runtime=-1)],youtube_cursor={'continuation':'opaque','visitor':None,'clickTrackingParams':'tracking'})
  self.assertTrue(self.store.put(data));saved=self.store.get()[0]
  self.assertEqual(saved['local_items'][0]['runtime'],0);self.assertNotIn('visitor',saved['youtube_cursor']);self.assertEqual(saved['youtube_cursor']['continuation'],'opaque')
 def test_bounds_and_retirement_are_enforced(self):
  for n in range(m.MAX_ROWS+5):self.store.put(dict(row(),path=row()['path']+'?bl_shelf='+str(n)))
  self.assertLessEqual(len(self.store.get()),m.MAX_ROWS);self.assertLessEqual(self.path.stat().st_size,m.MAX_BYTES)
  self.store.clear();self.assertEqual(self.store.get(),[]);self.assertFalse(self.path.exists())

class CurrentHistory(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.path=Path(self.tmp.name)/'history.sqlite'
  with sqlite3.connect(self.path) as c:c.execute('CREATE TABLE storage_v2 (key TEXT PRIMARY KEY, timestamp REAL, value BLOB, size INTEGER)')
 def write(self,data):
  raw=pickle.dumps(data,protocol=2)
  with sqlite3.connect(self.path) as c:c.execute('INSERT OR REPLACE INTO storage_v2 VALUES (?,?,?,?)',('00000000001',1,raw,len(raw)))
 def test_each_reuse_reads_current_watch_and_resume_without_changing_database(self):
  self.write({'play_count':1,'played_time':71});before=self.path.read_bytes();files=[item()];original=copy.deepcopy(files)
  actual=m.current_watch(files,self.path);self.assertEqual(actual[0]['playcount'],1);self.assertEqual(actual[0]['resume']['position'],71);self.assertEqual(actual[0]['art'],files[0]['art']);self.assertEqual(files,original);self.assertEqual(self.path.read_bytes(),before)
  self.write({'play_count':2,'played_time':0});self.assertEqual(m.current_watch(files,self.path)[0]['playcount'],2)
  with sqlite3.connect(self.path) as c:c.execute('DELETE FROM storage_v2')
  fresh=m.current_watch(files,self.path);self.assertEqual(fresh[0]['playcount'],0);self.assertEqual(fresh[0]['resume']['position'],0)
 def test_disabled_or_absent_local_history_does_not_reuse_old_watch_values(self):
  fresh=m.current_watch([item()],self.path,enabled=False);self.assertEqual(fresh[0]['playcount'],0)
  self.assertEqual(m.current_watch([item()],self.path.with_name('absent.sqlite'))[0]['resume']['position'],0)
  self.assertFalse(self.path.with_name('absent.sqlite').exists())
 def test_unknown_schema_or_pickle_globals_fail_closed_without_execution(self):
  with sqlite3.connect(self.path) as c:c.execute('DROP TABLE storage_v2')
  with self.assertRaises(m.HistoryUnavailable):m.current_watch([item()],self.path)
  with sqlite3.connect(self.path) as c:
   c.execute('CREATE TABLE storage_v2 (key TEXT,value BLOB)');c.execute('INSERT INTO storage_v2 VALUES (?,?)',('00000000001',b'cos\nsystem\n.'))
  with self.assertRaises(m.HistoryUnavailable):m.current_watch([item()],self.path)
 def test_wal_updates_are_visible_without_checkpointing_personal_history(self):
  c=sqlite3.connect(self.path);self.addCleanup(c.close);c.execute('PRAGMA journal_mode=WAL')
  raw=pickle.dumps({'play_count':3,'played_time':12});c.execute('INSERT INTO storage_v2 VALUES (?,?,?,?)',('00000000001',1,raw,len(raw)));c.commit()
  self.assertEqual(m.current_watch([item()],self.path)[0]['playcount'],3)
