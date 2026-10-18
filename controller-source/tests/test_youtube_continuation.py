"""Personalized continuations retain ownership, order and playback metadata."""
import copy,unittest
from urllib.parse import urlencode
import youtube_home as home
from test_youtube_home import shelf,response
from youtube_core import BASE

def video(n):
 return {'file':BASE+'/play/?'+urlencode({'video_id':'v'+str(n).zfill(10),'resume':'true'}),'filetype':'file',
         'title':'Video '+str(n),'art':{'thumb':'art-'+str(n)},'playcount':1,'resume':{'position':31,'total':600}}

class ContinuationContract(unittest.TestCase):
 def api(self,name):
  f=getattr(home,name,None);self.assertTrue(callable(f),'Missing continuation behavior: '+name);return f
 def test_shelf_cursor_retains_visitor_and_tracking_separately_from_section_cursor(self):
  raw=response(shelf('Personal category',['Abc_123-Xyz']));raw['responseContext']={'visitorData':'visitor-one'}
  listing=raw['contents']['tvBrowseRenderer']['content']['tvSurfaceContentRenderer']['content']['sectionListRenderer']['contents'][0]['shelfRenderer']['content']['horizontalListRenderer']
  listing['continuations']=[{'nextContinuationData':{'continuation':'shelf-token','clickTrackingParams':'shelf-track'}}]
  rows=home.local_rows(home.parse_shelves(raw),{'Abc_123-Xyz':{'file':BASE+'/play/?video_id=Abc_123-Xyz'}})
  self.assertEqual(rows[0].get('youtube_cursor'),{'continuation':'shelf-token','clickTrackingParams':'shelf-track','visitor':'visitor-one'})
 def test_horizontal_continuation_keeps_playlist_cards_and_next_context(self):
  raw={'responseContext':{'visitorData':'new-visitor'},'continuationContents':{'horizontalListContinuation':{
   'items':[{'tileRenderer':{'onSelectCommand':{'browseEndpoint':{'browseId':'VLPL_example'}},'metadata':{'tileMetadataRenderer':{'title':{'simpleText':'A real playlist'}}}}}],
   'continuations':[{'nextContinuationData':{'continuation':'next-token','clickTrackingParams':'next-track'}}]}}}
  entries,cursor=self.api('parse_horizontal')(raw)
  self.assertEqual(entries[0]['file'],BASE+'/playlist/PL_example/');self.assertEqual(entries[0]['filetype'],'directory')
  self.assertEqual(entries[0]['label'],'A real playlist');self.assertEqual(cursor,{'continuation':'next-token','clickTrackingParams':'next-track','visitor':'new-visitor'})
 def test_native_feed_next_route_is_removed_from_videos_without_losing_its_context(self):
  path=BASE+'/special/recommendations';nxt=path+'/?page=2&filtered=1&%25exclude=one%2Ctwo&page_token=opaque&click_tracking=track&visitor=visit'
  folder={'file':BASE+'/special/my_subscriptions/shorts/','filetype':'directory','label':'Shorts'}
  items,cursor=self.api('split_page')([folder,video(1),video(1),{'file':nxt,'filetype':'directory','label':'Next page'}],path)
  self.assertEqual(items,[folder,video(1)]);self.assertEqual(cursor,{'path':nxt})
 def test_subscription_next_page_can_use_only_number_and_native_filter_context(self):
  path=BASE+'/special/my_subscriptions';nxt=path+'/?page=2&filtered=1&%25exclude=one%2Ctwo'
  items,cursor=self.api('split_page')([video(1),{'file':nxt,'filetype':'directory','label':'Next page: 2'}],path)
  self.assertEqual(items,[video(1)]);self.assertEqual(cursor,{'path':nxt})
 def test_append_deduplicates_within_row_and_preserves_existing_art_and_watch_state(self):
  before=[video(1),video(2)];saved=copy.deepcopy(before)
  incoming=[dict(video(2),title='Changed duplicate'),video(3),video(3)]
  result=self.api('merge_page')(before,incoming,{})
  self.assertEqual(result,[video(1),video(2),video(3)]);self.assertEqual(before,saved)
 def test_soft_duplicate_preference_uses_new_choices_but_keeps_small_categories_usable(self):
  f=self.api('merge_page');counts={'v0000000001':2,'v0000000002':2}
  result=f([], [video(n) for n in range(1,9)],counts)
  self.assertEqual([x['title'] for x in result],['Video 3','Video 4','Video 5','Video 6','Video 7','Video 8'])
  self.assertEqual(f([], [video(1),video(2)],counts),[video(1),video(2)])
 def test_lookalike_foreign_or_unrelated_routes_are_never_followed_as_feed_cursors(self):
  f=self.api('split_page');path=BASE+'/special/recommendations'
  for target in ['plugin://evil/special/recommendations?page_token=opaque',BASE+'/special/other?page_token=opaque',path+'?q=different&page_token=opaque']:
   item={'file':target,'filetype':'directory'}
   items,cursor=f([item],path);self.assertEqual(items,[item]);self.assertIsNone(cursor)

if __name__=='__main__':unittest.main()
