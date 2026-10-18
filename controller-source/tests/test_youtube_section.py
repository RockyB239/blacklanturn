"""Account-gated navigation and exact, private YouTube browse previews."""
import copy,importlib.util,sys,unittest
from pathlib import Path
from urllib.parse import parse_qs,urlsplit
sys.path.insert(0,str(Path(__file__).parents[1]/'addon'))
import navigation_core
spec=importlib.util.find_spec('youtube_core')
if spec:import youtube_core as yt
else:yt=None

class YouTubeSection(unittest.TestCase):
 def api(self,name):
  method=getattr(yt,name,None);self.assertTrue(callable(method),'Missing YouTube behavior: '+name);return method
 def store(self,current='0',tokens='first|second|third|'):
  return {'access_manager':{'current_user':current,'users':{'0':{'id':'account-one','refresh_token':tokens,'access_token':'expired','token_expires':0},'1':{'id':'account-two','refresh_token':'other|tokens|here|'}}}}
 def test_only_the_selected_authorized_account_makes_youtube_visible(self):
  connected=self.api('connected_account')
  for state in ({},self.store(tokens='|||'),self.store(current='missing')):self.assertFalse(connected(state)[0])
  self.assertFalse(connected(self.store(),enabled=False)[0])
  self.assertTrue(connected(self.store())[0],'Refreshable sessions survive access-token expiry')
  self.assertNotEqual(connected(self.store())[1],connected(self.store(current='1'))[1])
  self.assertNotEqual(connected(self.store())[1],connected(self.store(tokens='different|account|tokens|'))[1])
 def test_transient_read_failure_retains_visibility_but_explicit_logout_hides_it(self):
  state=self.api('ConnectionState')();read=lambda:self.store()
  self.assertTrue(state.refresh(read,True));self.assertTrue(state.connected)
  def unavailable():raise OSError('temporarily unreadable')
  self.assertFalse(state.refresh(unavailable,True));self.assertTrue(state.connected)
  self.assertTrue(state.refresh(lambda:self.store(tokens='|||'),True));self.assertFalse(state.connected)
  state.refresh(read,True);self.assertTrue(state.refresh(unavailable,False));self.assertFalse(state.connected)
 def test_sidebar_appears_without_rewriting_or_duplicating_saved_navigation(self):
  config=navigation_core.migrate_navigation({'PreviewDelay':8,'Saved':[{'file':'private'}]});before=copy.deepcopy(config)
  self.assertNotIn('youtube',[x['id'] for x in navigation_core.sidebar_items(config)])
  self.assertIn('youtube',[x['id'] for x in navigation_core.sidebar_items(config,youtube_connected=True)])
  sections=[x.get('destination',{}).get('section') for x in navigation_core.sidebar_items(config,youtube_connected=True)]
  self.assertEqual(sections.index('YouTube'),sections.index('Movies')+1);self.assertLess(sections.index('YouTube'),sections.index('My Stuff'))
  self.assertEqual(config,before)
  config['Sidebar'].append({'id':'yt-custom','label':'Videos','icon':'youtube','destination':{'kind':'section','section':'YouTube'}})
  self.assertEqual(sum(x.get('destination',{}).get('section')=='YouTube' for x in navigation_core.sidebar_items(config,youtube_connected=True)),1)
  self.assertNotIn('yt-custom',[x['id'] for x in navigation_core.sidebar_items(config,youtube_connected=False)])
 def test_youtube_destination_stays_inside_the_skin(self):
  self.assertEqual(navigation_core.resolve_destination({'kind':'section','section':'YouTube'},{}),{'kind':'section','section':'YouTube'})
 def test_feed_tabs_use_account_routes_and_search_does_not_escape_query(self):
  rows=self.api('tab_rows')
  self.assertEqual([x['path'] for x in rows('home')[:2]],['plugin://plugin.video.youtube/special/recommendations','plugin://plugin.video.youtube/special/my_subscriptions'])
  self.assertEqual(rows('subscriptions')[0]['path'],'plugin://plugin.video.youtube/special/my_subscriptions')
  self.assertEqual(rows('channels')[0]['path'],'plugin://plugin.video.youtube/subscriptions/list/')
  search=rows('search','cats & dogs')[0]['path'];self.assertEqual(parse_qs(urlsplit(search).query)['q'],['cats & dogs'])
  self.assertEqual(urlsplit(search).netloc,'plugin.video.youtube')
 def test_preview_plays_exact_highlighted_video_without_history_or_suggested_queue(self):
  preview=self.api('preview_path');item={'file':'plugin://plugin.video.youtube/play/?video_id=Abc_123-Xyz&playlist_id=private','filetype':'file','title':'Selected video'};before=copy.deepcopy(item)
  path=preview(item);q=parse_qs(urlsplit(path).query)
  self.assertEqual(q['video_id'],['Abc_123-Xyz']);self.assertEqual(q['incognito'],['true']);self.assertEqual(q['screensaver'],['true']);self.assertEqual(q['end'],['30']);self.assertNotIn('playlist_id',q);self.assertEqual(item,before)
  for bad in [{'file':'plugin://evil/play/?video_id=Abc_123-Xyz'},{'file':item['file'],'filetype':'directory'},{'file':'plugin://plugin.video.youtube/play/?video_id=wrong)Quit()'}]:self.assertIsNone(preview(bad))
 def test_video_artwork_prefers_its_thumbnail_and_preserves_normal_movie_artwork(self):
  from live_core import card_artwork
  item={'file':'plugin://plugin.video.youtube/play/?video_id=Abc_123-Xyz','filetype':'file','art':{'thumb':'selected.jpg','fanart':'channel-background.jpg'}}
  self.assertEqual(card_artwork(item),{'image':'selected.jpg','kind':'landscape'})
  item['file']='plugin://plugin.video.themoviedb.helper/?info=details&tmdb_type=movie&tmdb_id=1'
  self.assertEqual(card_artwork(item),{'image':'channel-background.jpg','kind':'landscape'})
 def test_full_play_keeps_provider_resume_history_and_original_url(self):
  video=self.api('video_id');item={'file':'plugin://plugin.video.youtube/play/?video_id=Abc_123-Xyz&resume=true','filetype':'file','resume':{'position':73,'total':600},'playcount':1,'art':{'thumb':'selected.jpg'}};before=copy.deepcopy(item)
  self.assertEqual(video(item),'Abc_123-Xyz');self.api('preview_path')(item);self.assertEqual(item,before)


 def test_library_uses_configured_account_playlists_and_channel_artist_metadata(self):
  rows=self.api('tab_rows')
  data=rows('library',account={'watch_later':'PLcustom_watch','watch_history':'PLcustom_history'})
  self.assertEqual(data[1]['path'],'plugin://plugin.video.youtube/channel/mine/playlist/PLcustom_watch/')
  self.assertEqual(data[2]['path'],'plugin://plugin.video.youtube/channel/mine/playlist/PLcustom_history/')
  self.assertEqual(self.api('caption')({'artist':['Channel name'],'runtime':125}),'Channel name · 2:05')
  local=rows('library',account={'watch_later':'','watch_history':''})
  self.assertEqual(local[1]['path'],'plugin://plugin.video.youtube/kodion/watch_later/list/')
  self.assertEqual(local[2]['path'],'plugin://plugin.video.youtube/kodion/playback_history/list/')



 def test_youtube_navigation_tiles_keep_folder_art_separate_from_video_thumbnails(self):
  from native_list_fixture import media_functions
  render=media_functions()['media_item']
  folder={'file':'plugin://plugin.video.youtube/special/my_subscriptions/shorts/','filetype':'directory','label':'Shorts','art':{'thumb':'shorts.png'}}
  video={'file':'plugin://plugin.video.youtube/play/?video_id=Abc_123-Xyz','filetype':'file','label':'A video','art':{'thumb':'video.jpg'}}
  before=copy.deepcopy(folder);tile=render(folder)
  self.assertEqual(tile.properties.get('youtubeFolder'),'true');self.assertEqual(tile.art.get('youtubefolder'),'shorts.png');self.assertEqual(tile.path,folder['file']);self.assertEqual(folder,before)
  self.assertEqual(render(video).properties.get('youtubeFolder'),'false')

 def test_playlist_thumbnail_uses_full_card_without_changing_folder_navigation(self):
  from native_list_fixture import media_functions
  render=media_functions()['media_item']
  item={'file':'plugin://plugin.video.youtube/playlist/PL_real/','filetype':'directory','label':'StarTalk Podcast',
        'art':{'thumb':'https://i.ytimg.com/vi/Abc_123-Xyz/hq720.jpg'}}
  before=copy.deepcopy(item);card=render(item)
  self.assertEqual(card.properties.get('youtubeFolder'),'false','Real playlist image must not use the centered icon layout')
  self.assertEqual(card.properties.get('cardArtKind'),'landscape');self.assertEqual(card.art['landscape'],item['art']['thumb'])
  self.assertEqual(card.getPath(),item['file']);self.assertEqual(item,before)

if __name__=='__main__':unittest.main()
