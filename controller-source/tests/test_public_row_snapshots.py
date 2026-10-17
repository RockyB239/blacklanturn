"""Public disk rows must never revive personal status, credentials or stale work."""
import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
from live_core import watch_state
P='plugin://plugin.video.themoviedb.helper/?info=popular&tmdb_type=movie'
ITEM={'file':'plugin://plugin.video.themoviedb.helper/?info=details&tmdb_type=movie&tmdb_id=42','title':'Public title','playcount':1,'resume':{'position':25,'total':100},'art':{'poster':'https://image.tmdb.org/t/p/w500/poster.jpg'},'token':'secret'}
class PublicSnapshots(unittest.TestCase):
 def module(self):
  spec=importlib.util.find_spec('public_rows')
  self.assertIsNotNone(spec,'Public snapshot storage is not implemented')
  import public_rows
  return public_rows
 def store(self,folder,scope='a',clock=lambda:1000):
  return self.module().PublicRowSnapshots(Path(folder)/'rows.json',scope,clock=clock)
 def test_disk_roundtrip_has_unknown_watch_state_and_only_public_fields(self):
  with tempfile.TemporaryDirectory() as folder:
   s=self.store(folder);self.assertTrue(s.put(P,[ITEM],revision=0))
   item=self.store(folder).get(P)[0]
   self.assertEqual(item['title'],'Public title');self.assertEqual(watch_state(item)['state'],'unknown')
   self.assertNotIn('secret',s.path.read_text());self.assertNotIn('playcount',s.path.read_text());self.assertNotIn('resume',s.path.read_text())
 def test_private_routes_unknown_queries_and_executable_items_are_excluded(self):
  with tempfile.TemporaryDirectory() as folder:
   s=self.store(folder)
   for path in [P+'&token=secret',P+'&user=chris',P+'&query=private',P.replace('popular','trakt_watchlist'),P.replace('popular','search'),P.replace('popular','user_list')]:
    self.assertFalse(s.put(path,[ITEM]));self.assertIsNone(s.get(path))
   for path in ['RunScript(bad)','plugin://other/?info=details',ITEM['file']+'&token=secret',ITEM['file'].replace('details','runscript')]:
    self.assertFalse(s.put(P,[dict(ITEM,file=path)]))
 def test_scope_hash_is_opaque_and_account_or_config_changes_miss(self):
  m=self.module();scope=m.snapshot_scope({'Home':[{'path':P}],'token':'private'},b'account-secret')
  self.assertEqual(len(scope),64);self.assertNotIn('private',scope)
  self.assertNotEqual(scope,m.snapshot_scope({},b'account-secret'));self.assertNotEqual(scope,m.snapshot_scope({'Home':[{'path':P}],'token':'private'},b'new-account'))
  with tempfile.TemporaryDirectory() as folder:
   s=self.store(folder,scope);s.put(P,[ITEM]);self.assertIsNone(self.store(folder,'different').get(P))
 def test_expiry_clock_rollback_corruption_and_oversize_miss_safely(self):
  with tempfile.TemporaryDirectory() as folder:
   s=self.store(folder);s.put(P,[ITEM])
   self.assertIsNone(self.store(folder,clock=lambda:1901).get(P))
   self.assertIsNone(self.store(folder,clock=lambda:999).get(P))
   for payload in ['bad','[]','{"version":1,"scope":"a","rows":null}', 'x'*(2*1024*1024+1)]:
    s.path.write_text(payload);self.assertIsNone(self.store(folder).get(P))
 def test_document_rows_items_and_bytes_are_bounded(self):
  with tempfile.TemporaryDirectory() as folder:
   s=self.store(folder)
   self.assertFalse(s.put(P,[ITEM]*81))
   self.assertFalse(s.put(P,[dict(ITEM,plot='x'*(2*1024*1024))]))
   for n in range(16):self.assertTrue(s.put(P+'&page='+str(n+1),[dict(ITEM,plot='x'*180000)]))
   data=json.loads(s.path.read_text());self.assertLessEqual(len(data['rows']),12);self.assertLessEqual(s.path.stat().st_size,2*1024*1024)
   self.assertIsNone(s.get(P+'&page=1'));self.assertIsNotNone(s.get(P+'&page=16'))
 def test_clear_rejects_late_results_in_memory_and_disk(self):
  with tempfile.TemporaryDirectory() as folder:
   s=self.store(folder);s.put(P,[ITEM]);old=s.revision;s.clear()
   self.assertIsNone(s.get(P));self.assertFalse(s.put(P,[ITEM],revision=old));self.assertIsNone(self.store(folder).get(P))
 def test_failed_atomic_replace_keeps_last_complete_snapshot(self):
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as folder:
   s=self.store(folder);s.put(P,[ITEM]);before=s.path.read_bytes()
   with patch('public_rows.os.replace',side_effect=OSError('full')):
    self.assertFalse(s.put(P,[dict(ITEM,title='Changed')]))
   self.assertEqual(s.path.read_bytes(),before);self.assertEqual(self.store(folder).get(P)[0]['title'],'Public title')

class HelperScope(unittest.TestCase):
 def test_native_settings_values_change_scope_without_profile_file(self):
  import public_rows
  fn=getattr(public_rows,'helper_settings_identity',None)
  self.assertIsNotNone(fn,'Native account settings scope is missing')
  xml='<settings><category><setting id="trakt_token"/><setting id="language"/></category></settings>'
  first=fn(xml,lambda key:{'trakt_token':'secret-one','language':'en'}[key])
  second=fn(xml,lambda key:{'trakt_token':'secret-two','language':'en'}[key])
  self.assertNotEqual(first,second);self.assertNotIn(b'secret',first)
  for schema in ['broken','<settings/>','<settings><setting id="language"/></settings>']:
   with self.assertRaises(ValueError):fn(schema,lambda key:'')

class SnapshotHardening(unittest.TestCase):
 def test_nested_provider_secrets_are_not_written_and_signed_art_is_dropped(self):
  import public_rows
  with tempfile.TemporaryDirectory() as folder:
   s=public_rows.PublicRowSnapshots(Path(folder)/'rows.json','scope')
   item=dict(ITEM,genre=[{'token':'nested-secret'},'Drama'],art={'poster':'https://image.tmdb.org/a?token=art-secret'})
   self.assertTrue(s.put(P,[item]));self.assertNotIn('secret',s.path.read_text())
   self.assertEqual(s.get(P)[0]['genre'],['Drama']);self.assertEqual(s.get(P)[0]['art'],{})
 def test_action_settings_are_not_queried_and_native_api_failures_propagate(self):
  import public_rows
  schema='<settings><setting id="trakt_token" type="string"/><setting id="authenticate_trakt" type="action"/></settings>'
  def read(key):
   if key=='authenticate_trakt':raise AssertionError('Not a stored value')
   return 'secret'
  self.assertEqual(len(public_rows.helper_settings_identity(schema,read)),32)
  with self.assertRaises(RuntimeError):public_rows.helper_settings_identity(schema,lambda key:(_ for _ in ()).throw(RuntimeError('unavailable')))

class FreshEmpty(unittest.TestCase):
 def test_successful_empty_response_removes_previous_disk_titles(self):
  import public_rows
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'rows.json';s=public_rows.PublicRowSnapshots(path,'a');s.put(P,[ITEM])
   self.assertTrue(s.put(P,[]));self.assertIsNone(public_rows.PublicRowSnapshots(path,'a').get(P))

class NativeItemRoutes(unittest.TestCase):
 def test_helper_movie_play_and_widget_reload_roundtrip_with_strict_identity(self):
  import public_rows
  from urllib.parse import urlencode
  path='plugin://plugin.video.themoviedb.helper/?'+urlencode({'info':'play','tmdb_type':'movie','tmdb_id':'42','widget':'true','reload':'$INFO[Window(Home).Property(TMDbHelper.Widgets.Reload)]'})
  with tempfile.TemporaryDirectory() as folder:
   s=public_rows.PublicRowSnapshots(Path(folder)/'rows.json','a')
   self.assertTrue(s.put(P,[dict(ITEM,file=path)]));self.assertEqual(s.get(P)[0]['file'],path)
   for bad in [path+'&player=evil',path.replace('tmdb_id=42','tmdb_id=42%29%2CQuit'),path.replace('tmdb_id=42','missing=42'),path.replace('reload=', 'command=')]:
    self.assertFalse(s.put(P,[dict(ITEM,file=bad)]))

class PublicTraktCharts(unittest.TestCase):
 def test_exact_public_trakt_chart_routes_roundtrip_without_watch_state(self):
  import public_rows
  for info in ('trakt_trending','trakt_popular'):
   for kind in ('movie','tv'):
    with self.subTest(info=info,kind=kind),tempfile.TemporaryDirectory() as folder:
     path='plugin://plugin.video.themoviedb.helper/?info='+info+'&tmdb_type='+kind+'&nextpage=true&widget=true'
     target=Path(folder)/'rows.json';s=public_rows.PublicRowSnapshots(target,'chart-scope')
     self.assertTrue(s.put(path,[ITEM]));fresh=public_rows.PublicRowSnapshots(target,'chart-scope').get(path)
     self.assertEqual(fresh[0]['title'],'Public title');self.assertEqual(watch_state(fresh[0])['state'],'unknown')
 def test_personal_trakt_routes_and_identity_parameters_still_never_persist(self):
  import public_rows
  with tempfile.TemporaryDirectory() as folder:
   s=public_rows.PublicRowSnapshots(Path(folder)/'rows.json','scope')
   for info in ('trakt_recommendations','trakt_watchlist','trakt_collection','trakt_inprogress','trakt_userlist','trakt_userslists','trakt_myairing','trakt_trendinglists','trakt_popularlists','trakt_trending_random','trakt_popular_random'):
    path=P.replace('info=popular','info='+info)
    self.assertFalse(s.put(path,[ITEM]),info);self.assertIsNone(s.get(path))
   for info in ('trakt_trending','trakt_popular'):
    for extra in ('&user=me','&user_slug=private','&list_id=42','&token=secret','&query=private'):
     self.assertFalse(s.put(P.replace('info=popular','info='+info)+extra,[ITEM]),extra)

class PublicPaginationCanonicalization(unittest.TestCase):
 def test_real_chart_shape_retains_twenty_cards_and_usable_next_page_without_display_text(self):
  import public_rows
  from urllib.parse import urlencode,urlsplit,parse_qs
  for kind in ('movie','tv'):
   with self.subTest(kind=kind),tempfile.TemporaryDirectory() as folder:
    path='plugin://plugin.video.themoviedb.helper/?'+urlencode({'info':'trakt_trending','tmdb_type':kind,'nextpage':'true','widget':'true'})
    cards=[dict(ITEM,file=ITEM['file'].replace('tmdb_type=movie','tmdb_type='+kind).replace('tmdb_id=42','tmdb_id='+str(i+1)),title='Public card '+str(i+1),uniqueid={'tmdb':str(i+1)}) for i in range(20)]
    next_params={'info':'trakt_trending','tmdb_type':kind,'nextpage':'true','widget':'true','page':'2','cacheonly':'False','plugin_category':'Public chart display text','reload':'$INFO[Window(Home).Property(TMDbHelper.Widgets.Reload)]'}
    next_item={'file':'plugin://plugin.video.themoviedb.helper/?'+urlencode(next_params),'filetype':'directory','title':'','label':'Next page','episode':-1,'season':-1,'year':0,'runtime':0,'rating':0.0,'art':{}}
    target=Path(folder)/'rows.json';store=public_rows.PublicRowSnapshots(target,'a')
    self.assertTrue(store.put(path,cards+[next_item]));fresh=public_rows.PublicRowSnapshots(target,'a').get(path)
    self.assertEqual(len(fresh),21);self.assertEqual([x['file'] for x in fresh[:20]],[x['file'] for x in cards])
    self.assertEqual([x['uniqueid'] for x in fresh[:20]],[{'tmdb':str(i+1)} for i in range(20)])
    query=parse_qs(urlsplit(fresh[-1]['file']).query);self.assertEqual(query['page'],['2']);self.assertEqual(query['cacheonly'],['false']);self.assertEqual(query['info'],['trakt_trending']);self.assertEqual(query['tmdb_type'],[kind])
    self.assertNotIn('plugin_category',query);self.assertNotIn('Public chart display text',target.read_text());self.assertEqual(json.loads(target.read_text())['rows'][0]['path'],path)
 def test_only_public_pagination_display_fields_are_canonicalized(self):
  import public_rows
  from urllib.parse import urlencode
  base='plugin://plugin.video.themoviedb.helper/?'
  common={'info':'trakt_popular','tmdb_type':'movie','page':'2','cacheonly':'FALSE','plugin_category':'discard me'}
  with tempfile.TemporaryDirectory() as folder:
   store=public_rows.PublicRowSnapshots(Path(folder)/'rows.json','a')
   uri=base+urlencode(common)
   self.assertTrue(store.put(P,[dict(ITEM,file=uri)]))
   for extra in ('&secret=hidden','&user=me','&token=hidden','&cacheonly=true','&plugin_category=repeat','&page=3','&info=popular'):
    self.assertFalse(store.put(P,[dict(ITEM,file=uri+extra)]),extra)
   for bad in [dict(common,cacheonly='invalid'),dict(common,cacheonly=' false '),dict(common,info='trakt_recommendations'),dict(common,info='details',tmdb_id='42'),{k:v for k,v in common.items() if k!='page'}]:
    self.assertFalse(store.put(P,[dict(ITEM,file=base+urlencode(bad))]))
   self.assertFalse(store.put(uri,[ITEM]),'Original row paths must keep strict validation rather than pagination canonicalization')
