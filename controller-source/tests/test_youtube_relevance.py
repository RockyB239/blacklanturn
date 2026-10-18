"""Category shelves admit positive native taxonomy, preserving valid cards and cursors."""
import copy,unittest
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch
import youtube_home as home,youtube_provider as provider
from youtube_core import BASE
from test_youtube_home import response,shelf
try:import youtube_relevance as relevance
except ModuleNotFoundError:relevance=None

def ident(n):return 'v'+str(n).zfill(10)
def video(n):return {'file':BASE+'/play/?video_id='+ident(n),'title':'Original','art':{'thumb':'original.jpg'},'playcount':1,'resume':{'position':20,'total':90}}
def metadata(n,category='10',topics=()):return {'id':ident(n),'snippet':{'categoryId':category},'topicDetails':{'topicCategories':['https://en.wikipedia.org/wiki/'+t for t in topics]}}
def entry(n):return {'kind':'youtube#video','id':ident(n)}

class Relevance(unittest.TestCase):
 def api(self):self.assertIsNotNone(relevance,'No category taxonomy policy');return relevance
 def test_conservative_families_leave_mixed_and_coarse_interests_unchanged(self):
  p=self.api()
  for label,want in [('Start a Music Mix','music'),('Guitar and more','music'),('Pop Music','music'),('Clash of Clans','gaming'),('MOBA games','gaming'),('Basketball','sports'),('History',None),('Science',None),('New to you',None),('Game shows',None)]:
   with self.subTest(label=label):self.assertEqual(p.family(label),want)
 def test_music_rejects_politics_philosophy_but_accepts_music_under_entertainment(self):
  p=self.api();self.assertTrue(p.matches(metadata(1),'music'));self.assertTrue(p.matches(metadata(2,'24',['Rock_music']),'music'))
  self.assertFalse(p.matches(metadata(3,'25',['Politics','Society']),'music'));self.assertFalse(p.matches(metadata(4,'27',['Philosophy']),'music'))
  self.assertTrue(p.matches(metadata(5,'24',['Video_game_culture']),'gaming'));self.assertTrue(p.matches(metadata(6,'24',['Basketball']),'sports'))
  self.assertFalse(p.matches({},'music'))
 def test_drama_titles_with_game_words_are_not_gaming_shelves(self):
  p=self.api()
  for label in ['Game of Thrones','Squid Game','The Hunger Games']:
   with self.subTest(label=label):self.assertIsNone(p.family(label))
  for label in ['Strategy video games','Action games','Video games','Gaming','MOBA','MMO','Clash of Clans']:
   with self.subTest(label=label):self.assertEqual(p.family(label),'gaming')
 def test_country_and_reggae_music_under_entertainment_remain_eligible(self):
  p=self.api()
  for topic in ['Country_music','Reggae']:
   with self.subTest(topic=topic):self.assertTrue(p.matches(metadata(1,'24',[topic]),'music'))
 def test_malformed_topic_url_is_skipped_without_losing_other_valid_topics(self):
  p=self.api();raw=metadata(1,'24');raw['topicDetails']['topicCategories']=['https://[']
  try:matched=p.matches(raw,'music')
  except ValueError as exc:self.fail('Malformed topic URL escaped classification: '+str(exc))
  self.assertFalse(matched);raw['topicDetails']['topicCategories'].append('https://en.wikipedia.org/wiki/Music');self.assertTrue(p.matches(raw,'music'))
 def test_initial_cards_and_seeds_use_only_confirmed_family_without_altering_card_fields(self):
  self.api();items={ident(n):video(n) for n in [1,2,3]};before=copy.deepcopy(items)
  groups=[{'label':'Music Mix','items':[entry(n) for n in [1,2,3]],'youtube_cursor':{'continuation':'opaque'}}]
  rows=home.local_rows(groups,items,{ident(1):metadata(1),ident(2):metadata(2,'25',['Politics']),ident(3):metadata(3,'24',['Jazz'])})
  self.assertEqual(rows[0]['local_items'],[video(1),video(3)]);self.assertEqual(items,before)
  self.assertEqual(rows[0]['youtube_cursor'],{'continuation':'opaque','relevance_family':'music'})
  self.assertEqual(rows[0]['youtube_fallback'],{'related_seeds':[ident(1),ident(3)],'seed_index':0,'relevance_family':'music'})
  self.assertEqual(rows[0]['relevance_family'],'music')

class ProviderRelevance(unittest.TestCase):
 def runtime(self,client):return SimpleNamespace(identity='test-owner',context=object(),provider=SimpleNamespace(get_client=lambda context:client))
 def session(self,runtime):
  @contextmanager
  def session(current):yield runtime
  return session
 def resolve(self,runtime,unique,current):return [video(int(i[1:])) for i in unique]
 def client(self,raw,taxonomy):return SimpleNamespace(get_browse_items=lambda **k:raw,get_related_videos=lambda **k:raw,get_videos=lambda ids,**k:{'items':[taxonomy[i] for i in ids if i in taxonomy]})
 def test_native_page_filters_before_resolution_and_carries_family(self):
  raw={'continuationContents':{'horizontalListContinuation':{'items':[{'tileRenderer':{'onSelectCommand':{'watchEndpoint':{'videoId':ident(n)}}}} for n in [1,2,3]],'continuations':[{'nextContinuationData':{'continuation':'next'}}]}}}
  client=self.client(raw,{ident(1):metadata(1),ident(2):metadata(2,'25',['Politics']),ident(3):metadata(3,'24',['Music'])});runtime=self.runtime(client)
  with patch.object(provider,'_session',self.session(runtime)),patch.object(provider,'_identity',return_value=runtime.identity),patch.object(provider,'_resolve',side_effect=self.resolve):
   files,more=provider.load_shelf_page({'continuation':'first','relevance_family':'music'})
  self.assertEqual(files,[video(1),video(3)]);self.assertEqual(more['relevance_family'],'music');self.assertEqual(more['continuation'],'next')
 def test_related_page_filters_and_preserves_family_when_advancing_seed(self):
  client=self.client({'items':[entry(1),entry(2)]},{ident(1):metadata(1),ident(2):metadata(2,'27',['Philosophy'])});runtime=self.runtime(client)
  cursor={'related_seeds':[ident(8),ident(9)],'seed_index':0,'relevance_family':'music'}
  with patch.object(provider,'_session',self.session(runtime)),patch.object(provider,'_identity',return_value=runtime.identity),patch.object(provider,'_resolve',side_effect=self.resolve):files,more=provider.load_related_page(cursor)
  self.assertEqual(files,[video(1)]);self.assertEqual(more,dict(cursor,seed_index=1))
 def test_missing_related_taxonomy_raises_instead_of_admitting_unknown_or_ending_row(self):
  client=self.client({'items':[entry(1)]},{});client.get_videos=lambda *a,**k:None;runtime=self.runtime(client)
  with patch.object(provider,'_session',self.session(runtime)),patch.object(provider,'_identity',return_value=runtime.identity),patch.object(provider,'_resolve',side_effect=self.resolve):
   with self.assertRaises(RuntimeError):provider.load_related_page({'related_seeds':[ident(8)],'relevance_family':'music'})
 def test_generic_related_extension_does_not_request_taxonomy(self):
  client=self.client({'items':[entry(1)]},{});client.get_videos=lambda *a,**k:self.fail('Generic row requested topical metadata');runtime=self.runtime(client)
  with patch.object(provider,'_session',self.session(runtime)),patch.object(provider,'_resolve',side_effect=self.resolve):files,more=provider.load_related_page({'related_seeds':[ident(8)]})
  self.assertEqual(files,[video(1)]);self.assertIsNone(more)
 def test_initial_metadata_failure_retains_native_home_but_cannot_seed_unverified_extension(self):
  raw=response(shelf('Music Mix',[ident(1)]));raw['contents']['tvBrowseRenderer']['content']['tvSurfaceContentRenderer']['content']['sectionListRenderer']['continuations']=[]
  client=self.client(raw,{});client.get_videos=lambda *a,**k:None;runtime=self.runtime(client)
  with patch.object(provider,'_identity',return_value=runtime.identity),patch.object(provider,'_resolve',side_effect=self.resolve):rows=provider._load_home(runtime,client,lambda:True)
  self.assertEqual(rows[0]['local_items'],[video(1)]);self.assertIsNone(rows[0]['youtube_fallback']);self.assertIsNone(rows[0]['youtube_cursor'])
 def test_initial_taxonomy_requests_only_resolved_topical_videos(self):
  raw=response(shelf('Music Mix',[ident(1),ident(2),ident(3)]),shelf('History',[ident(4)]));raw['contents']['tvBrowseRenderer']['content']['tvSurfaceContentRenderer']['content']['sectionListRenderer']['continuations']=[]
  client=self.client(raw,{ident(1):metadata(1),ident(3):metadata(3,'25',['Politics'])});calls=[];fetch=client.get_videos
  def checked(ids,**kwargs):calls.extend(ids);return fetch(ids,**kwargs)
  client.get_videos=checked;runtime=self.runtime(client)
  def resolve(runtime,unique,current):return [video(int(i[1:])) for i in unique if i!=ident(2)]
  with patch.object(provider,'_identity',return_value=runtime.identity),patch.object(provider,'_resolve',side_effect=resolve):result=provider._load_home(runtime,client,lambda:True)
  self.assertEqual(calls,[ident(1),ident(3)]);self.assertEqual([x['local_items'] for x in result],[[video(1)],[video(4)]])
 def test_removed_or_unclassified_related_videos_are_skipped_without_losing_cursor_progress(self):
  client=self.client({'items':[entry(1),entry(2),entry(3)],'nextPageToken':'next'},{ident(1):metadata(1),ident(3):{'id':ident(3),'snippet':{'title':'Unclassified'}}});runtime=self.runtime(client)
  cursor={'related_seeds':[ident(8)],'relevance_family':'music'}
  with patch.object(provider,'_session',self.session(runtime)),patch.object(provider,'_identity',return_value=runtime.identity),patch.object(provider,'_resolve',side_effect=self.resolve):
   try:files,more=provider.load_related_page(cursor)
   except RuntimeError as exc:self.fail('A valid partial video response must progress: '+str(exc))
  self.assertEqual(files,[video(1)]);self.assertEqual(more['page_token'],'next');self.assertEqual(more['relevance_family'],'music')
  self.assertNotIn(ident(2),runtime._relevance_cache);self.assertNotIn(ident(3),runtime._relevance_cache)
 def test_valid_empty_related_metadata_is_unavailable_video_not_a_service_failure(self):
  client=self.client({'items':[entry(1)]},{});runtime=self.runtime(client)
  with patch.object(provider,'_session',self.session(runtime)),patch.object(provider,'_identity',return_value=runtime.identity):
   try:files,more=provider.load_related_page({'related_seeds':[ident(8),ident(9)],'relevance_family':'music'})
   except RuntimeError as exc:self.fail('Removed video must advance its seed: '+str(exc))
  self.assertEqual(files,[]);self.assertEqual(more['seed_index'],1);self.assertEqual(more['relevance_family'],'music')
 def test_malformed_taxonomy_service_responses_raise_for_retry(self):
  method=getattr(provider,'_relevance_metadata',None);self.assertTrue(callable(method))
  for raw in [None,{}, {'error':{'code':500}}, {'items':[],'error':{'code':500}}]:
   with self.subTest(raw=raw):
    runtime=self.runtime(SimpleNamespace(get_videos=lambda *a,**k:raw))
    with patch.object(provider,'_identity',return_value=runtime.identity),self.assertRaises(RuntimeError):method(runtime,[ident(1)],lambda:True)
 def test_taxonomy_cache_batches_bounds_expiry_and_retired_identity(self):
  method=getattr(provider,'_relevance_metadata',None);self.assertTrue(callable(method),'No bounded runtime taxonomy lookup')
  calls=[];owner=['test-owner'];clock=[100.0]
  def fetch(ids,**kwargs):calls.append((list(ids),kwargs));return {'items':[metadata(int(i[1:])) for i in ids]}
  runtime=self.runtime(SimpleNamespace(get_videos=fetch))
  with patch.object(provider,'_identity',side_effect=lambda:owner[0]),patch.object(provider.time,'monotonic',side_effect=lambda:clock[0]):
   result=method(runtime,[ident(n) for n in range(600)],lambda:True)
   self.assertEqual(len(result),600);self.assertTrue(all(len(ids)<=50 for ids,_ in calls));self.assertLessEqual(len(runtime._relevance_cache),512)
   self.assertTrue(all(k=={'_part':'snippet,topicDetails','max_results':50,'notify':False,'raise_exc':False} for _,k in calls))
   count=len(calls);method(runtime,[ident(599)],lambda:True);self.assertEqual(len(calls),count)
   clock[0]+=3601;method(runtime,[ident(599)],lambda:True);self.assertEqual(len(calls),count+1)
   owner[0]='different-owner'
   with self.assertRaises(RuntimeError):method(runtime,[ident(599)],lambda:True)
 def test_identity_change_during_fetch_cannot_populate_cache(self):
  method=getattr(provider,'_relevance_metadata',None);self.assertTrue(callable(method),'No bounded runtime taxonomy lookup');owner=['test-owner']
  def fetch(ids,**kwargs):owner[0]='different-owner';return {'items':[metadata(1)]}
  runtime=self.runtime(SimpleNamespace(get_videos=fetch))
  with patch.object(provider,'_identity',side_effect=lambda:owner[0]):
   with self.assertRaises(RuntimeError):method(runtime,[ident(1)],lambda:True)
  self.assertFalse(getattr(runtime,'_relevance_cache',{}))

if __name__=='__main__':unittest.main()
