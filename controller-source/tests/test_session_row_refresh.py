import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
from row_feedback import RowResultCache
import test_snapshot_controller as snapshot_fixture
from test_public_row_snapshots import ITEM
P='plugin://plugin.video.themoviedb.helper/?info=trakt_watchlist&tmdb_type=movie'
class SessionRefresh(unittest.TestCase):
 def test_retained_expired_account_row_paints_then_hydrates_without_disk_or_focus_reset(self):
  with tempfile.TemporaryDirectory() as folder:
   now=[1000.];fresh=dict(ITEM,playcount=1,resume={})
   s,calls,controls,queue=snapshot_fixture.SnapshotController().state(folder,lambda path:[fresh]);s.result_cache=RowResultCache(clock=lambda:now[0],retain_stale=300)
   s.result_cache.put(P,[dict(ITEM,playcount=0,resume={'position':20,'total':100})],ttl=30);now[0]+=31
   self.assertIsNone(s.result_cache.get(P));s.set_rows([{'label':'Watchlist','path':P}])
   self.assertEqual(s.rows[0][0]['file'],ITEM['file']);self.assertEqual(calls,[])
   self.assertNotIn('resume',s.rows[0][0]);self.assertNotIn('playcount',s.rows[0][0])
   card=controls[900].items[0];s.focus=900;queue.pop(0)()
   self.assertEqual(calls,[P]);self.assertIs(controls[900].items[0],card);self.assertEqual(card.properties['watchState'],'watched')
   self.assertIsNone(s.snapshot_cache.get(P),'Personal account rows must stay session-only')
 def test_account_invalidation_or_missing_identity_never_reuses_old_session_row(self):
  for missing in (False,True):
   with self.subTest(missing=missing),tempfile.TemporaryDirectory() as folder:
    now=[0.];s,calls,controls,queue=snapshot_fixture.SnapshotController().state(folder,lambda path:[ITEM]);s.result_cache=RowResultCache(clock=lambda:now[0],retain_stale=300);s.result_cache.put(P,[ITEM],ttl=30);now[0]=31
    if missing:s.snapshot_cache=None
    else:s.invalidate_row_results()
    self.assertEqual(s.retained_row_items({'path':P}),(None,False))
 def test_confirmed_empty_account_refresh_is_empty_on_section_revisit(self):
  with tempfile.TemporaryDirectory() as folder:
   now=[0.];s,calls,controls,queue=snapshot_fixture.SnapshotController().state(folder,lambda path:[]);s.result_cache=RowResultCache(clock=lambda:now[0],retain_stale=300)
   s.result_cache.put(P,[ITEM],ttl=30);now[0]=31;definitions=[{'label':'Watchlist','path':P},{'label':'Local','path':'','local_items':[ITEM]}];s.set_rows(definitions);queue.pop(0)()
   s.set_rows(definitions);self.assertEqual(s.rows[0],[]);self.assertEqual(len(calls),1)
 def test_restored_identity_clears_results_fetched_without_proof_for_another_account(self):
  from types import SimpleNamespace,MethodType
  from unittest.mock import Mock
  import test_discovery_controller as fixture
  from public_rows import PublicRowSnapshots
  with tempfile.TemporaryDirectory() as folder:
   now=[0.];s,calls,controls,queue=snapshot_fixture.SnapshotController().state(folder,lambda path:[ITEM]);s.snapshot_cache=None;s.result_cache=RowResultCache(clock=lambda:now[0],retain_stale=300)
   account=['unavailable'];helper=SimpleNamespace(getAddonInfo=lambda key:'owner',getSetting=lambda key:account[0])
   def read_identity(schema,getter):
    if account[0]=='unavailable':raise OSError('settings unavailable')
    return getter('identity')
   ns=fixture.methods(['configure_row_snapshots'],{'xbmcaddon':SimpleNamespace(Addon=lambda aid:helper),'xbmcvfs':SimpleNamespace(File=lambda p:SimpleNamespace(read=lambda:'schema',close=lambda:None)),'helper_settings_identity':read_identity,'snapshot_scope':lambda config,identity:identity,'PublicRowSnapshots':PublicRowSnapshots,'STORE':Path(folder)})
   s.configure_row_snapshots=MethodType(ns['configure_row_snapshots'],s)
   self.assertFalse(s.configure_row_snapshots());s.result_cache.put(P,[dict(ITEM,title='Account A')],ttl=30);now[0]=31
   account[0]='account-B';s.configure_row_snapshots();self.assertEqual(s.snapshot_cache.scope,'account-B')
   self.assertEqual(s.retained_row_items({'path':P}),(None,False))
 def test_stale_rows_share_existing_capacity_and_expire_without_delaying_freshness(self):
  now=[0.];cache=RowResultCache(clock=lambda:now[0],max_rows=1,retain_stale=60)
  cache.put('one',[ITEM],ttl=30);now[0]=31;self.assertIsNone(cache.get('one'));self.assertEqual(cache.get_stale('one'),[ITEM])
  cache.put('two',[ITEM]);self.assertIsNone(cache.get_stale('one'));now[0]=300;self.assertIsNone(cache.get_stale('two'));self.assertEqual(cache.stats()['bytes'],0)
