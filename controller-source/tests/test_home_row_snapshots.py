"""Account-owned Home display reuse must stay separate from public discovery."""
import json,stat,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
from test_public_row_snapshots import ITEM,P
H='plugin://plugin.video.themoviedb.helper/?info=trakt_recommendations&tmdb_type=tv&nextpage=true&widget=true'

class HomeSnapshots(unittest.TestCase):
 def store(self,folder,scope='a',clock=lambda:1000):
  from home_rows import HomeRowSnapshots
  return HomeRowSnapshots(Path(folder)/'home.json',scope,clock=clock)
 def test_roundtrip_is_private_bounded_display_only_and_survives_overnight(self):
  from live_core import watch_state
  with tempfile.TemporaryDirectory() as folder:
   s=self.store(folder);self.assertTrue(s.put(H,[ITEM]))
   items=self.store(folder,clock=lambda:1000+12*3600).get(H)
   self.assertEqual(items[0]['title'],ITEM['title']);self.assertEqual(watch_state(items[0])['state'],'unknown')
   raw=s.path.read_text();self.assertNotIn('secret',raw);self.assertNotIn('playcount',raw);self.assertNotIn('resume',raw)
   self.assertEqual(stat.S_IMODE(s.path.stat().st_mode),0o600)
   self.assertIsNone(self.store(folder,'other').get(H));self.assertIsNone(self.store(folder,clock=lambda:1000+86401).get(H))
 def test_only_first_page_recommendations_can_be_retained(self):
  from public_rows import PublicRowSnapshots
  with tempfile.TemporaryDirectory() as folder:
   s=self.store(folder)
   for path in [P,H+'&user=somebody',H+'&page=2',H+'&query=secret',H.replace('trakt_recommendations','trakt_watchlist'),H+'&info=popular']:
    self.assertFalse(s.put(path,[ITEM]),path)
   self.assertFalse(PublicRowSnapshots(Path(folder)/'public.json','a').put(H,[ITEM]))
   self.assertFalse(s.put(H,[dict(ITEM,file='plugin://bad/?token=secret')]))
   self.assertFalse(s.put(H,[ITEM]*41))
   self.assertFalse(s.put(H,[dict(ITEM,plot='x'*300000)]))
 def test_paging_card_is_canonical_and_keeps_navigation_without_breadcrumb_text(self):
  from urllib.parse import urlencode
  path='plugin://plugin.video.themoviedb.helper/?'+urlencode(dict(info='trakt_recommendations',tmdb_type='tv',page=2,widget='true',nextpage='true',cacheonly='FALSE',plugin_category='discard breadcrumb',reload='$INFO[Window(Home).Property(TMDbHelper.Widgets.Reload)]'))
  with tempfile.TemporaryDirectory() as folder:
   s=self.store(folder);self.assertTrue(s.put(H,[ITEM,{'file':path,'filetype':'directory','label':'Next page'}]))
   retained=self.store(folder).get(H);self.assertIn('page=2',retained[-1]['file']);self.assertNotIn('breadcrumb',s.path.read_text())
   self.assertFalse(s.put(H,[dict(ITEM,file=path+'&token=secret')]))
 def test_account_removal_and_late_work_cannot_repopulate(self):
  with tempfile.TemporaryDirectory() as folder:
   s=self.store(folder);s.put(H,[ITEM]);revision=s.revision;s.clear()
   self.assertFalse(s.put(H,[ITEM],revision));self.assertIsNone(self.store(folder).get(H))
 def test_missing_or_expired_authorization_has_no_scope(self):
  from home_rows import home_scope
  token=json.dumps({'access_token':'a','refresh_token':'r','created_at':100,'expires_in':2000})
  self.assertEqual(len(home_scope({},b'identity',token,now=1000)),64)
  self.assertIsNone(home_scope({},b'identity',token,now=2101))
  for value in ('','bad','[]','{}',json.dumps({'access_token':'a'})):
   self.assertIsNone(home_scope({},b'identity',value,now=1000))
  self.assertNotEqual(home_scope({},b'identity',token,now=1000),home_scope({},b'other',token,now=1000))
 def test_home_appears_before_provider_and_hydrates_without_stealing_focus(self):
  from test_snapshot_controller import SnapshotController
  with tempfile.TemporaryDirectory() as folder:
   later=dict(ITEM,file=ITEM['file'].replace('42','43'),title='Fresh title')
   s,calls,controls,queue=SnapshotController().state(folder,lambda path:[later,dict(ITEM,playcount=1)])
   s.section='Home';s.home_snapshot_cache=self.store(folder);s.home_snapshot_cache.put(H,[ITEM]);s.set_rows([{'path':H,'label':'Recommended shows'}])
   self.assertEqual(calls,[]);self.assertEqual(s.rows[0][0]['title'],ITEM['title']);self.assertNotIn('playcount',s.rows[0][0])
   s.focus=105;s.update=lambda item:None;queue.pop(0)()
   self.assertEqual(calls,[H]);self.assertEqual(s.focus,105);self.assertEqual(s.rows[0][0]['playcount'],1)
   s.invalidate_row_results();self.assertIsNone(s.home_snapshot_cache.get(H))

class HomeConfiguration(unittest.TestCase):
 def state(self,folder):
  import ast,io,time
  from types import SimpleNamespace,MethodType
  from public_rows import PublicRowSnapshots,snapshot_scope,helper_settings_identity
  from row_feedback import RowResultCache
  values={'trakt_token':json.dumps({'access_token':'a','refresh_token':'r','created_at':time.time()-10,'expires_in':3600})}
  helper=SimpleNamespace(getAddonInfo=lambda key:folder,getSetting=lambda key:values.get(key,''))
  ns=dict(PublicRowSnapshots=PublicRowSnapshots,snapshot_scope=snapshot_scope,helper_settings_identity=helper_settings_identity,STORE=Path(folder),xbmcaddon=SimpleNamespace(Addon=lambda aid:helper),xbmcvfs=SimpleNamespace(File=lambda path:io.StringIO('<settings><setting id="trakt_token" type="string"/></settings>')))
  source=ast.parse((Path(__file__).parents[1]/'addon/live_review.py').read_text());cls=next(x for x in source.body if isinstance(x,ast.ClassDef) and x.name=='LiveReview')
  names=('configure_row_snapshots','invalidate_row_results');exec(compile(ast.Module(body=[x for x in cls.body if isinstance(x,ast.FunctionDef) and x.name in names],type_ignores=[]),'actual-configuration','exec'),ns)
  state=SimpleNamespace(snapshot_cache=None,config={},result_cache=RowResultCache(),publish_cache_stats=lambda:None)
  for name in names:setattr(state,name,MethodType(ns[name],state))
  return state,values
 def test_native_authorization_roundtrip_then_logout_clears_both_stores(self):
  with tempfile.TemporaryDirectory() as folder:
   s,values=self.state(folder);self.assertTrue(s.configure_row_snapshots());s.home_snapshot_cache.put(H,[ITEM]);s.snapshot_cache.put(P,[ITEM])
   original=s.home_snapshot_cache;self.assertFalse(s.configure_row_snapshots());self.assertIs(s.home_snapshot_cache,original)
   # A new window loads the same account-owned cache, without a provider request.
   new,_=self.state(folder)
   # Match the exact native token, including its timestamp.
   token=values['trakt_token'];new_values=new.configure_row_snapshots.__func__.__globals__['xbmcaddon'].Addon('x')
   new_values.getSetting=lambda key:values.get(key,'')
   self.assertTrue(new.configure_row_snapshots());self.assertIsNotNone(new.home_snapshot_cache.get(H))
   revision=original.revision;values['trakt_token']='';self.assertTrue(s.configure_row_snapshots())
   self.assertIsNone(s.home_snapshot_cache);self.assertFalse(original.put(H,[ITEM],revision=revision));self.assertFalse(original.path.exists())
 def test_native_window_reinitialization_keeps_same_account_home_on_disk(self):
  with tempfile.TemporaryDirectory() as folder:
   s,values=self.state(folder);s.configure_row_snapshots();s.home_snapshot_cache.put(H,[ITEM]);before=s.home_snapshot_cache.path.read_bytes()
   # Kodi recreates controls and onInit resets the public reader before setup.
   s.snapshot_cache=None
   self.assertTrue(s.configure_row_snapshots())
   self.assertIsNotNone(s.home_snapshot_cache.get(H));self.assertEqual(s.home_snapshot_cache.path.read_bytes(),before)
 def test_recreated_window_revokes_retired_writer_without_deleting_display(self):
  with tempfile.TemporaryDirectory() as folder:
   s,values=self.state(folder);s.configure_row_snapshots();old=s.home_snapshot_cache;old.put(H,[ITEM]);revision=old.revision;before=old.path.read_bytes();sanitize=old.sanitize_items
   def recreate(files):
    s.snapshot_cache=None;s.configure_row_snapshots();return sanitize(files)
   old.sanitize_items=recreate
   self.assertFalse(old.put(H,[dict(ITEM,title='Obsolete')],revision=revision))
   self.assertEqual(old.path.read_bytes(),before);self.assertEqual(s.home_snapshot_cache.get(H)[0]['title'],ITEM['title'])
 def test_account_switch_cannot_show_the_previous_account_saved_home(self):
  with tempfile.TemporaryDirectory() as folder:
   s,values=self.state(folder);s.configure_row_snapshots();old=s.home_snapshot_cache;old.put(H,[ITEM]);token=json.loads(values['trakt_token']);token['access_token']='other-account';values['trakt_token']=json.dumps(token)
   self.assertTrue(s.configure_row_snapshots());self.assertIsNone(s.home_snapshot_cache.get(H));self.assertNotEqual(s.home_snapshot_cache.scope,old.scope)

if __name__=='__main__':unittest.main()
