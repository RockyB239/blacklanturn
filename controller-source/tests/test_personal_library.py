import unittest,copy,tempfile,json
from pathlib import Path
import personal_library as lib

def title(n=1,kind='movie'):
 return {'file':'plugin://plugin.video.themoviedb.helper/?info='+('seasons' if kind=='tv' else 'play')+'&tmdb_type='+kind+'&tmdb_id='+str(n),'label':'Title '+str(n),'filetype':'directory' if kind=='tv' else 'file','type':'tvshow' if kind=='tv' else 'movie','art':{'landscape':'https://image/1.jpg'},'playcount':1}
class PersonalLibrary(unittest.TestCase):
 def test_membership_uses_stable_identity_and_independent_shelves(self):
  original={'Saved':[title(9)],'PrivateExample':'keep'};a=lib.create_collection(original,'Together');b=lib.create_collection(a,'Weekend')
  a_id,b_id=[c['id'] for c in b['PersonalCollections']]
  c=lib.membership(b,a_id,title(),True);c=lib.membership(c,a_id,dict(title(),file=title()['file']+'&widget=true'),True);c=lib.membership(c,b_id,title(),True)
  self.assertEqual([len(x['items']) for x in c['PersonalCollections']],[1,1]);self.assertEqual(original,{'Saved':[title(9)],'PrivateExample':'keep'})
  d=lib.membership(c,a_id,title(),False);self.assertEqual([len(x['items']) for x in d['PersonalCollections']],[0,1]);self.assertEqual(d['Saved'],original['Saved'])
 def test_management_preserves_history_and_collection_identity(self):
  c=lib.create_collection(lib.create_collection({'History':'keep'},'One'),'Two');ident=c['PersonalCollections'][1]['id']
  c=lib.edit_collection(c,ident,'rename','Renamed');c=lib.edit_collection(c,ident,'up')
  self.assertEqual(c['PersonalCollections'][0]['id'],ident)
  c=lib.edit_collection(c,ident,'delete');self.assertEqual([x['name'] for x in c['PersonalCollections']],['One']);self.assertEqual(c['History'],'keep')
 def test_invalid_names_duplicates_bad_data_and_limits_never_modify_original(self):
  for name in ('','  ','a\nb','x'*81):
   with self.assertRaises(ValueError):lib.create_collection({},name)
  c=lib.create_collection({},'One');before=copy.deepcopy(c)
  with self.assertRaises(ValueError):lib.create_collection(c,' one ')
  self.assertEqual(c,before)
  with self.assertRaises(ValueError):lib.create_collection({'PersonalCollections':'bad'},'New')
  with self.assertRaises(ValueError):lib.membership(c,c['PersonalCollections'][0]['id'],{'file':'plugin://evil/play'},True)
 def test_searches_keep_exact_query_kind_and_do_not_change_last_query(self):
  c=lib.save_search({'SearchQuery':'old','Authorizations':'kept'},'Space movies','space','movie')
  c=lib.save_search(c,'Space movies again','space','movie')
  self.assertEqual(len(c['SavedSearches']),1);record=c['SavedSearches'][0]
  self.assertEqual((record['query'],record['kind']),('space','movie'));self.assertEqual(c['SearchQuery'],'old')
  c=lib.edit_search(c,record['id'],'rename','New name');self.assertEqual(c['SavedSearches'][0]['name'],'New name')
  c=lib.edit_search(c,record['id'],'delete');self.assertEqual(c['SavedSearches'],[]);self.assertEqual(c['Authorizations'],'kept')
 def test_my_stuff_rows_are_local_and_keep_metadata(self):
  c=lib.create_collection({},'Family');c=lib.membership(c,c['PersonalCollections'][0]['id'],title(),True)
  rows=lib.collection_rows(c);self.assertEqual(rows[0]['label'],'Family');self.assertEqual(rows[0]['local_items'][0],title())
  rows[0]['local_items'][0]['label']='changed';self.assertEqual(c['PersonalCollections'][0]['items'][0]['label'],'Title 1')
 def test_saved_fields_survive_actual_config_roundtrip(self):
  from live_runtime import read_controller_config,write_controller_config
  c=lib.save_search(lib.create_collection({'PrivateExample':{'keep':True}},'Family'),'Find','space','tv')
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'rows.json';write_controller_config(p,c);self.assertEqual(read_controller_config(p),c)
class LibraryWatchRefresh(unittest.TestCase):
 def test_fresh_watch_state_updates_all_memberships_without_touching_history(self):
  c=lib.create_collection({'Saved':[title()], 'History':'unchanged'},'One');c=lib.membership(c,c['PersonalCollections'][0]['id'],title(),True)
  fresh=dict(title(),playcount=0,resume={'position':30,'total':100})
  after=lib.refresh_watch(c,fresh)
  self.assertEqual(after['Saved'][0]['resume'],{'position':30,'total':100});self.assertEqual(after['PersonalCollections'][0]['items'][0]['playcount'],0);self.assertEqual(c['Saved'][0]['playcount'],1);self.assertEqual(after['History'],'unchanged')
